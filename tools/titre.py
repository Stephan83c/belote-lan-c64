"""Génère l'écran titre du client C64 : bitmap multicolore 160x200.

Sortie : c64/titre_img.c (bitmap $E000, matrice écran, RAM couleur) et, en option,
un aperçu PNG :  python3 tools/titre.py [apercu.png]

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
    for i, c in enumerate(s):
        g = glyphe(c)
        for gy in range(8):
            for gx in range(8):
                if g[gy] & (0x80 >> gx):
                    px, py = x + (i * 8 + gx) * sx, y + gy * sy
                    if ombre is not None:
                        rect(img, px + 1, py + 1, sx, sy, ombre)
        for gy in range(8):
            for gx in range(8):
                if g[gy] & (0x80 >> gx):
                    rect(img, x + (i * 8 + gx) * sx, y + gy * sy, sx, sy, coul)


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
    rect(img, x, y, w, h, NOIR)
    rect(img, x + 1, y + 1, w - 2, h - 2, BLANC)
    # coins arrondis
    for cx, cy in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        img[cy][cx] = FOND
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
    texte(img, (W - 6 * 16) // 2, 10, "BELOTE", JAUNE, sx=2, sy=3, ombre=NOIR)
    texte(img, (W - 7 * 8) // 2, 40, "LAN C64", BLANC, sx=1, sy=2, ombre=NOIR)

    # éventail : valet de trèfle, as de pique, puis la belote (dame et roi de coeur)
    main = [("V", "trefle"), ("A", "pique"), ("D", "coeur"), ("R", "coeur")]
    pas, cw, ch = 20, 28, 72
    x0 = (W - (cw + pas * (len(main) - 1))) // 2
    for i, (r, c) in enumerate(main):
        dy = abs(i * 2 - 3) * 3      # éventail : les cartes du bord plus bas
        carte(img, x0 + i * pas, 76 + dy, r, c, w=cw, h=ch)

    texte(img, (W - 17 * 8) // 2, 176, "ESPACE POUR JOUER", GRIS_CLAIR, sx=1, sy=2)
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


def main():
    img = image()
    bitmap, ecran, couleur = convertir(img)
    src = "\n\n".join([
        "/* Écran titre (bitmap multicolore), généré par tools/titre.py : ne pas éditer. */",
        tableau("titre_bitmap", bitmap),
        tableau("titre_ecran", ecran),
        tableau("titre_couleur", couleur),
    ]) + "\n"
    (RACINE / "c64/titre_img.c").write_text(src)
    if len(sys.argv) > 1:
        apercu(img, bitmap, ecran, couleur, sys.argv[1])


if __name__ == "__main__":
    main()
