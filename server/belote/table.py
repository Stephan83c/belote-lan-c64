"""La table de jeu : sièges, chef, états, diffusion et bots (SPEC 4, 6.3, 7).

Toute la logique est synchrone et s'exécute dans la boucle asyncio : chaque
message reçu est traité entièrement avant le suivant. Seuls les délais des bots
passent par `call_later`.
"""

from __future__ import annotations

import asyncio
import random
import re
import time
from dataclasses import dataclass
from typing import Protocol

from .bots import choisir_carte, choisir_enchere
from .moteur import CoupRefuse, Donne, PasTonTour, Phase, couleur, equipe_gagnante

ATTENTE = "ATTENTE"
LANCEE = "LANCEE"
EN_COURS = "EN COURS"
FIN_MANCHE = "FIN MANCHE"
FIN_PARTIE = "FIN PARTIE"

NOM_BOT = "BOT"
NOM_VALIDE = re.compile(r"[A-Z0-9]{1,5}")
# Les clients nomment les bots BOT1 à BOT4 : ces noms (et BOT) sont refusés aux humains.
NOM_RESERVE = re.compile(r"BOT[0-9]*")
TCHAT_MAX = 30
DELAI_BOT = 1.0
# Après une prise, le premier bot attend plus longtemps : le temps de voir la carte prise.
FACTEUR_PAUSE_PRISE = 3


class Client(Protocol):
    def envoyer(self, ligne: str) -> None: ...
    def fermer(self) -> None: ...

    # Facultatif : adresse IP du client, pour reconnaître un C64 redémarré.
    # adresse: str | None


@dataclass
class Siege:
    humain: Client | None = None
    nom: str = NOM_BOT
    nom_reserve: str | None = None  # ancien occupant pouvant revenir (4.3)
    actif_a: float = 0.0


def _entier(texte: str) -> int | None:
    return int(texte) if texte.isascii() and texte.isdigit() and len(texte) < 6 else None


