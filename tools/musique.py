"""Génère la musique et les bruitages du client C64 : c64/son_donnees.s.

Lancer :  python3 tools/musique.py   (bibliothèque standard seulement)

Le lecteur (c64/son.s) tourne dans l'interruption du KERNAL, 60 fois par seconde :
toutes les durées sont en 1/60 s. Compositions originales.

Format d'un air : 1 octet (1 = en boucle), puis pour chaque voix 1-3 :
adresse du flux (0 = voix muette), forme d'onde, AD, SR, largeur d'impulsion (octet haut).
Flux d'une voix : note durée (note 0 = silence), $FD a b = arpège de la note
avec +a et +b demi-tons (0 0 : sans arpège), $FF = fin.

Bruitage (voix 3) : AD SR, puis une image par 1/60 s : forme d'onde (bit 0 = gate),
fréquence (octet bas, octet haut) ; $FF = fin.
"""
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
HORLOGE_PAL = 985248

TRI, DENT, CARRE, BRUIT = 0x10, 0x20, 0x40, 0x80
GATE = 0x01

NOMS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note(nom: str) -> int:
    """'C#5' -> indice de note (1 = C0) ; 'R' -> 0 (silence)."""
    if nom == "R":
        return 0
    demi = NOMS[nom[0]]
    reste = nom[1:]
    if reste.startswith("#"):
        demi += 1
        reste = reste[1:]
    return int(reste) * 12 + demi + 1


def frequence(n: int) -> int:
    """Registre de fréquence SID (PAL) de l'indice de note n."""
    midi = n - 1 + 12
    f = 440 * 2 ** ((midi - 69) / 12)
    return min(0xFFFF, round(f * 16777216 / HORLOGE_PAL))


def flux(evenements) -> list[int]:
    """[('E5', 20), ('ARP', 4, 7), ...] -> octets ; vérifie la durée totale."""
    octets = []
    for e in evenements:
        if e[0] == "ARP":
            octets += [0xFD, e[1], e[2]]
        else:
            n, d = note(e[0]), e[1]
            assert 1 <= d <= 255 and n < 90, e
            octets += [n, d]
    return octets + [0xFF]


def duree(evenements) -> int:
    return sum(e[1] for e in evenements if e[0] != "ARP")


# ---- Écran titre : valse musette (3/4, une noire = 20/60 s) --------------

N, C = 20, 10   # noire, croche
MELODIE = [
    ("C",  [("E5", N), ("D5", C), ("E5", C), ("G5", N)]),
    ("C",  [("C6", 2 * N), ("G5", N)]),
    ("G7", [("F5", N), ("E5", C), ("F5", C), ("A5", N)]),
    ("G7", [("G5", 3 * N)]),
    ("G7", [("D5", N), ("C#5", C), ("D5", C), ("F5", N)]),
    ("G7", [("G5", N), ("F5", N), ("D5", N)]),
    ("C",  [("E5", N), ("G5", C), ("E5", C), ("C5", N)]),
    ("C",  [("C5", 2 * N), ("R", N)]),
    ("F",  [("A5", N), ("G5", C), ("A5", C), ("C6", N)]),
    ("F",  [("F5", 2 * N), ("A5", N)]),
    ("C",  [("G5", N), ("F5", C), ("G5", C), ("E5", N)]),
    ("A7", [("A5", 2 * N), ("G5", N)]),
    ("Dm", [("F5", N), ("E5", C), ("F5", C), ("A5", N)]),
    ("G7", [("G5", N), ("F5", N), ("B4", N)]),
    ("C",  [("C5", N), ("E5", N), ("G5", N)]),
    ("C",  [("C6", 2 * N), ("R", N)]),
]
# accord : (basse fondamentale, basse alternée, note de l'accord, arpège)
ACCORDS = {
    "C":  ("C3", "G2", "C4", (4, 7)),
    "G7": ("G2", "D3", "G3", (4, 10)),
    "F":  ("F2", "C3", "F3", (4, 7)),
    "A7": ("A2", "E3", "A3", (4, 10)),
    "Dm": ("D3", "A2", "D4", (3, 7)),
}


def valse():
    v1, v2, v3 = [], [], []
    precedent = None
    for accord, mesure in MELODIE:
        assert duree(mesure) == 3 * N, (accord, mesure)
        v1 += mesure
        fond, alt, base, arp = ACCORDS[accord]
        # oum : la basse au premier temps, alternée si l'accord se répète
        v2 += [(alt if accord == precedent else fond, N), ("R", 2 * N)]
        # pa-pa : l'accord arpégé aux deuxième et troisième temps
        v3 += [("R", N), ("ARP", *arp), (base, N), (base, N), ("ARP", 0, 0)]
        precedent = None if accord == precedent else accord
    return v1, v2, v3


