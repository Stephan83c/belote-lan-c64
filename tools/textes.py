"""Génère les textes du client C64 en quatre langues : c64/textes.h et c64/textes.c.

Lancer :  python3 tools/textes.py   (bibliothèque standard seulement)

Chaque texte a un identifiant, une largeur maximale à l'écran et une traduction
par langue. Le script refuse un texte trop large ou un caractère que l'écran ne
sait pas afficher : en mode couleur étendue, il n'existe que les 64 premiers
caractères (espace, chiffres, ponctuation, A-Z, [ et ]), sans # ni @ (devenus le
tapis et les symboles des cartes). Tout est donc en majuscules, sans accents :
UE pour Ü, N pour Ñ, comme le français s'écrit déjà sans accents.

Dans un format (sprintf), la largeur compte %s pour 6 caractères (un nom), %u et
%d pour 4, %c pour 1.

Les mots-clés du protocole ne se traduisent pas : ils restent en français sur le
réseau (débogable avec nc) et le client les traduit à l'affichage.
"""
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
LANGUES = ["FR", "EN", "DE", "ES"]

# (identifiant, largeur maximale, français, anglais, allemand, espagnol)
TEXTES = [
    # Nom de la langue, sur l'écran de connexion (F1)
    ("LANGUE", 8, "FRANCAIS", "ENGLISH", "DEUTSCH", "ESPANOL"),
    # Touche qui confirme l'effacement de la partie (F4)
    ("TOUCHE_OUI", 1, "O", "Y", "J", "S"),
    # Figures : valet, dame, roi (les autres rangs sont des chiffres et A)
    ("FIGURES", 3, "VDR", "JQK", "BDK", "JQK"),

    # ---- Écran de connexion (libellés suivis de « : » en colonne 8) ----
    ("C_SERVEUR", 8, "SERVEUR", "SERVER", "SERVER", "SERVIDOR"),
    ("C_NOM", 8, "NOM", "NAME", "NAME", "NOMBRE"),
    ("C_INFO", 40, "4 PLACES : LES BOTS COMPLETENT LA TABLE", "4 SEATS: BOTS FILL THE EMPTY ONES",
     "4 PLAETZE: BOTS FUELLEN FREIE PLAETZE", "4 PLAZAS: LOS BOTS COMPLETAN LA MESA"),
    # Barre de touches de l'écran de connexion (ligne 24, comme en jeu)
    ("B_CONNEXION", 39, "RETURN VALIDER  CRSR CHAMP  F1 LANGUE",
     "RETURN CONFIRM  CRSR FIELD  F1 LANGUAGE", "RETURN OK  CRSR FELD  F1 SPRACHE",
     "RETURN ACEPTAR  CRSR CAMPO  F1 IDIOMA"),
    ("M_PERDUE", 40, "CONNEXION PERDUE", "CONNECTION LOST", "VERBINDUNG VERLOREN",
     "CONEXION PERDIDA"),
    ("M_ENTREZ_NOM", 40, "ENTREZ UN NOM (6 LETTRES OU CHIFFRES)",
     "ENTER A NAME (6 LETTERS OR DIGITS)", "NAME EINGEBEN (6 BUCHSTABEN/ZIFFERN)",
     "ESCRIBA UN NOMBRE (6 LETRAS O CIFRAS)"),
    ("M_NOM_BOT", 40, "NOM RESERVE AUX BOTS : CHOISIR UN AUTRE",
     "NAME RESERVED FOR BOTS: CHOOSE ANOTHER", "NAME FUER BOTS RESERVIERT: BITTE AENDERN",
     "NOMBRE RESERVADO A LOS BOTS: ELIJA OTRO"),
    ("M_UCI", 40, "COMMAND INTERFACE ABSENTE OU INACTIVE",
     "COMMAND INTERFACE MISSING OR DISABLED", "COMMAND INTERFACE FEHLT ODER IST AUS",
     "COMMAND INTERFACE AUSENTE O INACTIVA"),
    ("M_CONNEXION", 40, "CONNEXION...", "CONNECTING...", "VERBINDE...", "CONECTANDO..."),
    ("M_BLOQUE", 40, "ULTIMATE BLOQUE : ETEINDRE ET RALLUMER",
     "ULTIMATE STUCK: POWER IT OFF AND ON", "ULTIMATE BLOCKIERT: AUS- UND EINSCHALTEN",
     "ULTIMATE BLOQUEADO: APAGAR Y ENCENDER"),
    ("M_IMPOSSIBLE", 40, "CONNEXION IMPOSSIBLE", "CANNOT CONNECT",
     "VERBINDUNG FEHLGESCHLAGEN", "CONEXION IMPOSIBLE"),
    ("M_FERMEE", 40, "CONNEXION FERMEE PAR LE SERVEUR", "CONNECTION CLOSED BY THE SERVER",
     "VERBINDUNG VOM SERVER GETRENNT", "CONEXION CERRADA POR EL SERVIDOR"),
    ("M_MUET", 40, "LE SERVEUR NE REPOND PAS", "THE SERVER IS NOT RESPONDING",
     "DER SERVER ANTWORTET NICHT", "EL SERVIDOR NO RESPONDE"),
    ("M_PLEINE", 40, "TABLE PLEINE (4 JOUEURS) : PLUS TARD",
     "TABLE FULL (4 PLAYERS): TRY LATER", "TISCH VOLL (4 SPIELER): SPAETER",
     "MESA LLENA (4 JUGADORES): MAS TARDE"),
    ("M_NOM_REFUSE", 40, "NOM REFUSE : EN CHOISIR UN AUTRE", "NAME REFUSED: CHOOSE ANOTHER ONE",
     "NAME ABGELEHNT: BITTE EINEN ANDEREN", "NOMBRE RECHAZADO: ELIJA OTRO"),
    # Préfixe d'un refus du serveur (ERR), suivi du motif
    ("REFUS", 11, "REFUS : ", "REFUSED: ", "ABGELEHNT: ", "RECHAZADO: "),

    # ---- Motifs des refus du serveur (ERR), après REFUS dans le journal ----
    ("E_TROP_LONG", 28, "LIGNE TROP LONGUE", "LINE TOO LONG", "ZEILE ZU LANG",
     "LINEA DEMASIADO LARGA"),
    ("E_NOM", 28, "NOM INVALIDE", "INVALID NAME", "UNGUELTIGER NAME", "NOMBRE NO VALIDO"),
    ("E_CHEF_SEUL", 28, "LE CHEF SEULEMENT", "HOST ONLY", "NUR DER CHEF", "SOLO EL JEFE"),
    ("E_PAS_LANCEE", 28, "PARTIE PAS LANCEE", "GAME NOT STARTED", "SPIEL NICHT GESTARTET",
     "PARTIDA NO INICIADA"),
    ("E_INCONNU", 28, "COMMANDE INCONNUE", "UNKNOWN COMMAND", "UNBEKANNTER BEFEHL",
     "ORDEN DESCONOCIDA"),
    ("E_PAS_TON_TOUR", 28, "PAS TON TOUR", "NOT YOUR TURN", "NICHT DEIN ZUG", "NO ES TU TURNO"),
    ("E_COUP_REFUSE", 28, "CARTE INTERDITE", "CARD NOT ALLOWED", "KARTE NICHT ERLAUBT",
     "CARTA NO PERMITIDA"),
    ("E_NOM_RESERVE", 28, "NOM RESERVE AUX BOTS", "NAME RESERVED FOR BOTS",
     "NAME FUER BOTS RESERVIERT", "NOMBRE RESERVADO A BOTS"),
    ("E_TABLE_PLEINE", 28, "TABLE PLEINE", "TABLE FULL", "TISCH VOLL", "MESA LLENA"),
    ("E_DEJA_LANCEE", 28, "PARTIE DEJA LANCEE", "GAME ALREADY STARTED", "SPIEL LAEUFT SCHON",
     "PARTIDA YA INICIADA"),
    ("E_PARAM", 28, "REGLAGE REFUSE", "INVALID SETTING", "UNGUELTIGE EINSTELLUNG",
     "AJUSTE NO VALIDO"),

    # ---- Informations du serveur (INFO), reconnues par le client ----
    ("I_EFFACEE", 39, "PARTIE EFFACEE", "GAME WIPED", "SPIEL GELOESCHT", "PARTIDA BORRADA"),
    ("I_INACTIF", 39, "INACTIF : PLACE RENDUE AU BOT", "IDLE: YOUR SEAT GOES TO A BOT",
     "INAKTIV: DEIN PLATZ GEHT AN EINEN BOT", "INACTIVO: TU PUESTO PASA A UN BOT"),
    ("I_NOM_CHANGE", 39, "NOM CHANGE EN %s", "NAME CHANGED TO %s", "NAME GEAENDERT IN %s",
     "NOMBRE CAMBIADO A %s"),
    ("I_RECONNECTE", 39, "%s RECONNECTE", "%s RECONNECTED", "%s WIEDER VERBUNDEN",
     "%s RECONECTADO"),
    ("I_INACTIF_BOT", 39, "%s INACTIF REMPLACE PAR UN BOT", "%s IDLE, REPLACED BY A BOT",
     "%s INAKTIV, DURCH BOT ERSETZT", "%s INACTIVO, CAMBIADO POR UN BOT"),
    ("I_BOT", 39, "%s REMPLACE PAR UN BOT", "%s REPLACED BY A BOT", "%s DURCH BOT ERSETZT",
     "%s CAMBIADO POR UN BOT"),
    ("I_RESERVE_NOUS", 39, "RESERVE DE %u POINTS POUR NOUS", "RESERVE OF %u POINTS FOR US",
     "RESERVE VON %u PUNKTEN FUER UNS", "RESERVA DE %u PUNTOS PARA NOSOTROS"),
    ("I_RESERVE_EUX", 39, "RESERVE DE %u POINTS POUR EUX", "RESERVE OF %u POINTS FOR THEM",
     "RESERVE VON %u PUNKTEN FUER EUCH", "RESERVA DE %u PUNTOS PARA ELLOS"),

    # ---- Journal (après « NOM  : », 33 caractères) ----
    ("J_PLI", 33, "REMPORTE LE PLI", "WINS THE TRICK", "MACHT DEN STICH", "GANA LA BAZA"),
    ("J_PASSE", 33, "PASSE", "PASSES", "PASST", "PASA"),
    # « PREND A V♠ », « PREND A V♠ ATOUT ♥ »
    ("J_PREND", 12, "PREND A ", "TAKES ", "NIMMT ", "TOMA "),
    ("J_ATOUT", 10, " ATOUT ", " TRUMP ", " TRUMPF ", " TRIUNFO "),
    ("J_SECOND", 39, "SECOND TOUR D'ENCHERES", "SECOND ROUND OF BIDDING", "ZWEITE BIETRUNDE",
     "SEGUNDA RONDA DE SUBASTA"),
    ("J_COMMENCE", 39, "LA PARTIE COMMENCE", "THE GAME BEGINS", "DAS SPIEL BEGINNT",
     "EMPIEZA LA PARTIDA"),
    ("J_MANCHE", 39, "MANCHE : NOUS %d  EUX %d", "ROUND: US %d  THEM %d",
     "RUNDE: WIR %d  IHR %d", "MANO: NOSOTROS %d  ELLOS %d"),
    ("J_CAPOT_NOUS", 39, "CAPOT POUR NOUS", "CAPOT FOR US", "CAPOT FUER UNS",
     "CAPOT PARA NOSOTROS"),
    ("J_CAPOT_EUX", 39, "CAPOT POUR EUX", "CAPOT FOR THEM", "CAPOT FUER EUCH",
     "CAPOT PARA ELLOS"),
    ("J_LITIGE", 39, "LITIGE : %d POINTS EN RESERVE", "TIE: %d POINTS HELD IN RESERVE",
     "PATT: %d PUNKTE IN RESERVE", "EMPATE: %d PUNTOS EN RESERVA"),
    ("J_REDONNE", 39, "TOUT LE MONDE PASSE : ON REDONNE", "EVERYONE PASSED: REDEAL",
     "ALLE PASSEN: NEU GEBEN", "TODOS PASAN: SE REPARTE"),

    # ---- Table ----
    ("NOUS", 5, "NOUS", "US", "WIR", "NOS"),
    ("EUX", 5, "EUX", "THEM", "IHR", "ELLOS"),
    ("V_ATOUT", 15, "BELOTE   ATOUT:", "BELOTE   TRUMP:", "BELOTE  TRUMPF:", "BELOTE TRIUNFO:"),
    ("V_SCORES", 20, "NOUS:%04u   EUX:%04u", "US:%04u    THEM:%04u", "WIR:%04u    IHR:%04u",
     "NOS:%04u  ELLOS:%04u"),
    # Après le nom du chef sur la table d'attente : « MARC (CHEF) »
    ("V_CHEF", 4, "CHEF", "HOST", "CHEF", "JEFE"),
    ("V_RETOURNEE", 11, "RETOURNEE", "TURNED UP", "AUFGEDECKT", "VOLTEADA"),
    ("V_PRISE", 11, "PRISE", "TAKEN", "GENOMMEN", "TOMADA"),
    # Saisie du tchat : « VOUS : texte »
    ("V_VOUS", 4, "VOUS", "YOU", "DU", "TU"),
    ("V_ATTENTE", 40, "CHEF : %s   CIBLE : %u POINTS", "HOST: %s   TARGET: %u POINTS",
     "CHEF: %s   ZIEL: %u PUNKTE", "JEFE: %s   META: %u PUNTOS"),
    # Ligne des enchères : le tour (1ER TOUR) occupe la fin de la ligne
    ("V_AU_TOUR", 31, "ENCHERES : AU TOUR DE %s...", "BIDDING: %s TO PLAY...",
     "BIETEN: %s IST DRAN...", "SUBASTA: TURNO DE %s..."),
    ("V_PRENDRE", 12, "PRENDRE", "TAKE", "NEHMEN", "TOMAR"),
    ("V_PASSER", 10, "PASSE", "PASS", "PASSEN", "PASAR"),
    ("V_TOUR1", 8, "1ER TOUR", "ROUND 1", "RUNDE 1", "RONDA 1"),
    ("V_TOUR2", 8, "2E TOUR", "ROUND 2", "RUNDE 2", "RONDA 2"),
    ("V_A_VOUS", 40, "A VOUS DE JOUER : 1-8", "YOUR TURN: 1-8", "DU BIST DRAN: 1-8",
     "TE TOCA: 1-8"),
    ("V_FIN_CHEF", 40, "MANCHE TERMINEE : F5 POUR LA SUIVANTE", "ROUND OVER: F5 FOR THE NEXT ONE",
     "RUNDE VORBEI: F5 FUER DIE NAECHSTE", "MANO TERMINADA: F5 PARA LA SIGUIENTE"),
    # %s : NOUS ou EUX, l'équipe qui a marqué le plus de points dans la manche
    ("V_SUITE", 40, "MANCHE POUR %s - SUITE DANS %u S", "ROUND TO %s - NEXT ONE IN %u S",
     "RUNDE FUER %s - WEITER IN %u S", "MANO PARA %s - SIGUE EN %u S"),
    ("V_FIN_AUTRE", 40, "MANCHE TERMINEE : ON ATTEND LE CHEF", "ROUND OVER: WAITING FOR THE HOST",
     "RUNDE VORBEI: WARTEN AUF DEN CHEF", "MANO TERMINADA: ESPERANDO AL JEFE"),

    # ---- Barre de touches (ligne 24, 39 caractères : jamais la dernière case) ----
    ("B_BASE", 39, "F3 TCHAT F7 QUIT F8 AIDE", "F3 CHAT F7 QUIT F8 HELP",
     "F3 CHAT F7 ENDE F8 HILFE", "F3 CHAT F7 FIN F8 AYUDA"),
    ("B_RAZ", 39, "EFFACER LA PARTIE ? O OUI, AUTRE NON", "WIPE THE GAME? Y YES, OTHER KEY NO",
     "SPIEL LOESCHEN? J JA, ANDERE TASTE NEIN", "BORRAR LA PARTIDA? S SI, OTRA TECLA NO"),
    ("B_TCHAT", 39, "RETURN ENVOYER  DEL EFFACER  F3 ANNULER", "RETURN SEND  DEL DELETE  F3 CANCEL",
     "RETURN SENDEN  DEL LOESCHEN  F3 ABBRUCH", "RETURN ENVIAR  DEL BORRAR  F3 CANCELAR"),
    ("B_CHEF_ATTENTE", 39, "F1 PARAM F2 GO F3 TCHAT F7 QUIT F8 AIDE",
     "F1 SETUP F2 GO F3 CHAT F7 QUIT F8 HELP", "F1 OPT F2 GO F3 CHAT F7 ENDE F8 HILFE",
     "F1 OPC F2 GO F3 CHAT F7 FIN F8 AYUDA"),
    # Partie lancée, le chef a F4 : TCHAT devient MSG faute de place
    ("B_CHEF_ENCH", 39, "1-4 CHOIX F3 MSG F4 RAZ F7 QUIT F8 AIDE",
     "1-4 BID F3 MSG F4 WIPE F7 QUIT F8 HELP", "1-4 WAHL F3 MSG F4 NEU F7 ENDE F8 HILFE",
     "1-4 PUJA F3 MSG F4 CERO F7 FIN F8 AYUDA"),
    ("B_CHEF_CARTE", 39, "1-8 CARTE F3 MSG F4 RAZ F7 QUIT F8 AIDE",
     "1-8 CARD F3 MSG F4 WIPE F7 QUIT F8 HELP", "1-8 WAHL F3 MSG F4 NEU F7 ENDE F8 HILFE",
     "1-8 TIRA F3 MSG F4 CERO F7 FIN F8 AYUDA"),
    ("B_CHEF_MANCHE", 39, "F3 MSG F4 RAZ F5 SUITE F7 QUIT F8 AIDE",
     "F3 MSG F4 WIPE F5 NEXT F7 QUIT F8 HELP", "F3 MSG F4 NEU F5 LOS F7 ENDE F8 HILFE",
     "F3 MSG F4 CERO F5 SIGUE F7 FIN F8 AYUDA"),
    ("B_MANCHE", 39, "F3 TCHAT F5 SUITE F7 QUIT F8 AIDE", "F3 CHAT F5 NEXT F7 QUIT F8 HELP",
     "F3 CHAT F5 LOS F7 ENDE F8 HILFE", "F3 CHAT F5 SIGUE F7 FIN F8 AYUDA"),
    ("B_CHEF", 39, "F3 TCHAT F4 RAZ F7 QUIT F8 AIDE", "F3 CHAT F4 WIPE F7 QUIT F8 HELP",
     "F3 CHAT F4 NEU F7 ENDE F8 HILFE", "F3 CHAT F4 CERO F7 FIN F8 AYUDA"),
    ("B_ENCH", 39, "1-4 CHOIX F3 TCHAT F7 QUIT F8 AIDE", "1-4 BID F3 CHAT F7 QUIT F8 HELP",
     "1-4 WAHL F3 CHAT F7 ENDE F8 HILFE", "1-4 PUJA F3 CHAT F7 FIN F8 AYUDA"),
    ("B_CARTE", 39, "1-8 CARTE F3 TCHAT F7 QUIT F8 AIDE", "1-8 CARD F3 CHAT F7 QUIT F8 HELP",
     "1-8 WAHL F3 CHAT F7 ENDE F8 HILFE", "1-8 TIRA F3 CHAT F7 FIN F8 AYUDA"),
    ("B_RETOUR", 39, "F8 RETOUR AU JEU", "F8 BACK TO THE GAME", "F8 ZURUECK ZUM SPIEL",
     "F8 VOLVER AL JUEGO"),
    ("B_PARAM", 39, "RETURN VALIDER  F1 ANNULER", "RETURN CONFIRM  F1 CANCEL",
     "RETURN OK  F1 ABBRUCH", "RETURN ACEPTAR  F1 CANCELAR"),
    ("B_FIN_CHEF", 39, "F5 NOUVELLE PARTIE F7 QUIT", "F5 NEW GAME F7 QUIT",
     "F5 NEUES SPIEL F7 ENDE", "F5 NUEVA PARTIDA F7 FIN"),
    ("B_FIN", 39, "F7 QUIT", "F7 QUIT", "F7 ENDE", "F7 FIN"),

    # ---- Titres, à droite de « BELOTE LAN C64 » ----
    ("T_REGLES", 22, "REGLES DU JEU", "GAME RULES", "SPIELREGELN", "REGLAS DEL JUEGO"),
    ("T_PARAM", 22, "PARAMETRES", "SETTINGS", "EINSTELLUNGEN", "AJUSTES"),
    ("T_FIN", 22, "PARTIE TERMINEE", "GAME OVER", "SPIEL BEENDET", "PARTIDA TERMINADA"),

    # ---- Réglages (F1) ----
    ("P_CIBLE", 40, "%c SCORE CIBLE : %u", "%c TARGET SCORE: %u", "%c ZIELPUNKTE  : %u",
     "%c PUNTOS META : %u"),
    ("P_INACTIF", 40, "%c INACTIVITE  : %u MIN", "%c IDLE TIMEOUT: %u MIN",
     "%c INAKTIVITAET: %u MIN", "%c INACTIVIDAD : %u MIN"),
    ("P_CHOISIR", 40, "CRSR HAUT/BAS : CHOISIR", "CRSR UP/DOWN  : SELECT",
     "CRSR HOCH/RUNTER : WAEHLEN", "CRSR ARRIBA/ABAJO : ELEGIR"),
    ("P_MODIFIER", 40, "+ / -         : MODIFIER", "+ / -         : CHANGE",
     "+ / -            : AENDERN", "+ / -             : CAMBIAR"),

    # ---- Fin de partie ----
    ("F_VICT_NOUS", 40, "VICTOIRE DE NOUS !", "WE WIN!", "WIR GEWINNEN!", "GANAMOS NOSOTROS!"),
    ("F_VICT_EUX", 40, "VICTOIRE DE EUX !", "THEY WIN!", "IHR GEWINNT!", "GANAN ELLOS!"),
    ("F_NOUVELLE", 40, "F5 = NOUVELLE PARTIE   (CHEF SEULEMENT)", "F5 = NEW GAME   (HOST ONLY)",
     "F5 = NEUES SPIEL   (NUR DER CHEF)", "F5 = NUEVA PARTIDA   (SOLO EL JEFE)"),
    ("F_QUITTER", 40, "F7 = QUITTER", "F7 = QUIT", "F7 = BEENDEN", "F7 = SALIR"),
]

