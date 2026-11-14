"""Génère l'écran titre du client C64 : bitmap multicolore 160x200.

Sortie : c64/titre_img.c (bitmap $E000, matrice écran, RAM couleur) et, en option,
un aperçu PNG :  python3 tools/titre.py [apercu.png]

Compression : plus de la moitié des 1000 cases (8x8 pixels) sont du feutre pur,
toutes identiques (mêmes octets, mêmes couleurs). titre_cases a un bit par case
(1 = feutre) ; les autres cases suivent dans titre_autres, 10 octets chacune :
8 octets de bitmap, l'octet de la matrice écran, celui de la RAM couleur.

En multicolore, chaque bloc de 4x8 pixels (larges) a le fond commun ($D021, vert)
et trois couleurs à lui : le dessin les respecte presque partout, la conversion
remplace l'éventuelle quatrième par la plus proche.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

RACINE = Path(__file__).resolve().parent.parent
W, H = 160, 200

# Palette C64 (Pepto)
PAL = [
    (0, 0, 0), (255, 255, 255), (104, 55, 43), (112, 164, 178),
    (111, 61, 134), (88, 141, 67), (53, 40, 121), (184, 199, 111),
    (111, 79, 37), (67, 57, 0), (154, 103, 89), (68, 68, 68),
    (108, 108, 108), (154, 210, 132), (108, 94, 181), (149, 149, 149),
]
NOIR, BLANC, ROUGE, VERT, JAUNE, GRIS_CLAIR, VERT_CLAIR = 0, 1, 2, 5, 7, 15, 13
FOND = VERT

CHARGEN = Path.home() / ".local/share/vice/C64/chargen-901225-01.bin"


def glyphe(c):
    """Lignes 8x8 du caractère ASCII c dans la ROM majuscules/graphiques."""
    rom = CHARGEN.read_bytes()
    o = ord(c)
    code = o - 64 if 65 <= o <= 90 else o
    return rom[code * 8:code * 8 + 8]


def texte(img, x, y, s, coul, sx=1, sy=2, ombre=None):
    """sy peut être fractionnaire (1.5 : lignes du caractère hautes de 2, 1, 2, 1...)."""
    def ligne(gy):
        y0 = y + int(gy * sy)
        return y0, y + int((gy + 1) * sy) - y0

    for i, c in enumerate(s):
        g = glyphe(c)
        for gy in range(8):
            for gx in range(8):
                if g[gy] & (0x80 >> gx):
                    (py, h), px = ligne(gy), x + (i * 8 + gx) * sx
                    if ombre is not None:
                        rect(img, px + 1, py + 1, sx, h, ombre)
        for gy in range(8):
            for gx in range(8):
                if g[gy] & (0x80 >> gx):
                    py, h = ligne(gy)
                    rect(img, x + (i * 8 + gx) * sx, py, sx, h, coul)


# Mini-police 3x5 pour la ligne d'auteur (la ROM ne fait que du 8x8).
MINI = {
    "A": ["010", "101", "111", "101", "101"], "C": ["011", "100", "100", "100", "011"],
    "E": ["111", "100", "110", "100", "111"], "G": ["011", "100", "101", "101", "011"],
    "H": ["101", "101", "111", "101", "101"], "I": ["111", "010", "010", "010", "111"],
    "L": ["100", "100", "100", "100", "111"], "N": ["110", "101", "101", "101", "101"],
    "P": ["110", "101", "110", "100", "100"], "S": ["011", "100", "010", "001", "110"],
    "T": ["111", "010", "010", "010", "010"], "V": ["101", "101", "101", "101", "010"],
    "0": ["010", "101", "101", "101", "010"], "2": ["110", "001", "010", "100", "111"],
    "3": ["110", "001", "010", "001", "110"], "6": ["011", "100", "110", "101", "010"],
    "(": ["001", "010", "010", "010", "001"], ")": ["100", "010", "010", "010", "100"],
    "-": ["000", "000", "111", "000", "000"], " ": ["000"] * 5,
}


def mini(img, y, s, coul, sy=2):
    """Ligne centrée en mini-police : 4 pixels larges par caractère."""
    x0 = (W - len(s) * 4 + 1) // 2
    for i, c in enumerate(s):
        for gy, ligne in enumerate(MINI[c]):
            for gx, b in enumerate(ligne):
                if b == "1":
                    rect(img, x0 + i * 4 + gx, y + gy * sy, 1, sy, coul)


def rect(img, x, y, w, h, c):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if 0 <= xx < W and 0 <= yy < H:
                img[yy][xx] = c


def masque_couleur(couleur, w, h):
    """Masque w x h (pixels larges, 2:1) d'un symbole ♠ ♥ ♣ ♦ dessiné en vrai."""
    k = 16
    big = Image.new("L", (2 * w * k, h * k), 0)
    d = ImageDraw.Draw(big)
    bw, bh = big.size

    def P(x, y):
        return (x * bw, y * bh)

    def cercle(cx, cy, r):
        rr = r * bw
        x, y = P(cx, cy)
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=255)

    if couleur == "coeur":
        cercle(0.28, 0.30, 0.25)
        cercle(0.72, 0.30, 0.25)
        d.polygon([P(0.05, 0.40), P(0.95, 0.40), P(0.5, 0.98)], fill=255)
    elif couleur == "carreau":
        d.polygon([P(0.5, 0.0), P(0.92, 0.5), P(0.5, 1.0), P(0.08, 0.5)], fill=255)
    elif couleur == "pique":
        cercle(0.28, 0.58, 0.23)
        cercle(0.72, 0.58, 0.23)
        d.polygon([P(0.06, 0.52), P(0.94, 0.52), P(0.5, 0.0)], fill=255)
        d.polygon([P(0.5, 0.6), P(0.72, 1.0), P(0.28, 1.0)], fill=255)
    elif couleur == "trefle":
        cercle(0.5, 0.26, 0.21)
        cercle(0.26, 0.58, 0.21)
        cercle(0.74, 0.58, 0.21)
        d.polygon([P(0.5, 0.45), P(0.72, 1.0), P(0.28, 1.0)], fill=255)
    small = big.resize((w, h), Image.BOX)
    return [[small.getpixel((x, y)) >= 128 for x in range(w)] for y in range(h)]