# ---- Fin de partie ---------------------------------------------------------

VICTOIRE = (
    [("C5", 8), ("E5", 8), ("G5", 8), ("C6", 20), ("G5", 8), ("C6", 48)],
    [("C3", 24), ("G3", 28), ("ARP", 4, 7), ("C4", 48), ("ARP", 0, 0)],
)
DEFAITE = (
    [("E5", 15), ("D#5", 15), ("D5", 15), ("C5", 54)],
    [("A3", 15), ("G#3", 15), ("G3", 15), ("ARP", 3, 7), ("A2", 54), ("ARP", 0, 0)],
)

# Airs : nom, boucle, voix (événements, onde, AD, SR, impulsion haute) ou None
AIRS = [
    ("TITRE", 1, [
        (valse()[0], CARRE, 0x26, 0xA4, 0x04),   # mélodie, carré étroit (accordéon)
        (valse()[1], TRI, 0x09, 0x00, 0x08),     # basse pincée
        (valse()[2], CARRE, 0x04, 0x00, 0x02),   # accords secs
    ]),
    ("VICTOIRE", 0, [
        (VICTOIRE[0], CARRE, 0x08, 0xC6, 0x06),
        (VICTOIRE[1], TRI, 0x0A, 0xA6, 0x08),
        None,
    ]),
    ("DEFAITE", 0, [
        (DEFAITE[0], CARRE, 0x2A, 0x96, 0x03),
        (DEFAITE[1], TRI, 0x0A, 0x96, 0x08),
        None,
    ]),
]

# ---- Bruitages (voix 3) ----------------------------------------------------


def images(onde, freqs, gate_images):
    """Une image par fréquence ; gate levé pendant les gate_images premières."""
    return [(onde | (GATE if i < gate_images else 0), f) for i, f in enumerate(freqs)]


EFFETS = [
    # carte posée : claquement de bruit qui descend
    ("CARTE", 0x00, 0xA0, images(BRUIT, [0x5000, 0x3800, 0x2400, 0x1800, 0x1000], 3)),
    # pli ramassé : glissement de bruit, attaque douce et longue retombée
    ("PLI", 0x60, 0xF8,
     images(BRUIT, [0x0600 + 0x0180 * i for i in range(8)]
            + [0x1200 - 0x0100 * i for i in range(14)], 8)),
    # tchat : deux notes claires (triangle)
    ("TCHAT", 0x09, 0x00,
     images(TRI, [frequence(note("E6"))] * 5 + [frequence(note("B6"))] * 12, 16)),
]


# ---- Sortie ----------------------------------------------------------------


def octets_asm(octets, largeur=16):
    for i in range(0, len(octets), largeur):
        yield "        .byte " + ",".join(f"${o:02X}" for o in octets[i:i + largeur])


def main() -> None:
    lignes = [
        "; Musique et bruitages, générés par tools/musique.py : ne pas éditer.",
        "",
        "        .export son_freq_lo, son_freq_hi, son_airs, son_effets",
        '        .segment "RODATA"',
        "",
        "son_freq_lo:",
    ]
    freqs = [0] + [frequence(n) for n in range(1, 96)]
    lignes += octets_asm([f & 0xFF for f in freqs])
    lignes.append("son_freq_hi:")
    lignes += octets_asm([f >> 8 for f in freqs])

    lignes += ["", "son_airs:"] + [f"        .word air_{nom}" for nom, _, _ in AIRS]
    for nom, boucle, voix in AIRS:
        if boucle:
            longueurs = {duree(v[0]) for v in voix if v}
            assert len(longueurs) == 1, (nom, longueurs)
        lignes += ["", f"air_{nom}:", f"        .byte {boucle}"]
        for i, v in enumerate(voix):
            if v is None:
                lignes.append("        .word 0\n        .byte 0,0,0,0")
            else:
                _, onde, ad, sr, pw = v
                lignes.append(f"        .word flux_{nom}_{i}")
                lignes.append(f"        .byte ${onde:02X},${ad:02X},${sr:02X},${pw:02X}")
        for i, v in enumerate(voix):
            if v is not None:
                lignes.append(f"flux_{nom}_{i}:")
                lignes += octets_asm(flux(v[0]))

    lignes += ["", "son_effets:"] + [f"        .word effet_{nom}" for nom, *_ in EFFETS]
    for nom, ad, sr, imgs in EFFETS:
        octets = [ad, sr]
        for onde, f in imgs:
            octets += [onde, f & 0xFF, f >> 8]
        lignes.append(f"effet_{nom}:")
        lignes += octets_asm(octets + [0xFF], 15)

    sortie = RACINE / "c64/son_donnees.s"
    sortie.write_text("\n".join(lignes) + "\n")
    print(f"{sortie} écrit")


if __name__ == "__main__":
    main()