# Règles du jeu (F8) : 21 lignes de 39 caractères au plus, figures de FIGURES.
REGLES = {
    "FR": [
        "32 CARTES. VOUS ET NORD CONTRE EST ET",
        "OUEST. ON JOUE VERS LA DROITE.",
        "ENCHERES, TOUR 1 : PRENDRE A LA COULEUR",
        "RETOURNEE (1) OU PASSER (2). TOUR 2 :",
        "UNE AUTRE COULEUR (1-3) OU PASSER (4).",
        "",
        "FOURNIR LA COULEUR DEMANDEE. A L'ATOUT,",
        "MONTER SI POSSIBLE. SANS LA COULEUR :",
        "COUPER SI L'ADVERSAIRE EST MAITRE, ET",
        "SURCOUPER SI POSSIBLE. PARTENAIRE",
        "MAITRE : JEU LIBRE.",
        "",
        "ATOUT : V 20, 9 14, A 11, 10 10, R 4,",
        "D 3. HORS ATOUT : A 11, 10 10, R 4,",
        "D 3, V 2. DIX DE DER 10, BELOTE 20.",
        "",
        "LE PRENEUR DOIT FAIRE PLUS QUE LA",
        "DEFENSE, SINON IL EST DEDANS : 162 A",
        "LA DEFENSE. CAPOT : 252.",
        "",
        "CHEF : F4 EFFACE LA PARTIE EN COURS.",
    ],
    "EN": [
        "32 CARDS. YOU AND NORTH AGAINST EAST",
        "AND WEST. PLAY PASSES TO THE RIGHT.",
        "BIDDING, ROUND 1: TAKE THE TURNED-UP",
        "SUIT (1) OR PASS (2). ROUND 2:",
        "ANOTHER SUIT (1-3) OR PASS (4).",
        "",
        "FOLLOW SUIT. IN TRUMPS, PLAY HIGHER",
        "IF YOU CAN. UNABLE TO FOLLOW: TRUMP",
        "IF THE OPPONENTS ARE WINNING, AND",
        "OVERTRUMP IF YOU CAN. PARTNER",
        "WINNING: PLAY ANY CARD.",
        "",
        "TRUMPS: J 20, 9 14, A 11, 10 10, K 4,",
        "Q 3. OTHER SUITS: A 11, 10 10, K 4,",
        "Q 3, J 2. LAST TRICK 10, BELOTE 20.",
        "",
        "THE TAKER MUST SCORE MORE THAN THE",
        "DEFENCE, OR ELSE GOES SET: 162 TO THE",
        "DEFENCE. CAPOT: 252.",
        "",
        "HOST: F4 WIPES THE GAME IN PROGRESS.",
    ],
    "DE": [
        "32 KARTEN. DU UND NORD GEGEN OST UND",
        "WEST. GESPIELT WIRD NACH RECHTS.",
        "BIETEN, RUNDE 1: AUFGEDECKTE FARBE",
        "NEHMEN (1) ODER PASSEN (2). RUNDE 2:",
        "ANDERE FARBE (1-3) ODER PASSEN (4).",
        "",
        "FARBE BEDIENEN. BEI TRUMPF HOEHER",
        "SPIELEN, WENN MOEGLICH. FARBE FEHLT:",
        "STECHEN, WENN DER GEGNER VORN LIEGT,",
        "UND UEBERSTECHEN, WENN MOEGLICH.",
        "PARTNER VORN: FREIE WAHL.",
        "",
        "TRUMPF: B 20, 9 14, A 11, 10 10, K 4,",
        "D 3. SONST: A 11, 10 10, K 4, D 3,",
        "B 2. LETZTER STICH 10, BELOTE 20.",
        "",
        "WER NIMMT, BRAUCHT MEHR PUNKTE ALS DIE",
        "GEGNER, SONST GEHEN 162 AN DIE",
        "GEGNER. CAPOT: 252.",
        "",
        "CHEF: F4 LOESCHT DAS LAUFENDE SPIEL.",
    ],
    "ES": [
        "32 CARTAS. TU Y NORTE CONTRA ESTE Y",
        "OESTE. SE JUEGA HACIA LA DERECHA.",
        "SUBASTA, RONDA 1: TOMAR EL PALO",
        "VOLTEADO (1) O PASAR (2). RONDA 2:",
        "OTRO PALO (1-3) O PASAR (4).",
        "",
        "SEGUIR EL PALO. EN TRIUNFO, SUBIR SI",
        "SE PUEDE. SIN EL PALO: FALLAR SI EL",
        "RIVAL VA GANANDO, Y SOBREFALLAR SI",
        "SE PUEDE. SI GANA EL COMPANERO:",
        "JUEGO LIBRE.",
        "",
        "TRIUNFO: J 20, 9 14, A 11, 10 10, K 4,",
        "Q 3. RESTO: A 11, 10 10, K 4, Q 3,",
        "J 2. ULTIMA BAZA 10, BELOTE 20.",
        "",
        "QUIEN TOMA DEBE HACER MAS PUNTOS QUE",
        "LA DEFENSA; SI NO, LOS 162 VAN A LA",
        "DEFENSA. CAPOT: 252.",
        "",
        "JEFE: F4 BORRA LA PARTIDA EN CURSO.",
    ],
}
NB_REGLES = 21
LARGEUR_REGLES = 39