def symbole(img, x, y, couleur, w, h):
    m = masque_couleur(couleur, w, h)
    coul = ROUGE if couleur in ("coeur", "carreau") else NOIR
    for yy in range(h):
        for xx in range(w):
            if m[yy][xx]:
                img[y + yy][x + xx] = coul


def carte(img, x, y, rang, couleur, w=24, h=64, visible=None):
    """Carte blanche bordée de noir ; rang et petit symbole en haut à gauche,
    grand symbole au centre."""
    # Coins arrondis : 3 pixels de chaque coin laissent voir ce qu'il y a derrière
    # (tapis ou carte précédente de l'éventail), et le bord noir suit la courbe.
    coins = []
    for sx, sy, cx, cy in ((1, 1, x, y), (-1, 1, x + w - 1, y),
                           (1, -1, x, y + h - 1), (-1, -1, x + w - 1, y + h - 1)):
        for dx, dy in ((0, 0), (1, 0), (0, 1)):
            px, py = cx + sx * dx, cy + sy * dy
            coins.append((px, py, img[py][px]))
    rect(img, x, y, w, h, NOIR)
    rect(img, x + 1, y + 1, w - 2, h - 2, BLANC)
    for px, py, c in coins:
        img[py][px] = c
    for sx, sy, cx, cy in ((1, 1, x, y), (-1, 1, x + w - 1, y),
                           (1, -1, x, y + h - 1), (-1, -1, x + w - 1, y + h - 1)):
        img[cy + sy][cx + sx] = NOIR
    coul = ROUGE if couleur in ("coeur", "carreau") else NOIR
    texte(img, x + 2, y + 3, rang, coul, sx=1, sy=2)
    symbole(img, x + 2, y + 21, couleur, 9, 16)
    symbole(img, x + w - 17, y + h - 34, couleur, 14, 26)


