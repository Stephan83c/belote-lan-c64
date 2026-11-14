"""Moteur de belote pur (SPEC section 5) : aucune entrée/sortie, aucun réseau.

Les méthodes de `Donne` renvoient une liste d'événements (tuples). La plupart
correspondent directement à un message du protocole, par ex. ("JOUE", 1, 14).
Trois événements sont internes et interprétés par la table :
("MAINS",) distribution terminée, ("MAIN", p) main privée de p, ("FIN",) huit
plis joués.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

PIQUE, COEUR, TREFLE, CARREAU = range(4)
SEPT, HUIT, NEUF, DIX, VALET, DAME, ROI, AS = range(8)

_ORDRE_NORMAL = (SEPT, HUIT, NEUF, VALET, DAME, ROI, DIX, AS)
_ORDRE_ATOUT = (SEPT, HUIT, DAME, ROI, DIX, AS, NEUF, VALET)
_FORCE_NORMALE = {rang: i for i, rang in enumerate(_ORDRE_NORMAL)}
_FORCE_ATOUT = {rang: i for i, rang in enumerate(_ORDRE_ATOUT)}
_POINTS_NORMAUX = {SEPT: 0, HUIT: 0, NEUF: 0, VALET: 2, DAME: 3, ROI: 4, DIX: 10, AS: 11}
_POINTS_ATOUT = {SEPT: 0, HUIT: 0, DAME: 3, ROI: 4, DIX: 10, AS: 11, NEUF: 14, VALET: 20}

DIX_DE_DER = 10
TOTAL_MANCHE = 162
POINTS_CAPOT = 252
POINTS_BELOTE = 20


class CoupRefuse(Exception):
    """Action au bon moment mais contraire aux règles."""


class PasTonTour(Exception):
    """Action d'une place qui n'a pas la main."""


class Phase(Enum):
    ENCHERES = 1
    JEU = 2
    FINIE = 3
    ANNULEE = 4


def carte(couleur_: int, rang_: int) -> int:
    return couleur_ * 8 + rang_


def couleur(c: int) -> int:
    return c // 8


def rang(c: int) -> int:
    return c % 8


def equipe(place: int) -> int:
    return place % 2


def partenaire(place: int) -> int:
    return (place + 2) % 4


def points_carte(c: int, atout: int) -> int:
    return (_POINTS_ATOUT if couleur(c) == atout else _POINTS_NORMAUX)[rang(c)]


def force(c: int, atout: int) -> int:
    """Force à l'intérieur d'une couleur (selon qu'elle est atout ou non)."""
    return (_FORCE_ATOUT if couleur(c) == atout else _FORCE_NORMALE)[rang(c)]


def gagnant_pli(pli: list[tuple[int, int]], atout: int) -> int:
    """Place maîtresse d'un pli (complet ou non), liste de (place, carte)."""
    demandee = couleur(pli[0][1])

    def cle(coup: tuple[int, int]) -> tuple[int, int]:
        c = coup[1]
        if couleur(c) == atout:
            return (2, force(c, atout))
        if couleur(c) == demandee:
            return (1, force(c, atout))
        return (0, 0)

    return max(pli, key=cle)[0]


def coups_legaux(main: list[int], pli: list[tuple[int, int]], atout: int, place: int) -> list[int]:
    """Cartes de `main` autorisées par la section 5.3."""
    if not pli:
        return list(main)

    demandee = couleur(pli[0][1])
    atouts = [c for c in main if couleur(c) == atout]
    forces_posees = [force(c, atout) for _, c in pli if couleur(c) == atout]
    plus_fort_pose = max(forces_posees, default=-1)
    surcoupes = [c for c in atouts if force(c, atout) > plus_fort_pose]

    if demandee == atout:
        return surcoupes or atouts or list(main)

    en_couleur = [c for c in main if couleur(c) == demandee]
    if en_couleur:
        return en_couleur

    if gagnant_pli(pli, atout) == partenaire(place):
        return list(main)
    if not atouts:
        return list(main)
    if surcoupes:
        return surcoupes
    # Impossible de surcouper : sous-couper seulement s'il ne reste que de l'atout.
    return [c for c in main if couleur(c) != atout] or atouts


@dataclass(frozen=True)
class ResultatManche:
    points: tuple[int, int]  # points marqués, réserve remportée comprise
    reserve: int  # réserve après cette manche
    litige: int = 0  # points mis en réserve par cette manche
    capot: int | None = None  # équipe qui a fait les 8 plis
    reserve_gagnee: tuple[int, int] | None = None  # (équipe, points)


def compter_manche(
    equipe_preneuse: int,
    points_cartes: tuple[int, int],
    plis: tuple[int, int],
    equipe_belote: int | None = None,
    reserve: int = 0,
) -> ResultatManche:
    """Section 5.5. `points_cartes` inclut le dix de der, jamais la belote."""
    t = equipe_preneuse
    d = 1 - t
    belote = [0, 0]
    if equipe_belote is not None:
        belote[equipe_belote] = POINTS_BELOTE

    points = [0, 0]
    gagnante: int | None = None
    capot: int | None = None
    litige = 0

    if 8 in plis:
        capot = plis.index(8)
        points[capot] = POINTS_CAPOT + belote[capot]
        points[1 - capot] = belote[1 - capot]
        gagnante = capot
    else:
        total_t = points_cartes[t] + belote[t]
        total_d = points_cartes[d] + belote[d]
        if total_t > total_d:
            points[t], points[d] = total_t, total_d
            gagnante = t
        elif total_t < total_d:
            points[t], points[d] = belote[t], TOTAL_MANCHE + belote[d]
            gagnante = d
        else:
            # La belote reste toujours à l'équipe qui l'annonce (5.4) : seuls
            # les points de cartes du preneur partent en réserve.
            points[t], points[d] = belote[t], total_d
            litige = points_cartes[t]
            reserve += litige

    reserve_gagnee = None
    if gagnante is not None and reserve:
        points[gagnante] += reserve
        reserve_gagnee = (gagnante, reserve)
        reserve = 0

    return ResultatManche((points[0], points[1]), reserve, litige, capot, reserve_gagnee)


def equipe_gagnante(scores: tuple[int, int] | list[int], cible: int) -> int | None:
    """Section 2.3. None : la partie continue (y compris égalité parfaite)."""
    if max(scores) < cible or scores[0] == scores[1]:
        return None
    return 0 if scores[0] > scores[1] else 1


class Donne:
    """Une donne : distribution, enchères puis huit plis."""

    def __init__(self, donneur: int, rng: random.Random | None = None, paquet: list[int] | None = None):
        if paquet is None:
            paquet = list(range(32))
            (rng or random).shuffle(paquet)
        if sorted(paquet) != list(range(32)):
            raise ValueError("le paquet doit contenir les 32 cartes")

        self.donneur = donneur
        self.premier = (donneur + 1) % 4
        self.mains: list[list[int]] = [[] for _ in range(4)]
        self._paquet = list(paquet)
        for nb in (3, 2):
            for place in self._ordre():
                self._donner(place, nb)
        self.retournee = self._paquet.pop(0)

        self.phase = Phase.ENCHERES
        self.tour_encheres = 1
        self.joueur = self.premier
        self._passes = 0

        self.preneur: int | None = None
        self.atout: int | None = None
        self.pli: list[tuple[int, int]] = []
        self.jouees: list[int] = []         # cartes posées, dans l'ordre (mémoire des bots)
        self.nb_plis = 0
        self.points_cartes = [0, 0]
        self.plis_gagnes = [0, 0]
        self.place_belote: int | None = None
        self._belote_annoncee = False

    def _ordre(self) -> list[int]:
        return [(self.premier + i) % 4 for i in range(4)]

    def _donner(self, place: int, nb: int) -> None:
        self.mains[place].extend(self._paquet[:nb])
        del self._paquet[:nb]
        self.mains[place].sort()

    def _verifier_tour(self, place: int) -> None:
        if self.phase not in (Phase.ENCHERES, Phase.JEU) or place != self.joueur:
            raise PasTonTour

    def nb_cartes(self) -> list[int]:
        return [len(m) for m in self.mains]

    def plicours(self) -> list[int]:
        """Cartes du pli en cours par place, -1 si pas encore jouée."""
        cartes = [-1] * 4
        for place, c in self.pli:
            cartes[place] = c
        return cartes

    def passer(self, place: int) -> list[tuple]:
        self._verifier_tour(place)
        if self.phase is not Phase.ENCHERES:
            raise CoupRefuse
        evts: list[tuple] = [("PASSE", place)]
        self._passes += 1
        self.joueur = (place + 1) % 4
        if self._passes < 4:
            evts.append(("TOUR", self.joueur))
        elif self.tour_encheres == 1:
            self.tour_encheres = 2
            self._passes = 0
            evts += [("ENCHERES", 2), ("TOUR", self.joueur)]
        else:
            self.phase = Phase.ANNULEE
            evts.append(("REDONNE",))
        return evts

    def prendre(self, place: int, couleur_: int) -> list[tuple]:
        self._verifier_tour(place)
        if self.phase is not Phase.ENCHERES or not 0 <= couleur_ <= 3:
            raise CoupRefuse
        est_retournee = couleur_ == couleur(self.retournee)
        if est_retournee != (self.tour_encheres == 1):
            raise CoupRefuse

        self.preneur = place
        self.atout = couleur_
        self.mains[place].append(self.retournee)
        for p in self._ordre():
            self._donner(p, 2 if p == place else 3)

        roi, dame = carte(couleur_, ROI), carte(couleur_, DAME)
        for p, main in enumerate(self.mains):
            if roi in main and dame in main:
                self.place_belote = p

        self.phase = Phase.JEU
        self.joueur = self.premier
        return [("PREND", place, couleur_), ("MAINS",), ("TOUR", self.joueur)]

    def legaux(self, place: int) -> list[int]:
        return coups_legaux(self.mains[place], self.pli, self.atout, place)

    def jouer(self, place: int, c: int) -> list[tuple]:
        self._verifier_tour(place)
        if self.phase is not Phase.JEU or c not in self.legaux(place):
            raise CoupRefuse

        self.mains[place].remove(c)
        self.pli.append((place, c))
        self.jouees.append(c)
        evts: list[tuple] = [("JOUE", place, c)]

        if place == self.place_belote and c in (carte(self.atout, ROI), carte(self.atout, DAME)):
            evts.append(("REBELOTE" if self._belote_annoncee else "BELOTE", place))
            self._belote_annoncee = True
        evts.append(("MAIN", place))

        if len(self.pli) < 4:
            self.joueur = (place + 1) % 4
            evts.append(("TOUR", self.joueur))
            return evts

        gagnant = gagnant_pli(self.pli, self.atout)
        camp = equipe(gagnant)
        self.points_cartes[camp] += sum(points_carte(x, self.atout) for _, x in self.pli)
        self.plis_gagnes[camp] += 1
        self.nb_plis += 1
        self.pli = []
        self.joueur = gagnant
        evts.append(("PLI", gagnant))

        if self.nb_plis < 8:
            evts.append(("TOUR", gagnant))
        else:
            self.points_cartes[camp] += DIX_DE_DER
            self.phase = Phase.FINIE
            evts.append(("FIN",))
        return evts

    def resultat(self, reserve: int = 0) -> ResultatManche:
        return compter_manche(
            equipe(self.preneur),
            (self.points_cartes[0], self.points_cartes[1]),
            (self.plis_gagnes[0], self.plis_gagnes[1]),
            None if self.place_belote is None else equipe(self.place_belote),
            reserve,
        )