# Espace, chiffres, ponctuation (sauf # " $ % &, devenus le tapis et les coins des
# cartes), A-Z, [ et ] : voir car() dans c64/ecran.c.
PERMIS = set(chr(c) for c in range(32, 64) if chr(c) not in "#\"$%&") | set("ABCDEFGHIJKLMNOPQRSTUVWXYZ[]")
FORMAT = re.compile(r"%(-?\d*)([sudc])")
LARGEUR_FORMAT = {"s": 6, "u": 4, "d": 4, "c": 1}


def largeur(s: str) -> int:
    return len(FORMAT.sub(lambda m: "x" * max(LARGEUR_FORMAT[m.group(2)],
                                              int(m.group(1) or 0)), s))


def formats(s: str) -> list[str]:
    return [m.group(2) for m in FORMAT.finditer(s)]


def verifier() -> list[str]:
    fautes = []
    vus = set()
    for ident, maxi, *trad in TEXTES:
        if ident in vus:
            fautes.append(f"{ident} : identifiant en double")
        vus.add(ident)
        if len(trad) != len(LANGUES):
            fautes.append(f"{ident} : {len(trad)} traductions au lieu de {len(LANGUES)}")
            continue
        for langue, s in zip(LANGUES, trad):
            if largeur(s) > maxi:
                fautes.append(f"{ident} {langue} : {largeur(s)} > {maxi} : {s!r}")
            interdits = set(FORMAT.sub("", s)) - PERMIS
            if interdits:
                fautes.append(f"{ident} {langue} : caractères {''.join(sorted(interdits))!r}")
            if formats(s) != formats(trad[0]):
                fautes.append(f"{ident} {langue} : formats {formats(s)} au lieu de {formats(trad[0])}")
    for langue in LANGUES:
        lignes = REGLES[langue]
        if len(lignes) != NB_REGLES:
            fautes.append(f"REGLES {langue} : {len(lignes)} lignes au lieu de {NB_REGLES}")
        for s in lignes:
            if len(s) > LARGEUR_REGLES:
                fautes.append(f"REGLES {langue} : {len(s)} > {LARGEUR_REGLES} : {s!r}")
            if set(s) - PERMIS:
                fautes.append(f"REGLES {langue} : caractères interdits dans {s!r}")
    return fautes