class Table:
    def __init__(self, rng: random.Random | None = None, delai_bot: float = DELAI_BOT):
        self.rng = rng or random.Random()
        self.delai_bot = delai_bot
        self._pause_prise = False
        self.sieges = [Siege() for _ in range(4)]
        self.chef = -1
        self.etat = ATTENTE
        self.cible = 1000
        self.inactif_min: float = 3
        self.scores = [0, 0]
        self.reserve = 0
        self.donneur = 0
        self.donne: Donne | None = None
        self._minuteur_bot: asyncio.TimerHandle | None = None
        self._attendu_depuis = time.monotonic()

    # ---- Diffusion -------------------------------------------------------

    def _humains(self) -> list[tuple[int, Siege]]:
        return [(p, s) for p, s in enumerate(self.sieges) if s.humain is not None]

    def _diffuser(self, ligne: str) -> None:
        for _, siege in self._humains():
            siege.humain.envoyer(ligne)

    def _envoyer_main(self, place: int) -> None:
        client = self.sieges[place].humain
        if client is not None:
            client.envoyer(" ".join(["MAIN", *map(str, self.donne.mains[place])]))

    def _ligne_nbcartes(self) -> str:
        return "NBCARTES " + " ".join(map(str, self.donne.nb_cartes()))

    def _ligne_siege(self, place: int) -> str:
        s = self.sieges[place]
        return f"SIEGE {place} {'H' if s.humain is not None else 'B'} {s.nom}"

    def _place_de(self, client: Client) -> int | None:
        for place, siege in enumerate(self.sieges):
            if siege.humain is client:
                return place
        return None

    # ---- Réception -------------------------------------------------------

    def recevoir(self, client: Client, ligne: str) -> None:
        """Traite une ligne déjà nettoyée par le cadreur."""
        mot, _, reste = ligne.strip(" ").partition(" ")
        if not mot:
            return
        place = self._place_de(client)
        if mot == "JOIN":
            self._cmd_join(client, reste.strip(" "), place)
        elif mot == "LEAVE":
            if place is not None:
                self._liberer(place, f"{self.sieges[place].nom} REMPLACE PAR UN BOT")
            client.fermer()
        elif place is None:
            client.envoyer("ERR NOM")  # JOIN obligatoire d'abord
        else:
            self.sieges[place].actif_a = time.monotonic()
            self._commande(client, place, mot, reste)

    def _commande(self, client: Client, place: int, mot: str, reste: str) -> None:
        if mot == "TCHAT":
            texte = reste.strip(" ")[:TCHAT_MAX].rstrip(" ")
            if texte:
                self._diffuser(f"TCHAT {self.sieges[place].nom} {texte}")
        elif mot == "LANCER":
            self._cmd_lancer(client, place)
        elif mot == "PARAM":
            self._cmd_param(client, place, reste)
        elif mot == "REJOUER":
            self._cmd_rejouer(client, place)
        elif mot == "RAZ":
            if place != self.chef:
                client.envoyer("ERR CHEF SEUL")
            elif not self.raz():
                client.envoyer("ERR PAS LANCEE")
        elif mot == "PASSE":
            self._action(client, lambda d: d.passer(place))
        elif mot == "ENCH":
            c = _entier(reste.strip(" "))
            self._action(client, lambda d: d.prendre(place, -1 if c is None else c))
        elif mot == "COUP":
            c = _entier(reste.strip(" "))
            self._action(client, lambda d: d.jouer(place, -1 if c is None else c))
        else:
            client.envoyer("ERR INCONNU")

    def _action(self, client: Client, faire) -> None:
        if self.etat != EN_COURS:
            client.envoyer("ERR PAS TON TOUR")
            return
        try:
            evenements = faire(self.donne)
        except PasTonTour:
            client.envoyer("ERR PAS TON TOUR")
        except CoupRefuse:
            client.envoyer("ERR COUP REFUSE")
        else:
            self._appliquer(evenements)

    # ---- Connexion, départ, chef -----------------------------------------

    def _nom_unique(self, nom: str) -> str | None:
        pris = {NOM_BOT}
        for s in self.sieges:
            if s.humain is not None:
                pris.add(s.nom)
            if s.nom_reserve:
                pris.add(s.nom_reserve)
        if nom not in pris:
            return nom
        # L'exemple de la spec donne JEAN -> JEA2 : le 1 n'est essayé qu'en dernier.
        for suffixe in "234567891":
            candidat = nom[:-1] + suffixe
            if candidat not in pris and not NOM_RESERVE.fullmatch(candidat):
                return candidat
        return None

    def _cmd_join(self, client: Client, nom: str, place_actuelle: int | None) -> None:
        if place_actuelle is not None or not NOM_VALIDE.fullmatch(nom):
            client.envoyer("ERR NOM")
            return
        if NOM_RESERVE.fullmatch(nom):
            client.envoyer("ERR NOM RESERVE")
            return

        reprise = self._place_fantome(client, nom)
        if reprise is not None:
            self._reprendre(client, reprise)
            return

        libres = [p for p, s in enumerate(self.sieges) if s.humain is None]
        if not libres:
            client.envoyer("ERR TABLE PLEINE")
            client.fermer()
            return

        place = next((p for p in libres if self.sieges[p].nom_reserve == nom), None)
        if place is None:
            final = self._nom_unique(nom)
            if final is None:
                client.envoyer("ERR NOM")
                return
            place = next((p for p in libres if self.sieges[p].nom_reserve is None), libres[0])
            if final != nom:
                client.envoyer(f"INFO NOM CHANGE EN {final}")
            nom = final

        siege = self.sieges[place]
        siege.humain, siege.nom, siege.nom_reserve = client, nom, None
        siege.actif_a = time.monotonic()

        ancien_chef = self.chef
        self._maj_chef()

        client.envoyer(f"BIENVENUE {nom} {place}")
        self._envoyer_etat(client, place)
        for p, autre in self._humains():
            if p != place:
                autre.humain.envoyer(self._ligne_siege(place))
                if self.chef != ancien_chef:
                    autre.humain.envoyer(f"CHEF {self.chef}")
        self._apres_changement()

    def _place_fantome(self, client: Client, nom: str) -> int | None:
        """Place tenue sous ce nom par une connexion de la même adresse IP.

        Un C64 redémarré (reset, make deploy) n'envoie pas LEAVE : sa vieille
        connexion TCP reste ouverte et garderait la place jusqu'à l'inactivité.
        """
        adresse = getattr(client, "adresse", None)
        if adresse is None:
            return None
        for place, siege in enumerate(self.sieges):
            ancien = siege.humain
            if ancien is not None and siege.nom == nom and getattr(ancien, "adresse", None) == adresse:
                return place
        return None

    def _reprendre(self, client: Client, place: int) -> None:
        siege = self.sieges[place]
        ancien = siege.humain
        siege.humain = client
        siege.actif_a = time.monotonic()
        ancien.fermer()  # sa déconnexion ne trouvera plus de place : sans effet
        client.envoyer(f"BIENVENUE {siege.nom} {place}")
        self._envoyer_etat(client, place)
        for p, autre in self._humains():
            if p != place:
                autre.humain.envoyer(f"INFO {siege.nom} RECONNECTE")

    def _envoyer_etat(self, client: Client, place: int) -> None:
        for p in range(4):
            client.envoyer(self._ligne_siege(p))
        client.envoyer(f"CHEF {self.chef}")
        client.envoyer(f"ETAT {self.etat}")
        client.envoyer(f"PARAM CIBLE {self.cible}")
        client.envoyer(f"PARAM INACTIF {self.inactif_min}")
        if self.etat == ATTENTE:
            return
        client.envoyer(f"SCORE {self.scores[0]} {self.scores[1]}")
        client.envoyer(f"DONNEUR {self.donneur}")
        if self.etat != EN_COURS:
            return
        d = self.donne
        if d.phase is Phase.ENCHERES:
            client.envoyer(f"RETOURNE {d.retournee}")
            client.envoyer(f"ENCHERES {d.tour_encheres}")
        else:
            client.envoyer(f"PREND {d.preneur} {d.atout}")
        self._envoyer_main(place)
        client.envoyer(self._ligne_nbcartes())
        if d.phase is Phase.JEU:
            client.envoyer("PLICOURS " + " ".join(map(str, d.plicours())))
        client.envoyer(f"TOUR {d.joueur}")

    def _maj_chef(self) -> None:
        humains = [p for p, _ in self._humains()]
        if self.chef not in humains:
            self.chef = humains[0] if humains else -1

    def _liberer(self, place: int, info: str) -> None:
        """Le bot reprend la place, avec la main en cours."""
        siege = self.sieges[place]
        ancien_nom = siege.nom
        siege.humain = None
        siege.nom = NOM_BOT
        # En attente il n'y a pas de main à retrouver : la place redevient neutre.
        siege.nom_reserve = ancien_nom if self.etat != ATTENTE else None

        ancien_chef = self.chef
        self._maj_chef()
        self._diffuser(self._ligne_siege(place))
        if self.chef != ancien_chef:
            self._diffuser(f"CHEF {self.chef}")
        self._diffuser(f"INFO {info}")

        immediat = self.etat == EN_COURS and self.donne.joueur == place
        self._apres_changement(immediat=immediat)

    def deconnexion(self, client: Client) -> None:
        place = self._place_de(client)
        if place is not None:
            self._liberer(place, f"{self.sieges[place].nom} REMPLACE PAR UN BOT")

    # ---- Commandes du chef -----------------------------------------------

    def _cmd_lancer(self, client: Client, place: int) -> None:
        if place != self.chef:
            client.envoyer("ERR CHEF SEUL")
        elif self.etat != ATTENTE:
            client.envoyer("ERR DEJA LANCEE")
        else:
            self.donneur = place
            self._demarrer_partie()

    def _cmd_param(self, client: Client, place: int, reste: str) -> None:
        if place != self.chef:
            client.envoyer("ERR CHEF SEUL")
            return
        if self.etat != ATTENTE:
            client.envoyer("ERR DEJA LANCEE")
            return
        nom, _, valeur = reste.strip(" ").partition(" ")
        n = _entier(valeur.strip(" "))
        if nom == "CIBLE" and n is not None and 500 <= n <= 5000:
            self.cible = n
            self._diffuser(f"PARAM CIBLE {n}")
        elif nom == "INACTIF" and n is not None and 1 <= n <= 10:
            self.inactif_min = n
            self._diffuser(f"PARAM INACTIF {n}")
        else:
            client.envoyer("ERR PARAM")

    def _cmd_rejouer(self, client: Client, place: int) -> None:
        if place != self.chef:
            client.envoyer("ERR CHEF SEUL")
        elif self.etat == FIN_MANCHE:
            self.donneur = (self.donneur + 1) % 4
            self._nouvelle_donne()
        elif self.etat == FIN_PARTIE:
            self.donneur = (self.donneur + 1) % 4
            self._demarrer_partie()
        elif self.etat == ATTENTE:
            client.envoyer("ERR PAS LANCEE")
        else:
            client.envoyer("ERR DEJA LANCEE")

    def raz(self) -> bool:
        """Console du serveur ou commande RAZ du chef : efface la partie, retour en ATTENTE.

        Les humains connectés et les paramètres sont conservés. Renvoie False
        s'il n'y avait aucune partie à effacer.
        """
        if self.etat == ATTENTE:
            return False
        self.etat = ATTENTE
        self.donne = None
        self.scores = [0, 0]
        self.reserve = 0
        for siege in self.sieges:
            siege.nom_reserve = None
        self._diffuser("INFO PARTIE EFFACEE")
        self._diffuser("SCORE 0 0")
        self._diffuser(f"ETAT {ATTENTE}")
        self._apres_changement()
        return True

    # ---- Déroulement -----------------------------------------------------

    def _demarrer_partie(self) -> None:
        self.scores = [0, 0]
        self.reserve = 0
        self.etat = LANCEE
        self._diffuser(f"ETAT {LANCEE}")
        self._diffuser("SCORE 0 0")
        self._nouvelle_donne()

    def _nouvelle_donne(self) -> None:
        self.donne = Donne(self.donneur, self.rng)
        self.etat = EN_COURS
        self._diffuser(f"ETAT {EN_COURS}")
        self._diffuser(f"DONNEUR {self.donneur}")
        self._distribuer_mains()
        self._diffuser(f"RETOURNE {self.donne.retournee}")
        self._diffuser("ENCHERES 1")
        self._diffuser(f"TOUR {self.donne.joueur}")
        self._apres_changement()

    def _distribuer_mains(self) -> None:
        for place in range(4):
            self._envoyer_main(place)
        self._diffuser(self._ligne_nbcartes())

    def _appliquer(self, evenements: list[tuple]) -> None:
        for evt in evenements:
            nom = evt[0]
            if nom == "MAINS":
                self._distribuer_mains()
            elif nom == "MAIN":
                self._envoyer_main(evt[1])
            elif nom == "FIN":
                self._fin_manche()
            elif nom == "PREND":
                self._diffuser(" ".join(map(str, evt)))
                self._pause_prise = True
            elif nom == "REDONNE":
                self._diffuser("REDONNE")
                self.donneur = (self.donneur + 1) % 4
                self._nouvelle_donne()
            else:
                self._diffuser(" ".join(map(str, evt)))
        self._apres_changement()

    def _fin_manche(self) -> None:
        res = self.donne.resultat(self.reserve)
        self.reserve = res.reserve
        self.scores[0] += res.points[0]
        self.scores[1] += res.points[1]

        if res.capot is not None:
            self._diffuser(f"CAPOT {res.capot}")
        if res.litige:
            self._diffuser(f"LITIGE {res.litige}")
        if res.reserve_gagnee:
            camp, points = res.reserve_gagnee
            self._diffuser(f"INFO RESERVE {points} POUR EQUIPE {camp}")
        self._diffuser(f"MANCHE {res.points[0]} {res.points[1]}")
        self._diffuser(f"SCORE {self.scores[0]} {self.scores[1]}")

        gagnante = equipe_gagnante(self.scores, self.cible)
        if gagnante is None:
            self.etat = FIN_MANCHE
        else:
            self.etat = FIN_PARTIE
            self._diffuser(f"GAGNANT {gagnante}")
        self._diffuser(f"ETAT {self.etat}")

    # ---- Bots et inactivité ----------------------------------------------

    def _apres_changement(self, immediat: bool = False) -> None:
        self._attendu_depuis = time.monotonic()
        self._planifier_bot(immediat)

    def _planifier_bot(self, immediat: bool) -> None:
        pause, self._pause_prise = self._pause_prise, False
        if self._minuteur_bot is not None:
            self._minuteur_bot.cancel()
            self._minuteur_bot = None
        # Sans humain à la table, la partie reste en suspens (4.2).
        if self.etat != EN_COURS or not self._humains():
            return
        if self.sieges[self.donne.joueur].humain is not None:
            return
        delai = 0 if immediat else self.delai_bot
        if pause:
            delai = self.delai_bot * FACTEUR_PAUSE_PRISE
        self._minuteur_bot = asyncio.get_running_loop().call_later(delai, self._action_bot)

    def _action_bot(self) -> None:
        self._minuteur_bot = None
        d = self.donne
        place = d.joueur
        if d.phase is Phase.ENCHERES:
            choix = choisir_enchere(d.mains[place], d.tour_encheres, couleur(d.retournee))
            evenements = d.passer(place) if choix is None else d.prendre(place, choix)
        else:
            evenements = d.jouer(place, choisir_carte(d.mains[place], d.pli, d.atout, place, d.jouees))
        self._appliquer(evenements)

    def _place_attendue(self) -> int | None:
        if self.etat == EN_COURS:
            return self.donne.joueur
        if self.etat in (FIN_MANCHE, FIN_PARTIE):
            return self.chef
        return None

    def verifier_inactivite(self, maintenant: float | None = None) -> None:
        """Remplace par un bot l'humain attendu depuis trop longtemps (4.3).

        Seul celui dont la table attend une action peut être jugé inactif : le
        joueur à son tour, ou le chef en fin de manche ou de partie.
        """
        place = self._place_attendue()
        if place is None or place < 0:
            return
        siege = self.sieges[place]
        if siege.humain is None:
            return
        maintenant = time.monotonic() if maintenant is None else maintenant
        depuis = max(self._attendu_depuis, siege.actif_a)
        if maintenant - depuis >= self.inactif_min * 60:
            client = siege.humain
            client.envoyer("INFO INACTIF : PLACE RENDUE AU BOT")
            self._liberer(place, f"{siege.nom} INACTIF REMPLACE PAR UN BOT")
            client.fermer()

    async def boucle_inactivite(self, periode: float = 1.0) -> None:
        while True:
            await asyncio.sleep(periode)
            self.verifier_inactivite()