def image():
    img = [[FOND] * W for _ in range(H)]
    # feutre : points vert clair, comme le tapis de l'écran de jeu
    for y in range(0, H, 4):
        for x in range((y // 4) % 2 * 2, W, 4):
            img[y][x] = VERT_CLAIR

    # titre
    texte(img, (W - 6 * 16) // 2, 8, "BELOTE", JAUNE, sx=2, sy=3, ombre=NOIR)
    texte(img, (W - 7 * 8) // 2, 37, "LAN C64", BLANC, sx=1, sy=2, ombre=NOIR)

    # éventail : valet de trèfle, as de pique, puis la belote (dame et roi de coeur)
    main = [("V", "trefle"), ("A", "pique"), ("D", "coeur"), ("R", "coeur")]
    pas, cw, ch = 20, 28, 72
    x0 = (W - (cw + pas * (len(main) - 1))) // 2
    for i, (r, c) in enumerate(main):
        dy = abs(i * 2 - 3) * 3      # éventail : les cartes du bord plus bas
        carte(img, x0 + i * pas, 66 + dy, r, c, w=cw, h=ch)

    # Touche « SPACE » plutôt qu'une phrase : l'écran titre vaut pour toutes les
    # langues (la langue se choisit ensuite, par F1 sur l'écran de connexion).
    # Touche discrète, centrée entre l'éventail et la ligne d'auteur : un cadre
    # fin aux coins arrondis, juste autour du mot.
    # Lettres moins hautes (12 lignes au lieu de 16) pour une barre plus fine.
    kx, ky, kw, kh = (W - 48) // 2, 159, 48, 17
    rect(img, kx, ky, kw, kh, BLANC)
    rect(img, kx + 1, ky + 1, kw - 2, kh - 2, FOND)
    for cx, cy in ((kx, ky), (kx + kw - 1, ky), (kx, ky + kh - 1), (kx + kw - 1, ky + kh - 1)):
        rect(img, cx, cy, 1, 1, FOND)
    texte(img, (W - 5 * 8) // 2, ky + 3, "SPACE", JAUNE, sx=1, sy=1.5)
    mini(img, 187, "(C) 2026 STEPHAN - LICENCE GPL V3", BLANC)
    return img


def dist(a, b):
    return sum((p - q) ** 2 for p, q in zip(PAL[a], PAL[b]))


def convertir(img):
    bitmap, ecran, couleur = [], [], []
    for cy in range(25):
        for cx in range(40):
            bloc = [img[cy * 8 + y][cx * 4 + x] for y in range(8) for x in range(4)]
            compte = {}
            for c in bloc:
                if c != FOND:
                    compte[c] = compte.get(c, 0) + 1
            choix = sorted(compte, key=lambda c: -compte[c])[:3]
            while len(choix) < 3:
                choix.append(NOIR)
            # 01 = écran (poids fort), 10 = écran (poids faible), 11 = RAM couleur
            code = {FOND: 0, choix[0]: 1, choix[1]: 2, choix[2]: 3}
            ecran.append((choix[0] << 4) | choix[1])
            couleur.append(choix[2])
            for y in range(8):
                octet = 0
                for x in range(4):
                    c = bloc[y * 4 + x]
                    if c not in code:
                        c = min(code, key=lambda k: dist(k, c))
                    octet |= code[c] << (6 - 2 * x)
                bitmap.append(octet)
    return bitmap, ecran, couleur


def apercu(img, bitmap, ecran, couleur, chemin):
    """Relit les données converties, comme le VIC, en PNG 320x200."""
    out = Image.new("RGB", (320, 200))
    for cy in range(25):
        for cx in range(40):
            n = cy * 40 + cx
            cols = [FOND, ecran[n] >> 4, ecran[n] & 15, couleur[n]]
            for y in range(8):
                b = bitmap[n * 8 + y]
                for x in range(4):
                    c = PAL[cols[(b >> (6 - 2 * x)) & 3]]
                    out.putpixel((cx * 8 + x * 2, cy * 8 + y), c)
                    out.putpixel((cx * 8 + x * 2 + 1, cy * 8 + y), c)
    out.resize((640, 400), Image.NEAREST).save(chemin)


def tableau(nom, data):
    lignes = [f"const unsigned char {nom}[{len(data)}] = {{"]
    for i in range(0, len(data), 16):
        lignes.append("    " + ",".join(f"0x{b:02X}" for b in data[i:i + 16]) + ",")
    lignes.append("};")
    return "\n".join(lignes)


def compresser(bitmap, ecran, couleur):
    cases = [(tuple(bitmap[i * 8:i * 8 + 8]), ecran[i], couleur[i]) for i in range(1000)]
    feutre = max(set(cases), key=cases.count)
    drapeaux, autres = [0] * 125, []
    for i, c in enumerate(cases):
        if c == feutre:
            drapeaux[i >> 3] |= 0x80 >> (i & 7)
        else:
            autres += list(c[0]) + [c[1], c[2]]
    # relecture, comme le décodeur de c64/titre.c
    b, e, k, j = [], [], [], 0
    for i in range(1000):
        if drapeaux[i >> 3] & (0x80 >> (i & 7)):
            c = feutre
        else:
            c = (tuple(autres[j:j + 8]), autres[j + 8], autres[j + 9])
            j += 10
        b += c[0]
        e.append(c[1])
        k.append(c[2])
    assert (b, e, k) == (bitmap, ecran, couleur)
    return list(feutre[0]) + [feutre[1], feutre[2]], drapeaux, autres


def main():
    img = image()
    bitmap, ecran, couleur = convertir(img)
    feutre, drapeaux, autres = compresser(bitmap, ecran, couleur)
    src = "\n\n".join([
        "/* Écran titre (bitmap multicolore), généré par tools/titre.py : ne pas éditer. */",
        tableau("titre_feutre", feutre),
        tableau("titre_cases", drapeaux),
        tableau("titre_autres", autres),
    ]) + "\n"
    (RACINE / "c64/titre_img.c").write_text(src)
    if len(sys.argv) > 1:
        apercu(img, bitmap, ecran, couleur, sys.argv[1])


if __name__ == "__main__":
    main()