def c_chaine(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def generer() -> None:
    entete = [
        "/* Généré par tools/textes.py : ne pas modifier à la main. */",
        "#ifndef TEXTES_H",
        "#define TEXTES_H",
        "",
        f"#define NB_LANGUES {len(LANGUES)}",
        f"#define NB_REGLES {NB_REGLES}",
        "",
        "enum {",
    ]
    entete += [f"    T_{ident}," for ident, *_ in TEXTES]
    entete += [
        f"    T_REGLES,                       /* {NB_REGLES} lignes */",
        f"    NB_TEXTES = T_REGLES + {NB_REGLES}",
        "};",
        "",
        "extern unsigned char langue;",
        "extern const char *const *txt;           /* textes de la langue choisie */",
        "extern const char *const *const textes[NB_LANGUES];",
        "void langue_choisir(unsigned char n);",
        "#define T(i) (txt[i])",
        "",
        "#endif",
        "",
    ]
    corps = [
        "/* Généré par tools/textes.py : ne pas modifier à la main. */",
        '#include "ascii.h"',
        '#include "textes.h"',
        "",
    ]
    for i, langue in enumerate(LANGUES):
        corps.append(f"static const char *const textes_{langue.lower()}[NB_TEXTES] = {{")
        for ident, _, *trad in TEXTES:
            corps.append(f"    {c_chaine(trad[i])},")
        for s in REGLES[langue]:
            corps.append(f"    {c_chaine(s)},")
        corps.append("};")
        corps.append("")
    noms = ", ".join(f"textes_{l.lower()}" for l in LANGUES)
    corps += [
        f"const char *const *const textes[NB_LANGUES] = {{ {noms} }};",
        "",
        "#ifndef LANGUE_DEFAUT",
        "#define LANGUE_DEFAUT 0",
        "#endif",
        "unsigned char langue = LANGUE_DEFAUT;",
        "const char *const *txt;                 /* langue_choisir() au démarrage */",
        "",
        "void langue_choisir(unsigned char n)",
        "{",
        "    langue = n < NB_LANGUES ? n : 0;",
        "    txt = textes[langue];",
        "}",
        "",
    ]
    (RACINE / "c64" / "textes.h").write_text("\n".join(entete))
    (RACINE / "c64" / "textes.c").write_text("\n".join(corps))


def main() -> int:
    fautes = verifier()
    for f in fautes:
        print(f, file=sys.stderr)
    if fautes:
        return 1
    generer()
    print(f"c64/textes.c : {len(TEXTES) + NB_REGLES} textes x {len(LANGUES)} langues")
    return 0


if __name__ == "__main__":
    sys.exit(main())
