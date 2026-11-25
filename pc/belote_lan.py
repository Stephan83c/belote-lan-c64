#!/usr/bin/env python3
"""BELOTE LAN — client pour PC (Windows, macOS, Linux), dans le terminal.

Il parle au même serveur que le C64 (protocole texte de SPEC.fr.md section 7) :
un joueur sur PC peut s'asseoir à la même table que des joueurs sur C64.

    python belote_lan.py                       serveur public, langue du système
    python belote_lan.py --serveur 192.168.1.55 --nom JEAN --langue fr
    python belote_lan.py --ascii               symboles S H C D si ♠ ♥ ♣ ♦ s'affichent mal

Bibliothèque standard seulement (Python 3.8 ou plus). Le terminal doit faire au
moins 80 x 24. Sous Windows, les couleurs passent par les séquences ANSI de la
console (Windows 10 et 11).
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import socket
import sys
import threading
import time
import unicodedata
from pathlib import Path

VERSION = "2.0"
SERVEUR_DEFAUT = "boombass.net"
PORT_DEFAUT = 6464
LARGEUR, HAUTEUR = 80, 24
NOM_MAX = 6
TCHAT_MAX = 30
DUREE_PLI = 1.5          # secondes pendant lesquelles le pli ramassé reste visible
DELAI_DERNIERE = 0.6     # la dernière carte part seule après ce délai (comme sur C64)
FICHIER_REGLAGES = Path.home() / ".belote-lan.json"

# ---------------------------------------------------------------------------
# Textes en quatre langues (comme le C64 : français, anglais, allemand, espagnol)
# ---------------------------------------------------------------------------

LANGUES = ["FR", "EN", "DE", "ES"]

TEXTES = {
    "langue": ("Français", "English", "Deutsch", "Español"),
    "figures": ("VDR", "JQK", "BDK", "JQK"),
    "oui": ("O", "Y", "J", "S"),
    "entree": ("Entrée", "Enter", "Eingabe", "Intro"),
    "echap": ("Échap", "Esc", "Esc", "Esc"),
    # Écran de connexion
    "connexion": ("Connexion", "Connection", "Verbindung", "Conexión"),
    "c_serveur": ("Serveur", "Server", "Server", "Servidor"),
    "c_nom": ("Nom", "Name", "Name", "Nombre"),
    # Choix du salon, une fois connecté (serveur à plusieurs salons)
    "s_titre": ("Choisissez un salon", "Choose a room", "Raum wählen", "Elija una sala"),
    "s_salon": ("Salon", "Room", "Raum", "Sala"),
    "s_joueurs": ("joueurs", "players", "Spieler", "jugadores"),
    "s_attente": ("en attente", "waiting", "wartet", "en espera"),
    "s_jeu": ("en jeu", "playing", "spielt", "jugando"),
    "s_aide": ("↑↓ choisir   1-9 salon   Entrée entrer   Esc retour",
               "↑↓ select   1-9 room   Enter join   Esc back",
               "↑↓ wählen   1-9 Raum   Eingabe beitreten   Esc zurück",
               "↑↓ elegir   1-9 sala   Intro entrar   Esc volver"),
    "c_langue": ("Langue", "Language", "Sprache", "Idioma"),
    "c_info": ("4 places : les bots complètent la table.", "4 seats: bots fill the empty ones.",
               "4 Plätze: Bots füllen freie Plätze.", "4 plazas: los bots completan la mesa."),
    "c_aide": ("↑↓ champ   ←→ langue   Entrée jouer   Échap quitter",
               "↑↓ field   ←→ language   Enter play   Esc quit",
               "↑↓ Feld   ←→ Sprache   Eingabe spielen   Esc Ende",
               "↑↓ campo   ←→ idioma   Intro jugar   Esc salir"),
    "m_nom": ("Entrez un nom : 1 à 6 lettres ou chiffres.", "Enter a name: 1 to 6 letters or digits.",
              "Name eingeben: 1 bis 6 Buchstaben oder Ziffern.",
              "Escriba un nombre: 1 a 6 letras o cifras."),
    "m_nom_bot": ("Nom réservé aux bots : choisissez-en un autre.",
                  "Name reserved for bots: choose another one.",
                  "Name für Bots reserviert: bitte einen anderen.",
                  "Nombre reservado a los bots: elija otro."),
    "m_nom_refuse": ("Nom refusé : choisissez-en un autre.", "Name refused: choose another one.",
                     "Name abgelehnt: bitte einen anderen.", "Nombre rechazado: elija otro."),
    "m_pleine": ("Table pleine (4 joueurs) : réessayez plus tard.",
                 "Table full (4 players): try again later.",
                 "Tisch voll (4 Spieler): später erneut versuchen.",
                 "Mesa llena (4 jugadores): inténtelo más tarde."),
    "m_connexion": ("Connexion…", "Connecting…", "Verbinde…", "Conectando…"),
    "m_impossible": ("Connexion impossible : ", "Cannot connect: ", "Verbindung fehlgeschlagen: ",
                     "Conexión imposible: "),
    "m_fermee": ("Connexion fermée par le serveur.", "Connection closed by the server.",
                 "Verbindung vom Server getrennt.", "Conexión cerrada por el servidor."),
    "m_reprendre": ("Entrée : revenir à la table (même nom, même place).",
                    "Enter: back to the table (same name, same seat).",
                    "Eingabe: zurück an den Tisch (gleicher Name, gleicher Platz).",
                    "Intro: volver a la mesa (mismo nombre, mismo sitio)."),
    "m_petit": ("Agrandissez la fenêtre : 80 x 24 au moins.", "Enlarge the window: at least 80 x 24.",
                "Fenster vergrößern: mindestens 80 x 24.", "Agrande la ventana: 80 x 24 como mínimo."),
    # Table
    "nous": ("NOUS", "US", "WIR", "NOS"),
    "eux": ("EUX", "THEM", "IHR", "ELLOS"),
    "chef": ("chef", "host", "Chef", "jefe"),
    "cible": ("cible", "target", "Ziel", "meta"),
    "donneur": ("Donneur : {}", "Dealer: {}", "Geber: {}", "Reparte: {}"),
    "atout": ("Atout", "Trump", "Trumpf", "Triunfo"),
    "pris_par": ("pris par", "taken by", "genommen von", "tomado por"),
    "plis": ("Plis", "Tricks", "Stiche", "Bazas"),
    "points": ("Points", "Points", "Punkte", "Puntos"),
    "retournee": ("Retournée", "Turned up", "Aufgedeckt", "Volteada"),
    "passe": ("passe", "pass", "passt", "pasa"),
    "prend": ("prend", "takes", "nimmt", "toma"),
    "prendre": ("Prendre", "Take", "Nehmen", "Tomar"),
    "passer": ("Passer", "Pass", "Passen", "Pasar"),
    "tour1": ("1er tour", "Round 1", "Runde 1", "Ronda 1"),
    "tour2": ("2e tour", "Round 2", "Runde 2", "Ronda 2"),
    "belote": ("Belote !", "Belote!", "Belote!", "¡Belote!"),
    "rebelote": ("Rebelote !", "Rebelote!", "Rebelote!", "¡Rebelote!"),
    "journal": ("Journal", "Log", "Protokoll", "Diario"),
    "vous": ("VOUS", "YOU", "DU", "TÚ"),
    "dernier_pli": ("Dernier pli", "Last trick", "Letzter Stich", "Última baza"),
    # Invites (ligne sous la table)
    "attente_chef": ("Vous êtes le chef : L pour lancer la partie.",
                     "You are the host: L to start the game.",
                     "Du bist Chef: L startet das Spiel.",
                     "Eres el jefe: L para empezar la partida."),
    "attente": ("En attente du lancement par le chef ({}).", "Waiting for the host ({}) to start.",
                "Warten auf den Start durch den Chef ({}).", "Esperando a que el jefe ({}) empiece."),
    "attente_regl": ("Cible {} points, inactivité {} min.", "Target {} points, idle timeout {} min.",
                     "Ziel {} Punkte, Inaktivität {} Min.", "Meta {} puntos, inactividad {} min."),
    "a_vous_ench": ("À vous d'annoncer : ←→ puis Entrée, ou 1-{}.",
                    "Your bid: ←→ then Enter, or 1-{}.",
                    "Du bietest: ←→ dann Eingabe, oder 1-{}.",
                    "Te toca pujar: ←→ e Intro, o 1-{}."),
    "a_vous_carte": ("À vous de jouer : ←→ puis Entrée, ou 1-8.",
                     "Your turn: ←→ then Enter, or 1-8.",
                     "Du bist dran: ←→ dann Eingabe, oder 1-8.",
                     "Te toca: ←→ e Intro, o 1-8."),
    "au_tour": ("Au tour de {}…", "{} to play…", "{} ist dran…", "Turno de {}…"),
    # Panneaux de fin
    "p_manche": ("La manche", "The round", "Die Runde", "La mano"),
    "p_rempli": ("Contrat rempli", "Contract made", "Vertrag erfüllt", "Contrato hecho"),
    "p_dedans": ("Dedans !", "Set!", "Durchgefallen!", "¡Fallado!"),
    "p_capot": ("Capot !", "Capot!", "Capot!", "¡Capot!"),
    "p_litige": ("Litige : réserve {}", "Tie: reserve {}", "Patt: Reserve {}", "Empate: reserva {}"),
    "p_reserve": ("+{} de réserve", "+{} from reserve", "+{} aus Reserve", "+{} de reserva"),
    "en_reserve": ("Réserve {}", "Reserve {}", "Reserve {}", "Reserva {}"),
    "p_total": ("Au total", "Overall", "Gesamt", "En total"),
    "p_suite": ("Suite dans {} s (Entrée : maintenant)", "Next round in {} s (Enter: now)",
                "Weiter in {} s (Eingabe: sofort)", "Sigue en {} s (Intro: ya)"),
    "p_victoire_nous": ("Victoire de NOUS !", "We win!", "Wir gewinnen!", "¡Ganamos nosotros!"),
    "p_victoire_eux": ("Victoire de EUX !", "They win!", "Ihr gewinnt!", "¡Ganan ellos!"),
    "p_nouvelle": ("Entrée : nouvelle partie", "Enter: new game", "Eingabe: neues Spiel",
                   "Intro: nueva partida"),
    "p_attend_chef": ("Le chef relance la partie.", "The host starts a new game.",
                      "Der Chef startet neu.", "El jefe empieza otra partida."),
    # Réglages du chef
    "reglages": ("Réglages", "Settings", "Optionen", "Ajustes"),
    "r_cible": ("Score cible", "Target score", "Zielpunkte", "Puntos meta"),
    "r_inactif": ("Inactivité (min)", "Idle timeout (min)", "Inaktivität (Min)", "Inactividad (min)"),
    "r_aide": ("↑↓ choisir    ←→ modifier", "↑↓ select    ←→ change",
               "↑↓ wählen    ←→ ändern", "↑↓ elegir    ←→ cambiar"),
    # Barre de touches
    "k_tchat": ("tchat", "chat", "Chat", "chat"),
    "k_dernier": ("dernier pli", "last trick", "letzter Stich", "última baza"),
    "k_aide": ("aide", "help", "Hilfe", "ayuda"),
    "k_quitter": ("quitter", "quit", "Ende", "salir"),
    "k_lancer": ("lancer", "start", "Start", "empezar"),
    "k_reglages": ("réglages", "settings", "Optionen", "ajustes"),
    "k_effacer": ("effacer", "wipe", "löschen", "borrar"),
    "k_suite": ("suite", "next", "weiter", "seguir"),
    "k_nouvelle": ("nouvelle partie", "new game", "neues Spiel", "nueva partida"),
    "k_jouer": ("jouer", "play", "spielen", "jugar"),
    "k_choisir": ("annoncer", "bid", "bieten", "pujar"),
    "k_envoyer": ("envoyer", "send", "senden", "enviar"),
    "k_annuler": ("annuler", "cancel", "Abbruch", "cancelar"),
    "k_retour": ("retour au jeu", "back to the game", "zurück zum Spiel", "volver al juego"),
    "q_quitter": ("Quitter la table ? {} oui, autre touche non",
                  "Leave the table? {} yes, any other key no",
                  "Tisch verlassen? {} ja, andere Taste nein",
                  "¿Dejar la mesa? {} sí, otra tecla no"),
    "q_effacer": ("Effacer la partie ? {} oui, autre touche non",
                  "Wipe the game? {} yes, any other key no",
                  "Spiel löschen? {} ja, andere Taste nein",
                  "¿Borrar la partida? {} sí, otra tecla no"),
    # Journal
    "j_commence": ("La partie commence.", "The game begins.", "Das Spiel beginnt.", "Empieza la partida."),
    "j_pli": ("{} remporte le pli.", "{} wins the trick.", "{} macht den Stich.", "{} gana la baza."),
    "j_passe": ("{} passe.", "{} passes.", "{} passt.", "{} pasa."),
    "j_prend": ("{} prend à {}.", "{} takes {}.", "{} nimmt {}.", "{} toma {}."),
    "j_second": ("Second tour d'enchères.", "Second round of bidding.", "Zweite Bietrunde.",
                 "Segunda ronda de subasta."),
    "j_redonne": ("Tout le monde passe : on redonne.", "Everyone passed: redeal.",
                  "Alle passen: neu geben.", "Todos pasan: se reparte."),
    "j_belote": ("{} : belote.", "{}: belote.", "{}: Belote.", "{}: belote."),
    "j_rebelote": ("{} : rebelote.", "{}: rebelote.", "{}: Rebelote.", "{}: rebelote."),
    "j_manche": ("Manche : NOUS {}, EUX {}.", "Round: US {}, THEM {}.", "Runde: WIR {}, IHR {}.",
                 "Mano: NOS {}, ELLOS {}."),
    "j_capot_nous": ("Capot pour NOUS !", "Capot for US!", "Capot für UNS!", "¡Capot para NOS!"),
    "j_capot_eux": ("Capot pour EUX.", "Capot for THEM.", "Capot für EUCH.", "Capot para ELLOS."),
    "j_litige": ("Litige : {} points en réserve.", "Tie: {} points held in reserve.",
                 "Patt: {} Punkte in Reserve.", "Empate: {} puntos en reserva."),
    "j_refus": ("Refusé : {}", "Refused: {}", "Abgelehnt: {}", "Rechazado: {}"),
    "j_bienvenue": ("Bienvenue, {} !", "Welcome, {}!", "Willkommen, {}!", "¡Bienvenido, {}!"),
    # Motifs des refus (ERR)
    "TROP LONG": ("ligne trop longue", "line too long", "Zeile zu lang", "línea demasiado larga"),
    "NOM": ("nom invalide", "invalid name", "ungültiger Name", "nombre no válido"),
    "CHEF SEUL": ("le chef seulement", "host only", "nur der Chef", "solo el jefe"),
    "PAS LANCEE": ("partie pas lancée", "game not started", "Spiel nicht gestartet",
                   "partida no iniciada"),
    "INCONNU": ("commande inconnue", "unknown command", "unbekannter Befehl", "orden desconocida"),
    "PAS TON TOUR": ("pas ton tour", "not your turn", "nicht dein Zug", "no es tu turno"),
    "COUP REFUSE": ("carte interdite", "card not allowed", "Karte nicht erlaubt", "carta no permitida"),
    "NOM RESERVE": ("nom réservé aux bots", "name reserved for bots", "Name für Bots reserviert",
                    "nombre reservado a bots"),
    "TABLE PLEINE": ("table pleine", "table full", "Tisch voll", "mesa llena"),
    "DEJA LANCEE": ("partie déjà lancée", "game already started", "Spiel läuft schon",
                    "partida ya iniciada"),
    "PARAM": ("réglage refusé", "invalid setting", "ungültige Einstellung", "ajuste no válido"),
    # Informations du serveur (INFO)
    "i_effacee": ("Partie effacée.", "Game wiped.", "Spiel gelöscht.", "Partida borrada."),
    "i_inactif": ("Inactif : votre place est rendue au bot.", "Idle: your seat goes to a bot.",
                  "Inaktiv: dein Platz geht an einen Bot.", "Inactivo: tu sitio pasa a un bot."),
    "i_nom_change": ("Nom changé en {}.", "Name changed to {}.", "Name geändert in {}.",
                     "Nombre cambiado a {}."),
    "i_reconnecte": ("{} est revenu.", "{} is back.", "{} ist zurück.", "{} ha vuelto."),
    "i_inactif_bot": ("{} inactif, remplacé par un bot.", "{} idle, replaced by a bot.",
                      "{} inaktiv, durch Bot ersetzt.", "{} inactivo, cambiado por un bot."),
    "i_bot": ("{} remplacé par un bot.", "{} replaced by a bot.", "{} durch Bot ersetzt.",
              "{} cambiado por un bot."),
    "i_reserve_nous": ("Réserve de {} points pour NOUS.", "Reserve of {} points for US.",
                       "Reserve von {} Punkten für UNS.", "Reserva de {} puntos para NOS."),
    "i_reserve_eux": ("Réserve de {} points pour EUX.", "Reserve of {} points for THEM.",
                      "Reserve von {} Punkten für EUCH.", "Reserva de {} puntos para ELLOS."),
}

REGLES = {
    "FR": [
        "32 cartes. Vous et NORD contre EST et OUEST.",
        "",
        "Enchères. 1er tour : prendre à la couleur",
        "retournée ou passer. 2e tour : choisir une autre",
        "couleur ou passer. Si tous passent, on redonne.",
        "",
        "Fournir la couleur demandée. À l'atout, monter si",
        "possible. Sans la couleur : couper si l'adversaire",
        "est maître, et surcouper si possible. Partenaire",
        "maître : jeu libre.",
        "",
        "Atout : V 20, 9 14, A 11, 10 10, R 4, D 3.",
        "Hors atout : A 11, 10 10, R 4, D 3, V 2.",
        "Dix de der 10. Belote-rebelote 20.",
        "",
        "Le preneur doit faire plus que la défense, sinon",
        "il est dedans : 162 à la défense. Capot : 252.",
    ],
    "EN": [
        "32 cards. You and NORTH against EAST and WEST.",
        "",
        "Bidding. Round 1: take the turned-up suit or",
        "pass. Round 2: choose another suit or pass.",
        "If everyone passes, the cards are dealt again.",
        "",
        "Follow suit. In trumps, play higher if you can.",
        "Unable to follow: trump if the opponents are",
        "winning, and overtrump if you can. Partner",
        "winning: play any card.",
        "",
        "Trumps: J 20, 9 14, A 11, 10 10, K 4, Q 3.",
        "Other suits: A 11, 10 10, K 4, Q 3, J 2.",
        "Last trick 10. Belote-rebelote 20.",
        "",
        "The taker must score more than the defence, or",
        "else goes set: 162 to the defence. Capot: 252.",
    ],
    "DE": [
        "32 Karten. Du und NORD gegen OST und WEST.",
        "",
        "Bieten. Runde 1: die aufgedeckte Farbe nehmen",
        "oder passen. Runde 2: eine andere Farbe wählen",
        "oder passen. Passen alle, wird neu gegeben.",
        "",
        "Farbe bedienen. Bei Trumpf höher spielen, wenn",
        "möglich. Farbe fehlt: stechen, wenn der Gegner",
        "vorn liegt, und überstechen, wenn möglich.",
        "Partner vorn: freie Wahl.",
        "",
        "Trumpf: B 20, 9 14, A 11, 10 10, K 4, D 3.",
        "Sonst: A 11, 10 10, K 4, D 3, B 2.",
        "Letzter Stich 10. Belote-Rebelote 20.",
        "",
        "Wer nimmt, braucht mehr Punkte als die Gegner,",
        "sonst gehen 162 an die Gegner. Capot: 252.",
    ],
    "ES": [
        "32 cartas. Tú y NORTE contra ESTE y OESTE.",
        "",
        "Subasta. Ronda 1: tomar el palo volteado o",
        "pasar. Ronda 2: elegir otro palo o pasar.",
        "Si todos pasan, se vuelve a repartir.",
        "",
        "Seguir el palo. En triunfo, subir si se puede.",
        "Sin el palo: fallar si el rival va ganando, y",
        "sobrefallar si se puede. Si gana el compañero:",
        "juego libre.",
        "",
        "Triunfo: J 20, 9 14, A 11, 10 10, K 4, Q 3.",
        "Resto: A 11, 10 10, K 4, Q 3, J 2.",
        "Última baza 10. Belote-rebelote 20.",
        "",
        "Quien toma debe hacer más puntos que la defensa;",
        "si no, los 162 van a la defensa. Capot: 252.",
    ],
}

INFOS_FIXES = {"PARTIE EFFACEE": "i_effacee", "INACTIF : PLACE RENDUE AU BOT": "i_inactif"}
INFOS_NOM = [  # (suffixe, clé) : « NOM SUFFIXE »
    (" INACTIF REMPLACE PAR UN BOT", "i_inactif_bot"),
    (" REMPLACE PAR UN BOT", "i_bot"),
    (" RECONNECTE", "i_reconnecte"),
]


class Langue:
    def __init__(self, indice: int = 0):
        self.i = indice

    @property
    def code(self) -> str:
        return LANGUES[self.i]

    def __call__(self, cle: str, *args) -> str:
        t = TEXTES[cle][self.i]
        return t.format(*args) if args else t


def langue_systeme() -> int:
    """Langue du système : variables LANG/LC_ALL, ou langue de l'interface Windows."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(var, "").lower()
        if v:
            break
    else:
        v = ""
        if os.name == "nt":
            try:
                import ctypes
                prim = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
                v = {0x0C: "fr", 0x09: "en", 0x07: "de", 0x0A: "es"}.get(prim, "en")
            except Exception:
                v = ""
    for i, code in enumerate(("fr", "en", "de", "es")):
        if v.startswith(code):
            return i
    return 1 if v else 0


def en_ascii(texte: str) -> str:
    """Majuscules ASCII imprimables : é devient E (le serveur ne connaît que l'ASCII)."""
    t = unicodedata.normalize("NFKD", texte)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return "".join(c if 32 <= ord(c) < 127 else "?" for c in t).upper()


# ---------------------------------------------------------------------------
# Règles (copie de server/belote/moteur.py, à garder en accord comme proto.c)
# ---------------------------------------------------------------------------

_ORDRE_NORMAL = (0, 1, 2, 4, 5, 6, 3, 7)   # 7 8 9 V D R 10 A
_ORDRE_ATOUT = (0, 1, 5, 6, 3, 7, 2, 4)    # 7 8 D R 10 A 9 V
_FORCE_NORMALE = {r: i for i, r in enumerate(_ORDRE_NORMAL)}
_FORCE_ATOUT = {r: i for i, r in enumerate(_ORDRE_ATOUT)}
_POINTS_NORMAUX = (0, 0, 0, 10, 2, 3, 4, 11)
_POINTS_ATOUT = (0, 0, 14, 10, 20, 3, 4, 11)


def force(c: int, atout: int) -> int:
    return (_FORCE_ATOUT if c // 8 == atout else _FORCE_NORMALE)[c % 8]


def points_carte(c: int, atout: int) -> int:
    return (_POINTS_ATOUT if c // 8 == atout else _POINTS_NORMAUX)[c % 8]


def gagnant_pli(pli: list, atout: int) -> int:
    demandee = pli[0][1] // 8

    def cle(coup):
        c = coup[1]
        if c // 8 == atout:
            return (2, force(c, atout))
        if c // 8 == demandee:
            return (1, force(c, atout))
        return (0, 0)

    return max(pli, key=cle)[0]


def coups_legaux(main: list, pli: list, atout: int, place: int) -> list:
    """Cartes autorisées (SPEC 5.3) ; pli = liste ordonnée de (place, carte)."""
    if not pli:
        return list(main)
    demandee = pli[0][1] // 8
    atouts = [c for c in main if c // 8 == atout]
    plus_fort = max((force(c, atout) for _, c in pli if c // 8 == atout), default=-1)
    surcoupes = [c for c in atouts if force(c, atout) > plus_fort]
    if demandee == atout:
        return surcoupes or atouts or list(main)
    en_couleur = [c for c in main if c // 8 == demandee]
    if en_couleur:
        return en_couleur
    if gagnant_pli(pli, atout) == (place + 2) % 4 or not atouts:
        return list(main)
    if surcoupes:
        return surcoupes
    return atouts  # impossible de surcouper : atout plus faible quand même (v2.1)


# ---------------------------------------------------------------------------
# État de la partie, tenu à jour par les messages du serveur (sans affichage)
# ---------------------------------------------------------------------------

ATTENTE, LANCEE, EN_COURS, FIN_MANCHE, FIN_PARTIE = (
    "ATTENTE", "LANCEE", "EN COURS", "FIN MANCHE", "FIN PARTIE")


def _int(t: str, defaut: int = -1) -> int:
    try:
        return int(t)
    except ValueError:
        return defaut


class Partie:
    def __init__(self):
        self.moi = -1
        self.noms = ["BOT"] * 4
        self.humains = [False] * 4
        self.chef = -1
        self.etat = ATTENTE
        self.cible = 1000
        self.inactif = 3
        self.scores = [0, 0]
        self.en_reserve = 0         # réserve en attente (litiges), affichée dans le bandeau
        self.gagnant = None
        self.suite_fin = None       # instant (monotonic) de la manche suivante
        self.journal = []           # (clé, arguments) ou ("tchat", nom, texte, place)
        self.erreur_join = None     # ERR reçu avant BIENVENUE
        self._rattrapage = False    # état complet envoyé après BIENVENUE, jusqu'au TOUR
        self.cloche = False         # un humain arrive ou part : cloche du terminal au prochain dessin
        self.sieges_vus = set()     # places déjà reçues depuis BIENVENUE
        self.nouvelle_donne()

    def nouvelle_donne(self) -> None:
        self.donneur = -1
        self.main = []
        self.nbcartes = [0] * 4
        self.retournee = None
        self.ench_tour = 0
        self.tour = -1
        self.preneur = None
        self.atout = None
        self.pli = []               # (place, carte) dans l'ordre
        self.ramasse = None         # (pli, gagnant, instant) : pli qui vient d'être gagné
        self.dernier = None         # (pli, gagnant)
        self.annonces = [None] * 4  # bulle près du nom : ("passe",) / ("prend", c) / ("belote",)
        self.plis = [0, 0]
        self.points = [0, 0]        # None : manche prise en cours (reconnexion)
        self.nb_plis = 0
        self.manche = None
        self.capot = None
        self.litige = 0
        self.reserve = None

    # -- outils
    def nom(self, p: int) -> str:
        if not 0 <= p <= 3:
            return "?"
        # Bots à style (serveur v2.1) : leur nom ; serveur v2.0 : tous « BOT », numérotés par place.
        return "BOT%d" % (p + 1) if not self.humains[p] and self.noms[p] == "BOT" else self.noms[p]

    def equipe(self, p: int) -> int:
        return p % 2

    def nous(self) -> int:
        return max(self.moi, 0) % 2

    def suis_chef(self) -> bool:
        return self.moi >= 0 and self.chef == self.moi

    def a_moi(self) -> bool:
        return self.etat == EN_COURS and self.tour == self.moi and self.moi >= 0

    def jouables(self) -> list:
        if not self.a_moi() or self.atout is None:
            return []
        return coups_legaux(self.main, self.pli, self.atout, self.moi)

    def choix_encheres(self) -> list:
        """Enchères possibles : [("ENCH", c)..., ("PASSE",)]."""
        if not self.a_moi() or self.atout is not None or self.retournee is None:
            return []
        rc = self.retournee // 8
        if self.ench_tour == 1:
            couleurs = [rc]
        else:
            couleurs = [c for c in range(4) if c != rc]
        return [("ENCH", c) for c in couleurs] + [("PASSE",)]

    def _j(self, *entree) -> None:
        self.journal.append(entree)
        del self.journal[:-200]

    # -- réception
    def recevoir(self, ligne: str) -> None:
        mot, _, reste = ligne.partition(" ")
        a = reste.split()
        n = [_int(x) for x in a]
        if mot == "BIENVENUE" and len(a) >= 2:
            self.noms[n[1]] = a[0]
            self.humains[n[1]] = True
            self.moi = n[1]
            self._rattrapage = True
            self.sieges_vus = set()
            self._j("j_bienvenue", a[0])
        elif mot == "SIEGE" and len(a) >= 3 and 0 <= n[0] <= 3:
            # Un humain arrive ou part (pas soi, pas l'état reçu à la connexion) : cloche.
            if n[0] in self.sieges_vus and n[0] != self.moi and self.humains[n[0]] != (a[1] == "H"):
                self.cloche = True
            self.sieges_vus.add(n[0])
            self.humains[n[0]] = a[1] == "H"
            self.noms[n[0]] = a[2]
        elif mot == "CHEF" and a:
            self.chef = n[0]
        elif mot == "ETAT":
            self._etat(reste)
        elif mot == "PARAM" and len(a) == 2:
            if a[0] == "CIBLE":
                self.cible = n[1]
            elif a[0] == "INACTIF":
                self.inactif = n[1]
        elif mot == "DONNEUR" and a:
            self.donneur = n[0]
        elif mot == "MAIN":
            self.main = [c for c in n if 0 <= c <= 31]
        elif mot == "NBCARTES" and len(a) == 4:
            self.nbcartes = n
        elif mot == "RETOURNE" and a:
            self.retournee = n[0]
        elif mot == "ENCHERES" and a:
            self.ench_tour = n[0]
            if n[0] == 2 and not self._rattrapage:
                self.annonces = [None] * 4
                self._j("j_second")
        elif mot == "TOUR" and a:
            self.tour = n[0]
            self._rattrapage = False
        elif mot == "PASSE" and a:
            self.annonces[n[0]] = ("passe",)
            self._j("j_passe", self.nom(n[0]))
        elif mot == "PREND" and len(a) >= 2:
            self.preneur, self.atout = n[0], n[1]
            self.annonces = [None] * 4
            self.annonces[n[0]] = ("prend", n[1])
            if self._rattrapage:
                self.points = None
                self.plis = None
            else:
                self._j("j_prend", self.nom(n[0]), ("couleur", n[1]))
        elif mot == "JOUE" and len(a) >= 2:
            p, c = n[0], n[1]
            if len(self.pli) >= 4:
                self.pli = []
            self.pli.append((p, c))
            self.ramasse = None
            if 0 <= p <= 3 and self.nbcartes[p] > 0:
                self.nbcartes[p] -= 1
            if p == self.tour:
                self.tour = -1
        elif mot in ("BELOTE", "REBELOTE") and a:
            self.annonces[n[0]] = (mot.lower(),)
            self._j("j_" + mot.lower(), self.nom(n[0]))
        elif mot == "PLI" and a:
            self._pli(n[0])
        elif mot == "PLICOURS" and len(a) == 4:
            self._plicours(n)
        elif mot == "CAPOT" and a:
            self.capot = n[0]
            self._j("j_capot_nous" if n[0] == self.nous() else "j_capot_eux")
        elif mot == "LITIGE" and a:
            self.litige = n[0]
            self.en_reserve += n[0]   # serveur v2.0 : pas de message RESERVE
            self._j("j_litige", n[0])
        elif mot == "RESERVE" and a:
            self.en_reserve = n[0]
        elif mot == "MANCHE" and len(a) == 2:
            self.manche = n
            self._j("j_manche", n[self.nous()], n[1 - self.nous()])
        elif mot == "SCORE" and len(a) == 2:
            self.scores = n
        elif mot == "GAGNANT" and a:
            self.gagnant = n[0]
            self.en_reserve = 0       # réserve non attribuée : perdue
        elif mot == "SUITE" and a:
            self.suite_fin = time.monotonic() + max(n[0], 0)
        elif mot == "REDONNE":
            self._j("j_redonne")
        elif mot == "TCHAT":
            nom, _, texte = reste.partition(" ")
            place = next((p for p in range(4) if self.humains[p] and self.noms[p] == nom), -1)
            self._j("tchat", nom, texte, place)
        elif mot == "INFO":
            self._info(reste)
        elif mot == "ERR":
            if self.moi < 0:
                self.erreur_join = reste
            else:
                self._j("j_refus", ("err", reste))

    def _etat(self, etat: str) -> None:
        self.etat = etat
        if etat == EN_COURS:            # nouvelle donne (après REDONNE aussi)
            self.nouvelle_donne()
            self.suite_fin = None
            self.gagnant = None
        elif etat == LANCEE:
            self.gagnant = None
            self.nouvelle_donne()
            if not self._rattrapage:
                self._j("j_commence")
        elif etat == ATTENTE:
            self.gagnant = None
            self.scores = [0, 0]
            self.nouvelle_donne()
        elif etat == FIN_MANCHE:
            self.tour = -1
        elif etat == FIN_PARTIE:
            self.tour = -1
            self.suite_fin = None

    def _pli(self, gagnant: int) -> None:
        pli = list(self.pli)
        if self.points is not None and self.atout is not None:
            camp = gagnant % 2
            self.points[camp] += sum(points_carte(c, self.atout) for _, c in pli)
            self.plis[camp] += 1
            self.nb_plis += 1
            if self.nb_plis == 8:
                self.points[camp] += 10
        self.ramasse = (pli, gagnant, time.monotonic())
        self.dernier = (pli, gagnant)
        self.pli = []
        self._j("j_pli", self.nom(gagnant))

    def _plicours(self, cartes: list) -> None:
        """Reconnexion : le pli en cours, par place ; l'ordre se déduit du joueur suivant
        (le TOUR qui suit), donc on range les cartes à partir de la place après un trou."""
        posees = [p for p in range(4) if cartes[p] >= 0]
        if not posees:
            self.pli = []
            return
        # L'entame est la place posée dont la précédente n'a pas joué.
        entame = next((p for p in posees if cartes[(p - 1) % 4] < 0), posees[0])
        self.pli = [((entame + i) % 4, cartes[(entame + i) % 4]) for i in range(len(posees))]

    def _info(self, texte: str) -> None:
        if texte in INFOS_FIXES:
            self._j(INFOS_FIXES[texte])
            if texte == "PARTIE EFFACEE":
                self.scores = [0, 0]
            return
        if texte.startswith("NOM CHANGE EN "):
            self._j("i_nom_change", texte[14:])
            return
        if texte.startswith("RESERVE ") and " POUR EQUIPE " in texte:
            pts, _, eq = texte[8:].partition(" POUR EQUIPE ")
            self.reserve = (_int(eq), _int(pts))
            self.en_reserve = 0
            self._j("i_reserve_nous" if _int(eq) == self.nous() else "i_reserve_eux", pts)
            return
        for suffixe, cle in INFOS_NOM:
            if texte.endswith(suffixe):
                self._j(cle, texte[: -len(suffixe)])
                return
        self._j("brut", texte)


# ---------------------------------------------------------------------------
# Réseau : un fil lit les lignes du serveur et les dépose dans la file d'événements
# ---------------------------------------------------------------------------

class Reseau:
    def __init__(self, hote: str, port: int, file: queue.Queue):
        self.sock = socket.create_connection((hote, port), timeout=8)
        self.sock.settimeout(None)
        self.file = file
        self.verrou = threading.Lock()
        self.ouvert = True
        threading.Thread(target=self._lire, daemon=True).start()

    def _lire(self) -> None:
        tampon = b""
        try:
            while True:
                bloc = self.sock.recv(4096)
                if not bloc:
                    break
                tampon += bloc
                while b"\n" in tampon:
                    ligne, tampon = tampon.split(b"\n", 1)
                    self.file.put(("ligne", self, ligne.rstrip(b"\r").decode("ascii", "replace")))
        except OSError:
            pass
        self.file.put(("ferme", self, None))

    def envoyer(self, ligne: str) -> None:
        donnees = en_ascii(ligne)[:63].encode("ascii") + b"\n"
        with self.verrou:
            try:
                self.sock.sendall(donnees)
            except OSError:
                pass

    def fermer(self) -> None:
        self.ouvert = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()


# ---------------------------------------------------------------------------
# Clavier : un fil lit les touches (msvcrt sous Windows, termios ailleurs)
# ---------------------------------------------------------------------------

_SEQ = {
    "[A": "UP", "[B": "DOWN", "[C": "RIGHT", "[D": "LEFT", "OA": "UP", "OB": "DOWN",
    "OC": "RIGHT", "OD": "LEFT", "OP": "F1", "OQ": "F2", "OR": "F3", "OS": "F4",
    "[11~": "F1", "[12~": "F2", "[13~": "F3", "[14~": "F4", "[15~": "F5", "[17~": "F6",
    "[18~": "F7", "[19~": "F8", "[[A": "F1", "[[B": "F2", "[[C": "F3", "[[D": "F4", "[[E": "F5",
}
_WIN = {72: "UP", 80: "DOWN", 75: "LEFT", 77: "RIGHT", 59: "F1", 60: "F2", 61: "F3", 62: "F4",
        63: "F5", 64: "F6", 65: "F7", 66: "F8"}


def decouper_touches(texte: str) -> list:
    """Découpe ce qu'a envoyé un terminal Unix en touches."""
    touches = []
    i = 0
    while i < len(texte):
        c = texte[i]
        if c == "\x1b":
            if i + 1 < len(texte) and texte[i + 1] in "[O":
                j = i + 2
                if texte[i + 1] == "[" and j < len(texte) and texte[j] == "[":
                    j += 1
                while j < len(texte) and not ("@" <= texte[j] <= "~" and texte[j] != "["):
                    j += 1
                seq = texte[i + 1:j + 1]
                touches.append(_SEQ.get(seq, "?"))
                i = j + 1
                continue
            touches.append("ESC")
        elif c in "\r\n":
            touches.append("ENTER")
        elif c in "\x7f\x08":
            touches.append("BACK")
        elif c == "\t":
            touches.append("TAB")
        elif c == "\x03":
            touches.append("CTRL_C")
        elif c >= " ":
            touches.append(c)
        i += 1
    return touches


class Clavier:
    def __init__(self, file: queue.Queue):
        self.file = file
        self.ancien = None
        if os.name == "nt":
            threading.Thread(target=self._windows, daemon=True).start()
        else:
            import termios
            import tty
            self.fd = sys.stdin.fileno()
            self.ancien = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
            threading.Thread(target=self._unix, daemon=True).start()

    def _windows(self) -> None:
        import msvcrt
        while True:
            c = msvcrt.getwch()
            if c in ("\x00", "\xe0"):
                t = _WIN.get(ord(msvcrt.getwch()))
            elif c == "\r":
                t = "ENTER"
            elif c == "\x08":
                t = "BACK"
            elif c == "\x1b":
                t = "ESC"
            elif c == "\t":
                t = "TAB"
            elif c == "\x03":
                t = "CTRL_C"
            else:
                t = c if c >= " " else None
            if t:
                self.file.put(("touche", None, t))

    def _unix(self) -> None:
        import codecs
        dec = codecs.getincrementaldecoder("utf-8")("replace")
        while True:
            try:
                bloc = os.read(self.fd, 64)
            except OSError:
                return
            if not bloc:
                return
            for t in decouper_touches(dec.decode(bloc)):
                self.file.put(("touche", None, t))

    def restaurer(self) -> None:
        if self.ancien is not None:
            import termios
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.ancien)


# ---------------------------------------------------------------------------
# Écran : une grille 80 x 24 de cases (caractère, style) envoyée d'un bloc
# ---------------------------------------------------------------------------

# Styles : séquences SGR (16 couleurs, comprises partout, Windows compris)
S_TAPIS = "0;97;42"
S_TAPIS_TEXTE = "0;1;97;42"
S_TAPIS_DOUX = "0;30;42"
S_BANDEAU = "0;97;40"
S_TOUCHE = "0;1;93;40"
S_JOURNAL = "0;37;40"
S_JOURNAL_TITRE = "0;1;97;40"
S_INFO = "0;93;40"
S_TCHAT = "0;96;40"
S_REFUS = "0;91;40"
S_CARTE_N = "0;30;107"
S_CARTE_R = "0;31;107"
S_GRISE_N = "0;30;47"
S_GRISE_R = "0;31;47"
S_EQUIPE = ("0;1;97;44", "0;1;97;41")    # NOUS/EUX selon l'équipe absolue : P0+P2 bleu, P1+P3 rouge
S_EQUIPE_TXT = ("0;1;94;107", "0;1;91;107")
S_TOUR = "0;1;30;103"
S_BULLE = "0;1;93;42"
S_PANNEAU = "0;30;107"
S_PANNEAU_TITRE = "0;1;30;107"
S_CHOIX = "0;1;97;40"
S_CHOIX_SEL = "0;1;30;107"
S_NUM = "0;1;97;42"
S_NUM_SEL = "0;1;30;107"
S_MSG_ERR = "0;1;97;41"
S_MSG_INFO = "0;1;93;42"


class Ecran:
    def __init__(self):
        self.vider()

    def vider(self, style: str = S_TAPIS) -> None:
        self.car = [[" "] * LARGEUR for _ in range(HAUTEUR)]
        self.sty = [[style] * LARGEUR for _ in range(HAUTEUR)]

    def ecrire(self, x: int, y: int, texte: str, style: str) -> None:
        if not 0 <= y < HAUTEUR:
            return
        for i, c in enumerate(texte):
            if 0 <= x + i < LARGEUR:
                self.car[y][x + i] = c
                self.sty[y][x + i] = style

    def remplir(self, x: int, y: int, l: int, h: int, style: str) -> None:
        for j in range(h):
            self.ecrire(x, y + j, " " * l, style)

    def centre(self, x0: int, l: int, y: int, texte: str, style: str) -> None:
        texte = texte[:l]
        self.ecrire(x0 + (l - len(texte)) // 2, y, texte, style)

    def rendu(self, dx: int, dy: int) -> str:
        sortie = []
        for y in range(HAUTEUR):
            sortie.append("\x1b[%d;%dH" % (y + 1 + dy, 1 + dx))
            style = None
            for x in range(LARGEUR):
                if self.sty[y][x] != style:
                    style = self.sty[y][x]
                    sortie.append("\x1b[" + style + "m")
                sortie.append(self.car[y][x])
        sortie.append("\x1b[0m")
        return "".join(sortie)


# ---------------------------------------------------------------------------
# Application : écran de connexion puis table de jeu
# ---------------------------------------------------------------------------

# Disposition de la table (colonnes 0 à 54 ; le journal occupe 56 à 79)
TABLE_L = 55
CENTRE = 27
# par place relative : 0 SUD, 1 EST, 2 NORD, 3 OUEST
CARTE_XY = {0: (25, 9), 1: (34, 6), 2: (25, 3), 3: (16, 6)}
JOURNAL_X = 56
JOURNAL_L = LARGEUR - JOURNAL_X


class App:
    def __init__(self, args):
        self.file = queue.Queue()
        self.ecran = Ecran()
        self.tr = Langue(0)
        self.symboles = "SHCD" if args.ascii else "♠♥♣♦"
        reglages = self._lire_reglages()
        langue = args.langue or reglages.get("langue")
        self.tr.i = LANGUES.index(langue.upper()) if langue and langue.upper() in LANGUES \
            else langue_systeme()
        self.champs = [args.serveur or reglages.get("serveur") or SERVEUR_DEFAUT,
                       (args.nom or reglages.get("nom") or "")[:NOM_MAX].upper()]
        self.champ = 1
        self.message = ""
        self.message_style = S_MSG_ERR
        self.reseau = None
        self.partie = None
        # Salons : liste reçue [(humains, en jeu)], None hors de l'écran des salons
        self.salons = None
        self.attente_salons = False   # SALONS envoyé, liste pas encore complète
        self.salons_recus = []
        self.nb_salons = 0
        self.sal_sel = 0
        self.salon = 0                # salon demandé dans JOIN (0 : JOIN sans numéro)
        self.en_jeu = False
        self.perdue = False
        self.fin = False
        # interface en jeu
        self.sel = 0
        self.ench_sel = 0
        self.tchat = None          # texte en cours de saisie, None hors saisie
        self.question = None       # "quitter" / "effacer"
        self.aide = False
        self.voir_dernier = False
        self.regl = None           # [sélection, cible, inactif]
        self.derniere_a = None     # instant d'envoi automatique de la dernière carte
        self.taille = None
        self.sale = True
        self.seconde = -1
        self.auto = args.auto

    # -- réglages mémorisés (serveur, nom, langue)
    @staticmethod
    def _lire_reglages() -> dict:
        try:
            return json.loads(FICHIER_REGLAGES.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _ecrire_reglages(self) -> None:
        try:
            FICHIER_REGLAGES.write_text(json.dumps(
                {"serveur": self.champs[0], "nom": self.champs[1], "langue": self.tr.code}),
                encoding="utf-8")
        except OSError:
            pass

    # -- boucle principale
    def executer(self) -> None:
        while not self.fin:
            try:
                ev = self.file.get(timeout=0.1)
            except queue.Empty:
                ev = None
            while ev is not None:
                self.traiter(ev)
                try:
                    ev = self.file.get_nowait()
                except queue.Empty:
                    ev = None
            self.minuterie()
            self.dessiner()

    def traiter(self, ev) -> None:
        genre, source, valeur = ev
        self.sale = True
        if genre == "touche":
            if valeur == "CTRL_C":
                self.quitter()
            elif self.en_jeu:
                self.touche_jeu(valeur)
            else:
                self.touche_connexion(valeur)
        elif genre == "ligne" and source is self.reseau:
            self.ligne(valeur)
        elif genre == "ferme" and source is self.reseau:
            self.reseau = None
            self.salons, self.attente_salons = None, False
            if self.fin:
                return
            if self.en_jeu:
                self.en_jeu = False
                self.perdue = True
                self.message = self.tr("m_fermee")
            elif self.partie and self.partie.erreur_join:
                self.erreur_join(self.partie.erreur_join)
            else:
                self.message = self.tr("m_fermee")
            self.message_style = S_MSG_ERR

    def minuterie(self) -> None:
        p = self.partie
        if not self.en_jeu or p is None:
            return
        maintenant = time.monotonic()
        if p.ramasse and maintenant - p.ramasse[2] >= DUREE_PLI:
            p.ramasse = None
            self.sale = True
        if self.derniere_a is not None and maintenant >= self.derniere_a:
            self.derniere_a = None
            jouables = p.jouables()
            if len(p.main) == 1 and jouables:
                self.jouer(jouables[0])
        if int(maintenant) != self.seconde:
            self.seconde = int(maintenant)
            if p.suite_fin is not None:
                self.sale = True

    def quitter(self) -> None:
        if self.reseau:
            self.reseau.envoyer("LEAVE")
            self.reseau.fermer()
            self.reseau = None
        self.fin = True

    # -- connexion
    def touche_connexion(self, t: str) -> None:
        if self.salons is not None or self.attente_salons:
            self.touche_salons(t)
            return
        if t == "ESC":
            self.quitter()
        elif t in ("UP", "DOWN", "TAB"):
            self.champ = (self.champ + (-1 if t == "UP" else 1)) % 3
        elif t in ("LEFT", "RIGHT", "F1"):          # dans tous les champs, comme sur C64
            self.tr.i = (self.tr.i + (-1 if t == "LEFT" else 1)) % len(LANGUES)
        elif t == "ENTER":
            self.connecter()
        elif t == "BACK" and self.champ < 2:
            self.champs[self.champ] = self.champs[self.champ][:-1]
            self.perdue = False
        elif len(t) == 1 and self.champ < 2:
            if self.champ == 0 and len(self.champs[0]) < 40 and (t.isalnum() or t in ".-:[]"):
                self.champs[0] += t
            elif self.champ == 1 and len(self.champs[1]) < NOM_MAX and t.isascii() and t.isalnum():
                self.champs[1] += t.upper()
            self.perdue = False

    def connecter(self) -> None:
        nom = self.champs[1]
        if not nom or not (nom.isascii() and nom.isalnum()):
            self.message, self.message_style, self.champ = self.tr("m_nom"), S_MSG_ERR, 1
            return
        if nom.startswith("BOT") and (nom == "BOT" or nom[3:].isdigit()):
            self.message, self.message_style, self.champ = self.tr("m_nom_bot"), S_MSG_ERR, 1
            return
        hote, port = self.champs[0].strip(), PORT_DEFAUT
        if hote.count(":") == 1:
            hote, _, p = hote.partition(":")
            port = _int(p, PORT_DEFAUT)
        hote = hote.strip("[]")
        self.message, self.message_style = self.tr("m_connexion"), S_MSG_INFO
        self.dessiner(force=True)
        try:
            self.reseau = Reseau(hote, port, self.file)
        except OSError as e:
            self.message = self.tr("m_impossible") + (e.strerror or str(e))
            self.message_style = S_MSG_ERR
            return
        self._ecrire_reglages()
        self.partie = Partie()
        self.perdue = False
        self.sel = self.ench_sel = 0
        self.tchat = self.question = self.regl = None
        self.aide = self.voir_dernier = False
        self.demander_salons()

    # -- salons
    def demander_salons(self) -> None:
        self.attente_salons, self.salons_recus, self.nb_salons = True, [], 0
        self.reseau.envoyer("SALONS")

    def rejoindre(self, n: int) -> None:
        """JOIN dans le salon n (1 à 9), ou sans numéro (n = 0, ancien serveur)."""
        self.salon, self.salons = n, None
        self.message, self.message_style = self.tr("m_connexion"), S_MSG_INFO
        self.reseau.envoyer("JOIN " + self.champs[1] + (" %d" % n if n else ""))

    def touche_salons(self, t: str) -> None:
        if t == "ESC":                              # retour à l'écran de connexion
            if self.reseau:
                self.reseau.envoyer("LEAVE")
                self.reseau.fermer()
                self.reseau = None
            self.salons, self.attente_salons, self.message = None, False, ""
        elif self.salons is None:
            return
        elif t in ("UP", "DOWN"):
            self.sal_sel = (self.sal_sel + (-1 if t == "UP" else 1)) % len(self.salons)
        elif t in ("LEFT", "RIGHT", "F1"):
            self.tr.i = (self.tr.i + (-1 if t == "LEFT" else 1)) % len(LANGUES)
        elif t == "ENTER":
            self.rejoindre(self.sal_sel + 1)
        elif len(t) == 1 and "1" <= t <= str(len(self.salons)):
            self.rejoindre(int(t))

    def ligne_salons(self, ligne: str) -> bool:
        """Réponse à SALONS ; True si la ligne est traitée ici."""
        mot, _, reste = ligne.partition(" ")
        if mot == "SALONS":
            self.nb_salons = min(_int(reste, 0), 9)
            if not self.nb_salons:
                self.attente_salons = False
                self.rejoindre(0)
        elif mot == "SALON":
            a = reste.split(" ", 2)
            self.salons_recus.append((_int(a[1], 0) if len(a) > 1 else 0,
                                      len(a) > 2 and a[2] != ATTENTE))
            if len(self.salons_recus) >= self.nb_salons:
                self.attente_salons = False
                self.salons = self.salons_recus[:self.nb_salons]
                self.sal_sel = min(self.sal_sel, len(self.salons) - 1)
                if self.auto:
                    self.rejoindre(1)
        elif mot == "ERR":
            # Serveur d'avant les salons : il refuse SALONS (ERR NOM) ; JOIN sans numéro.
            self.attente_salons = False
            self.rejoindre(0)
        else:
            return False
        return True

    def erreur_join(self, err: str) -> None:
        cle = {"NOM RESERVE": "m_nom_bot", "TABLE PLEINE": "m_pleine"}.get(err, "m_nom_refuse")
        self.message, self.message_style, self.champ = self.tr(cle), S_MSG_ERR, 1
        if self.reseau:
            self.reseau.fermer()
            self.reseau = None

    # -- messages du serveur
    def ligne(self, ligne: str) -> None:
        p = self.partie
        if p is None:
            return
        if self.attente_salons and self.ligne_salons(ligne):
            return
        avant_tour = p.tour
        p.recevoir(ligne)
        mot = ligne.split(" ", 1)[0]
        if mot == "BIENVENUE":
            self.en_jeu = True
            self.message = ""
            self.champs[1] = p.nom(p.moi)
        elif mot == "ERR" and p.moi < 0:
            if self.salon and p.erreur_join == "TABLE PLEINE":
                # Salon rempli entre-temps : la connexion reste ouverte, la liste à jour.
                p.erreur_join = None
                self.message, self.message_style = self.tr("m_pleine"), S_MSG_ERR
                self.demander_salons()
                return
            self.erreur_join(p.erreur_join)
            return
        elif mot == "TOUR" and p.a_moi() and avant_tour != p.moi:
            self.debut_tour()
        elif mot == "ETAT" and p.etat in (FIN_MANCHE, FIN_PARTIE, ATTENTE):
            self.voir_dernier = False
        if self.auto:
            self.jouer_auto()

    def debut_tour(self) -> None:
        p = self.partie
        choix = p.choix_encheres()
        if choix:
            self.ench_sel = len(choix) - 1          # PASSE par défaut, comme sur C64
            return
        jouables = p.jouables()
        if jouables:
            if self.sel >= len(p.main) or p.main[self.sel] not in jouables:
                self.sel = p.main.index(jouables[0])
            if len(p.main) == 1:
                self.derniere_a = time.monotonic() + DELAI_DERNIERE

    def jouer_auto(self) -> None:
        """--auto : joue seul (essais et démonstrations)."""
        p = self.partie
        if p.a_moi():
            choix = p.choix_encheres()
            if choix:
                self.envoyer_enchere(choix[-1])
            elif p.jouables():
                self.jouer(p.jouables()[0])

    # -- actions
    def envoyer(self, ligne: str) -> None:
        if self.reseau:
            self.reseau.envoyer(ligne)

    def jouer(self, c: int) -> None:
        p = self.partie
        self.envoyer("COUP %d" % c)
        p.tour = -1
        self.derniere_a = None

    def envoyer_enchere(self, choix) -> None:
        self.envoyer("PASSE" if choix[0] == "PASSE" else "ENCH %d" % choix[1])
        self.partie.tour = -1

    def touche_jeu(self, t: str) -> None:
        p = self.partie
        if self.question:
            if len(t) == 1 and t.upper() in "OYJS":
                if self.question == "quitter":
                    self.quitter()
                else:
                    self.envoyer("RAZ")
            self.question = None
            return
        if self.tchat is not None:
            if t == "ENTER":
                if self.tchat.strip():
                    self.envoyer("TCHAT " + self.tchat.strip())
                self.tchat = None
            elif t in ("ESC", "F3"):
                self.tchat = None
            elif t == "BACK":
                self.tchat = self.tchat[:-1]
            elif len(t) == 1 and len(self.tchat) < TCHAT_MAX:
                self.tchat += t
            return
        if self.regl is not None:
            self.touche_reglages(t)
            return
        if self.aide:
            self.aide = False
            return
        if self.voir_dernier:
            self.voir_dernier = False
            return
        u = t.upper() if len(t) == 1 else t
        if u in ("Q", "F7", "ESC"):
            self.question = "quitter"
        elif u in ("T", "F3"):
            self.tchat = ""
        elif u in ("A", "?", "F8", "H"):
            self.aide = True
        elif u in ("D", "F6") and p.dernier and p.etat == EN_COURS:
            self.voir_dernier = True
        elif u in ("L", "F2") and p.etat == ATTENTE:
            self.envoyer("LANCER")
        elif u in ("R", "F1") and p.etat == ATTENTE and p.suis_chef():
            self.regl = [0, p.cible, p.inactif]
        elif u in ("E", "F4") and p.etat != ATTENTE and p.suis_chef():
            self.question = "effacer"
        elif u in ("ENTER", " ", "F5") and p.etat in (FIN_MANCHE, FIN_PARTIE):
            if p.etat == FIN_MANCHE or p.suis_chef():
                self.envoyer("REJOUER")
        elif p.a_moi():
            self.touche_action(u)

    def touche_action(self, u: str) -> None:
        p = self.partie
        choix = p.choix_encheres()
        if choix:
            if u == "LEFT":
                self.ench_sel = (self.ench_sel - 1) % len(choix)
            elif u == "RIGHT":
                self.ench_sel = (self.ench_sel + 1) % len(choix)
            elif u in ("ENTER", " "):
                self.envoyer_enchere(choix[self.ench_sel % len(choix)])
            elif u.isdigit() and 1 <= int(u) <= len(choix):
                self.envoyer_enchere(choix[int(u) - 1])
            return
        jouables = p.jouables()
        if not jouables:
            return
        indices = [i for i, c in enumerate(p.main) if c in jouables]
        if u in ("LEFT", "RIGHT"):
            pos = indices.index(self.sel) if self.sel in indices else 0
            pos = (pos + (1 if u == "RIGHT" else -1)) % len(indices)
            self.sel = indices[pos]
        elif u in ("ENTER", " ", "UP"):
            if self.sel in indices:
                self.jouer(p.main[self.sel])
        elif u.isdigit() and 1 <= int(u) <= len(p.main):
            i = int(u) - 1
            if i in indices:
                self.sel = i
                self.jouer(p.main[i])
            else:
                self.envoyer("COUP %d" % p.main[i])   # le serveur explique le refus

    def touche_reglages(self, t: str) -> None:
        r = self.regl
        if t in ("ESC", "F1"):
            self.regl = None
        elif t in ("UP", "DOWN", "TAB"):
            r[0] = 1 - r[0]
        elif t in ("LEFT", "RIGHT", "+", "-"):
            plus = t in ("RIGHT", "+")
            if r[0] == 0:
                r[1] = min(5000, r[1] + 100) if plus else max(500, r[1] - 100)
            else:
                r[2] = min(10, r[2] + 1) if plus else max(1, r[2] - 1)
        elif t == "ENTER":
            p = self.partie
            if r[1] != p.cible:
                self.envoyer("PARAM CIBLE %d" % r[1])
            if r[2] != p.inactif:
                self.envoyer("PARAM INACTIF %d" % r[2])
            self.regl = None

    # -- dessin
    def dessiner(self, force: bool = False) -> None:
        taille = shutil.get_terminal_size((LARGEUR, HAUTEUR))
        if taille != self.taille:
            self.taille = taille
            sys.stdout.write("\x1b[0m\x1b[2J")
            force = True
        if self.partie.cloche:          # arrivée ou départ d'un humain (SPEC 6.4)
            self.partie.cloche = False
            sys.stdout.write("\a")
            sys.stdout.flush()
        if not (self.sale or force):
            return
        self.sale = False
        if taille.columns < LARGEUR or taille.lines < HAUTEUR:
            sys.stdout.write("\x1b[0m\x1b[2J\x1b[H" + self.tr("m_petit") +
                             " (%d x %d)" % (taille.columns, taille.lines))
            sys.stdout.flush()
            return
        e = self.ecran
        if self.en_jeu:
            self.dessiner_jeu()
        else:
            self.dessiner_connexion()
        dx = (taille.columns - LARGEUR) // 2
        dy = (taille.lines - HAUTEUR) // 2
        sys.stdout.write(e.rendu(dx, dy))
        sys.stdout.flush()

    def bandeau_haut(self, titre: str) -> None:
        e = self.ecran
        e.ecrire(0, 0, " " * LARGEUR, S_BANDEAU)
        e.ecrire(1, 0, "BELOTE LAN", S_TOUCHE)
        e.ecrire(12, 0, titre, S_BANDEAU)

    def barre(self, elements) -> None:
        """Ligne 23 : touches en jaune, libellés en blanc, sur noir."""
        e = self.ecran
        e.ecrire(0, HAUTEUR - 1, " " * LARGEUR, S_BANDEAU)
        x = 1
        for touche, libelle in elements:
            if x + len(touche) + len(libelle) + 1 >= LARGEUR:
                break
            e.ecrire(x, HAUTEUR - 1, touche, S_TOUCHE)
            x += len(touche) + 1
            e.ecrire(x, HAUTEUR - 1, libelle, S_BANDEAU)
            x += len(libelle) + 3

    def dessiner_salons(self) -> None:
        e, tr = self.ecran, self.tr
        e.vider(S_TAPIS)
        self.bandeau_haut("·  " + tr("s_titre"))
        e.ecrire(LARGEUR - len("v" + VERSION) - 1, 0, "v" + VERSION, S_BANDEAU)
        e.remplir(20, 2, 40, 3, S_BANDEAU)
        e.centre(20, 40, 3, tr("s_titre").upper(), S_TOUCHE)
        for i, (h, jeu) in enumerate(self.salons):
            texte = " %s %d    %d/4 %s    %s " % (tr("s_salon"), i + 1, h, tr("s_joueurs"),
                                                 tr("s_jeu" if jeu else "s_attente"))
            e.ecrire(22, 7 + i, texte.ljust(36), S_CHOIX_SEL if i == self.sal_sel else S_CHOIX)
        if self.message:
            e.centre(0, LARGEUR, 20, " " + self.message + " ", self.message_style)
        e.ecrire(0, HAUTEUR - 1, " " * LARGEUR, S_BANDEAU)
        e.centre(0, LARGEUR, HAUTEUR - 1, tr("s_aide"), S_TOUCHE)

    def dessiner_connexion(self) -> None:
        e, tr = self.ecran, self.tr
        if self.salons is not None:
            self.dessiner_salons()
            return
        e.vider(S_TAPIS)
        self.bandeau_haut("·  " + tr("connexion"))
        e.ecrire(LARGEUR - len("v" + VERSION) - 1, 0, "v" + VERSION, S_BANDEAU)
        # le titre, sur une carte blanche
        e.remplir(20, 2, 40, 3, S_BANDEAU)
        e.centre(20, 40, 3, "B E L O T E   L A N", S_TOUCHE)
        for i in range(4):                        # les quatre valets, atouts maîtres
            self.carte(26 + i * 8, 6, i * 8 + 4)
        libelles = [tr("c_serveur"), tr("c_nom"), tr("c_langue")]
        valeurs = [self.champs[0], self.champs[1], tr("langue")]
        for i in range(3):
            y = 11 + i * 2
            e.ecrire(16, y, libelles[i], S_TAPIS_TEXTE)
            e.ecrire(28, y, ":", S_TAPIS_TEXTE)
            style = S_CHOIX_SEL if i == self.champ else S_CHOIX
            texte = valeurs[i]
            if i == 2:
                texte = "← " + texte + " →" if i == self.champ else "  " + texte + "  "
            elif i == self.champ:
                texte += "_"
            e.ecrire(30, y, " " + texte.ljust(20 if i else 34) + " ", style)
        e.centre(0, LARGEUR, 18, tr("c_info"), S_TAPIS_TEXTE)
        if self.message:
            e.centre(0, LARGEUR, 20, " " + self.message + " ", self.message_style)
        if self.perdue:
            e.centre(0, LARGEUR, 21, tr("m_reprendre"), S_MSG_INFO)
        e.ecrire(0, HAUTEUR - 1, " " * LARGEUR, S_BANDEAU)
        e.centre(0, LARGEUR, HAUTEUR - 1, tr("c_aide"), S_TOUCHE)

    def nom_carte(self, c: int) -> str:
        r = c % 8
        if r < 4:
            rang = ("7", "8", "9", "10")[r]
        elif r == 7:
            rang = "A"
        else:
            rang = self.tr("figures")[r - 4]
        return rang + self.symboles[c // 8]

    def carte(self, x: int, y: int, c: int, grise: bool = False) -> None:
        """Carte 5 x 3 : rang en haut à gauche, symbole au milieu, rang en bas à droite."""
        rouge = (c // 8) % 2 == 1
        style = (S_GRISE_R if rouge else S_GRISE_N) if grise else (S_CARTE_R if rouge else S_CARTE_N)
        rang = self.nom_carte(c)[:-1]
        e = self.ecran
        e.ecrire(x, y, rang.ljust(5), style)
        e.ecrire(x, y + 1, "  " + self.symboles[c // 8] + "  ", style)
        e.ecrire(x, y + 2, rang.rjust(5), style)

    def rel(self, p: int) -> int:
        return (p - self.partie.moi) % 4

    def etiquette(self, p: int) -> None:
        """Nom d'une place, aux couleurs de son équipe (jaune quand c'est son tour)."""
        pa, e = self.partie, self.ecran
        r = self.rel(p)
        texte = " " + pa.nom(p) + (" (" + self.tr("chef") + ")" if p == pa.chef else "") + " "
        style = S_TOUR if p == pa.tour else S_EQUIPE[p % 2]
        bulle = self.texte_annonce(pa.annonces[p])
        if r == 0:
            x, y = CENTRE - len(texte) // 2, 12
        elif r == 2:
            x, y = CENTRE - len(texte) // 2, 2
        elif r == 3:
            x, y = 1, 7
        else:
            x, y = TABLE_L - 1 - len(texte), 7
        e.ecrire(x, y, texte, style)
        if bulle:
            if r in (0, 2):
                e.ecrire(x + len(texte) + 1, y, bulle, S_BULLE)
            elif r == 3:
                e.ecrire(1, y + 1, bulle, S_BULLE)
            else:
                e.ecrire(TABLE_L - 1 - len(bulle), y + 1, bulle, S_BULLE)

    def texte_annonce(self, a) -> str:
        if not a:
            return ""
        if a[0] == "prend":
            return self.tr("prend") + " " + self.symboles[a[1]]
        return self.tr(a[0])

    def dessiner_jeu(self) -> None:
        e, tr, p = self.ecran, self.tr, self.partie
        e.vider(S_TAPIS)
        nous = p.nous()
        # bandeau : scores
        self.bandeau_haut("")
        x = 15
        for eq, cle in ((nous, "nous"), (1 - nous, "eux")):
            e.ecrire(x, 0, tr(cle), S_EQUIPE_TXT[eq].replace("107", "40"))
            x += len(tr(cle)) + 1
            e.ecrire(x, 0, "%04d" % p.scores[eq], S_BANDEAU)
            x += 7
        if p.en_reserve:
            e.ecrire(x, 0, tr("en_reserve", p.en_reserve), S_TOUCHE)
        droite = "%s %d   v%s" % (tr("cible"), p.cible, VERSION)
        e.ecrire(LARGEUR - len(droite) - 1, 0, droite, S_BANDEAU)
        # ligne 1 : donneur, atout
        if p.etat in (EN_COURS, FIN_MANCHE) and p.donneur >= 0:
            e.ecrire(1, 1, tr("donneur", p.nom(p.donneur)), S_TAPIS_TEXTE)
        if p.atout is not None and p.preneur is not None:
            t = "%s %s  %s %s" % (tr("atout"), self.symboles[p.atout], tr("pris_par"), p.nom(p.preneur))
            e.ecrire(TABLE_L - 1 - len(t), 1, t, S_TAPIS_TEXTE)
        for place in range(4):
            self.etiquette(place)
        self.dessiner_centre()
        self.dessiner_main()
        self.dessiner_journal()
        self.dessiner_barre()

    def dessiner_centre(self) -> None:
        e, tr, p = self.ecran, self.tr, self.partie
        if self.aide:
            e.remplir(2, 2, TABLE_L - 4, 19, S_PANNEAU)
            for i, l in enumerate(REGLES[tr.code]):
                e.ecrire(4, 3 + i, l, S_PANNEAU)
            return
        if self.regl is not None:
            r = self.regl
            e.remplir(6, 4, 43, 9, S_PANNEAU)
            e.centre(6, 43, 5, tr("reglages"), S_PANNEAU_TITRE)
            for i, (cle, val) in enumerate((("r_cible", r[1]), ("r_inactif", r[2]))):
                style = S_CHOIX_SEL.replace("107", "47") if r[0] == i else S_PANNEAU
                e.ecrire(9, 7 + i * 2, " %-20s ◄ %4d ► " % (tr(cle), val), style)
            e.centre(6, 43, 11, tr("r_aide")[:41], S_PANNEAU)
            return
        maintenant = time.monotonic()
        ramasse = p.ramasse if p.ramasse and maintenant - p.ramasse[2] < DUREE_PLI else None
        if p.etat == FIN_PARTIE:
            self.panneau_partie()
            return
        if p.etat == FIN_MANCHE and not ramasse:
            self.panneau_manche()
            return
        if self.voir_dernier and p.dernier:
            pli, gagnant = p.dernier
            e.centre(0, TABLE_L, 13, tr("dernier_pli"), S_BULLE)
        elif ramasse:
            pli, gagnant = ramasse[0], ramasse[1]
        else:
            pli, gagnant = p.pli, None
        for place, c in pli:
            x, y = CARTE_XY[self.rel(place)]
            self.carte(x, y, c)
            if place == gagnant:
                e.ecrire(x - 1, y + 1, "►", S_BULLE)
        if p.etat == EN_COURS and p.atout is None and p.retournee is not None:
            self.carte(25, 6, p.retournee)
            e.centre(0, TABLE_L, 9, tr("retournee"), S_TAPIS_TEXTE)
            e.centre(0, TABLE_L, 10, tr("tour1") if p.ench_tour == 1 else tr("tour2"), S_TAPIS)
        # ligne 14 : invite
        invite = ""
        if p.etat == ATTENTE:
            if p.suis_chef():
                invite = tr("attente_chef")
            else:
                invite = tr("attente", p.nom(p.chef) if p.chef >= 0 else "?")
            e.centre(0, TABLE_L, 9, tr("attente_regl", p.cible, p.inactif), S_TAPIS_TEXTE)
        elif p.etat == EN_COURS:
            choix = p.choix_encheres()
            if choix:
                invite = tr("a_vous_ench", len(choix))
                self.dessiner_encheres(choix)
            elif p.a_moi():
                invite = tr("a_vous_carte")
            elif 0 <= p.tour <= 3:
                invite = tr("au_tour", p.nom(p.tour))
        if invite:
            e.centre(0, TABLE_L, 14, invite, S_TAPIS_TEXTE)
        # ligne 20 : plis et points de la manche
        if p.etat == EN_COURS and p.atout is not None and p.points is not None:
            nous = p.nous()
            t = "%s  %s %d - %s %d      %s  %s %d - %s %d" % (
                tr("plis"), tr("nous"), p.plis[nous], tr("eux"), p.plis[1 - nous],
                tr("points"), tr("nous"), p.points[nous], tr("eux"), p.points[1 - nous])
            e.centre(0, TABLE_L, 21, t, S_TAPIS_DOUX)

    def dessiner_encheres(self, choix) -> None:
        e, tr = self.ecran, self.tr
        textes = []
        for i, c in enumerate(choix):
            t = tr("passer") if c[0] == "PASSE" else tr("prendre") + " " + self.symboles[c[1]]
            textes.append(" %d %s " % (i + 1, t))
        largeur = sum(len(t) for t in textes) + 2 * (len(textes) - 1)
        x = CENTRE - largeur // 2
        for i, t in enumerate(textes):
            sel = i == self.ench_sel % len(choix)
            e.ecrire(x, 13, t, S_CHOIX_SEL if sel else S_CHOIX)
            if not sel and choix[i][0] == "ENCH" and choix[i][1] % 2:
                e.ecrire(x + len(t) - 2, 13, self.symboles[choix[i][1]], "0;1;91;40")
            elif sel and choix[i][0] == "ENCH" and choix[i][1] % 2:
                e.ecrire(x + len(t) - 2, 13, self.symboles[choix[i][1]], "0;1;31;107")
            x += len(t) + 2

    def dessiner_main(self) -> None:
        e, p = self.ecran, self.partie
        if not p.main:
            return
        jouables = p.jouables()
        x0 = CENTRE - (len(p.main) * 6 - 1) // 2
        for i, c in enumerate(p.main):
            x = x0 + i * 6
            if jouables:
                ok = c in jouables
                self.carte(x, 16 if ok else 17, c, grise=not ok)
                if ok:
                    sel = i == self.sel
                    e.ecrire(x + 1, 20, " %d " % (i + 1), S_NUM_SEL if sel else S_NUM)
            else:
                self.carte(x, 17, c)
                e.ecrire(x + 2, 20, str(i + 1), S_TAPIS_DOUX)

    def panneau_manche(self) -> None:
        e, tr, p = self.ecran, self.tr, self.partie
        x, l = 6, 43
        e.remplir(x, 3, l, 12, S_PANNEAU)
        e.centre(x, l, 4, tr("p_manche"), S_PANNEAU_TITRE)
        nous = p.nous()
        m = p.manche or [0, 0]
        e.ecrire(x + 6, 6, tr("nous"), S_EQUIPE_TXT[nous])
        e.ecrire(x + 22, 6, "%4d" % m[nous], S_PANNEAU_TITRE)
        e.ecrire(x + 6, 7, tr("eux"), S_EQUIPE_TXT[1 - nous])
        e.ecrire(x + 22, 7, "%4d" % m[1 - nous], S_PANNEAU_TITRE)
        if p.capot is not None:
            resultat = tr("p_capot")
        elif p.litige:
            resultat = tr("p_litige", p.en_reserve)
        elif p.reserve:
            resultat = tr("p_reserve", p.reserve[1])
        elif p.preneur is not None and p.manche:
            t = p.preneur % 2
            resultat = tr("p_rempli") if p.manche[t] > p.manche[1 - t] else tr("p_dedans")
        else:
            resultat = ""
        if resultat:
            e.centre(x, l, 9, resultat, S_PANNEAU_TITRE)
        e.ecrire(x + 6, 11, tr("p_total"), S_PANNEAU)
        e.ecrire(x + 15, 11, "%s %d - %s %d" % (tr("nous"), p.scores[nous], tr("eux"),
                                                 p.scores[1 - nous]), S_PANNEAU)
        if p.suite_fin is not None:
            reste = max(0, int(p.suite_fin - time.monotonic() + 0.99))
            e.centre(x, l, 13, tr("p_suite", reste), S_PANNEAU)

    def panneau_partie(self) -> None:
        e, tr, p = self.ecran, self.tr, self.partie
        x, l = 6, 43
        e.remplir(x, 4, l, 10, S_PANNEAU)
        nous = p.nous()
        if p.gagnant is not None:
            e.centre(x, l, 6, tr("p_victoire_nous" if p.gagnant == nous else "p_victoire_eux"),
                     S_EQUIPE_TXT[p.gagnant])
        e.centre(x, l, 8, "%s %d - %s %d" % (tr("nous"), p.scores[nous], tr("eux"),
                                             p.scores[1 - nous]), S_PANNEAU_TITRE)
        e.centre(x, l, 11, tr("p_nouvelle") if p.suis_chef() else tr("p_attend_chef"), S_PANNEAU)

    def dessiner_journal(self) -> None:
        e, tr, p = self.ecran, self.tr, self.partie
        x, l = JOURNAL_X, JOURNAL_L
        e.remplir(x - 1, 1, l + 1, HAUTEUR - 2, S_JOURNAL)
        e.ecrire(x, 1, tr("journal"), S_JOURNAL_TITRE)
        lignes = []
        for entree in p.journal[-40:]:
            lignes += self.lignes_journal(entree, l - 1)
        bas = HAUTEUR - 3 if self.tchat is None else HAUTEUR - 5
        visibles = lignes[-(bas - 2):]
        for i, (texte, style) in enumerate(visibles):
            e.ecrire(x, 3 + i, texte, style)
        if self.tchat is not None:
            e.ecrire(x, HAUTEUR - 4, "─" * (l - 1), S_JOURNAL)
            saisie = (tr("vous") + " : " + self.tchat + "_")[-(l - 1):]
            e.ecrire(x, HAUTEUR - 3, saisie, S_CHOIX_SEL)

    def lignes_journal(self, entree, l: int) -> list:
        tr = self.tr
        cle, args = entree[0], entree[1:]
        if cle == "tchat":
            nom, texte, place = args
            style = S_TCHAT
            texte = nom + " : " + texte
        elif cle == "brut":
            texte, style = args[0], S_INFO
        else:
            vals = []
            for a in args:
                if isinstance(a, tuple) and a[0] == "couleur":
                    vals.append(self.symboles[a[1]])
                elif isinstance(a, tuple) and a[0] == "err":
                    vals.append(tr(a[1]) if a[1] in TEXTES else a[1].lower())
                else:
                    vals.append(a)
            texte = tr(cle, *vals)
            style = S_REFUS if cle == "j_refus" else S_INFO if cle.startswith("i_") else S_JOURNAL
            if cle in ("j_manche", "j_capot_nous", "j_capot_eux", "j_commence", "j_bienvenue"):
                style = S_JOURNAL_TITRE
        lignes, ligne = [], ""
        for mot in texte.split(" "):
            if ligne and len(ligne) + 1 + len(mot) > l:
                lignes.append(ligne)
                ligne = "  " + mot
            else:
                ligne = (ligne + " " + mot) if ligne else mot
            while len(ligne) > l:
                lignes.append(ligne[:l])
                ligne = "  " + ligne[l:]
        lignes.append(ligne)
        return [(x, style) for x in lignes]

    def dessiner_barre(self) -> None:
        tr, p = self.tr, self.partie
        oui = tr("oui")
        if self.question:
            cle = "q_quitter" if self.question == "quitter" else "q_effacer"
            self.ecran.ecrire(0, HAUTEUR - 1, " " * LARGEUR, S_BANDEAU)
            self.ecran.centre(0, LARGEUR, HAUTEUR - 1, tr(cle, oui), S_TOUCHE)
            return
        if self.tchat is not None:
            self.barre([(tr("entree"), tr("k_envoyer")), (tr("echap"), tr("k_annuler"))])
            return
        if self.aide or self.voir_dernier:
            self.barre([(tr("entree"), tr("k_retour"))])
            return
        if self.regl is not None:
            self.barre([(tr("entree"), "OK"), (tr("echap"), tr("k_annuler"))])
            return
        el = []
        if p.etat == ATTENTE and p.suis_chef():
            el += [("L", tr("k_lancer")), ("R", tr("k_reglages"))]
        if p.etat == FIN_MANCHE:
            el.append((tr("entree"), tr("k_suite")))
        if p.etat == FIN_PARTIE and p.suis_chef():
            el.append((tr("entree"), tr("k_nouvelle")))
        if p.a_moi():
            el.append(("←→ " + tr("entree"), tr("k_choisir" if p.choix_encheres() else "k_jouer")))
        el.append(("T", tr("k_tchat")))
        if p.etat == EN_COURS and p.dernier:
            el.append(("D", tr("k_dernier")))
        el.append(("A", tr("k_aide")))
        if p.etat != ATTENTE and p.suis_chef():
            el.append(("E", tr("k_effacer")))
        el.append(("Q", tr("k_quitter")))
        self.barre(el)


def activer_ansi_windows() -> None:
    """Console Windows : séquences ANSI (VT), sortie UTF-8, sans Édition rapide.

    Édition rapide : un clic dans la fenêtre commence une sélection, et Windows
    bloque alors tout affichage du programme, qui paraît figé (le jeu s'arrête
    pendant son tour). On la coupe pour cette fenêtre seulement.
    """
    if os.name != "nt":
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            k.SetConsoleMode(h, mode.value | 0x0004)   # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        k.SetConsoleOutputCP(65001)
        h = k.GetStdHandle(-10)
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            # sans ENABLE_QUICK_EDIT_MODE (0x40), avec ENABLE_EXTENDED_FLAGS (0x80)
            k.SetConsoleMode(h, (mode.value & ~0x0040) | 0x0080)
    except Exception:
        pass


def main() -> None:
    # Avant tout affichage (l'aide de --help contient ♠) : sous Windows, une sortie redirigée
    # serait sinon en cp1252.
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="BELOTE LAN : client pour PC (terminal)")
    parser.add_argument("--serveur", help="adresse du serveur, éventuellement avec :port "
                        "(par défaut %s:%d)" % (SERVEUR_DEFAUT, PORT_DEFAUT))
    parser.add_argument("--nom", help="nom du joueur (6 lettres ou chiffres)")
    parser.add_argument("--langue", choices=["fr", "en", "de", "es", "FR", "EN", "DE", "ES"])
    parser.add_argument("--ascii", action="store_true", help="symboles S H C D au lieu de ♠ ♥ ♣ ♦")
    parser.add_argument("--auto", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    activer_ansi_windows()
    app = App(args)
    clavier = Clavier(app.file)
    sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b]0;BELOTE LAN\x07")
    try:
        app.executer()
    except KeyboardInterrupt:
        app.quitter()
    finally:
        clavier.restaurer()
        sys.stdout.write("\x1b[0m\x1b[2J\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
