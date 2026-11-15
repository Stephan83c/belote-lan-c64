#!/usr/bin/env python3
"""Capture du client PC : python3 tools/capture_pc.py LANGUE SORTIE.png (fr, en, de, es).

Le client (pc/belote_lan.py) joue une partie contre une table du serveur en mémoire,
avec les bots, jusqu'au milieu de la deuxième manche à son tour ; sa grille de
caractères et de styles est alors dessinée en PNG (cases de 11 x 22, DejaVu Sans
Mono), comme docs/pc.png et docs/pc-en.png. Demande Pillow.
"""
import asyncio, importlib.util, random, sys
from pathlib import Path
from types import SimpleNamespace
from PIL import Image, ImageDraw, ImageFont

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "server"))
from belote.table import Table
from belote.bots import choisir_carte, choisir_enchere

spec = importlib.util.spec_from_file_location("belote_lan", RACINE / "pc" / "belote_lan.py")
pc = importlib.util.module_from_spec(spec); spec.loader.exec_module(pc)

LANGUE, SORTIE = sys.argv[1], sys.argv[2]
FG = {30: (0, 0, 0), 31: (180, 30, 30), 37: (200, 200, 200), 90: (66, 66, 66), 91: (230, 70, 70),
      93: (255, 230, 80), 94: (40, 70, 190), 96: (90, 210, 230), 97: (255, 255, 255)}
BG = {40: (0, 0, 0), 41: (180, 30, 30), 42: (20, 110, 40), 44: (40, 70, 190), 47: (200, 200, 200),
      103: (255, 230, 80), 107: (255, 255, 255)}
CW, CH = 11, 22
POL = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 18)
POL_G = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 18)


def rendre(e):
    im = Image.new("RGB", (pc.LARGEUR * CW, pc.HAUTEUR * CH))
    d = ImageDraw.Draw(im)
    for y in range(pc.HAUTEUR):
        for x in range(pc.LARGEUR):
            codes = [int(c) for c in e.sty[y][x].split(";") if c]
            fg = next((FG[c] for c in codes if c in FG), (255, 255, 255))
            bg = next((BG[c] for c in codes if c in BG), (0, 0, 0))
            d.rectangle([x * CW, y * CH, x * CW + CW - 1, y * CH + CH - 1], fill=bg)
            ch = e.car[y][x]
            if ch != " ":
                d.text((x * CW, y * CH + 1), ch, font=POL_G if 1 in codes else POL, fill=fg)
    im.save(SORTIE)


async def principal():
    table = Table(rng=random.Random(11), delai_bot=0.0, delai_manche=0.0)
    app = pc.App(SimpleNamespace(ascii=False, langue=LANGUE, serveur="x", nom="JEAN", auto=False))
    app.partie = pc.Partie()

    class Pont:                     # le « réseau » : lignes du serveur vers l'App
        adresse = None
        def envoyer(self, l): app.ligne(l)
        def fermer(self): pass
    pont = Pont()

    class Reseau:                   # ce que l'App envoie va à la table
        def envoyer(self, l): table.recevoir(pont, l)
        def fermer(self): pass
    app.reseau = Reseau()
    app.reseau.envoyer("JOIN JEAN")
    app.reseau.envoyer("LANCER")
    p = app.partie
    while True:
        await asyncio.sleep(0)
        d = table.donne
        if table.etat == "EN COURS" and d.joueur == p.moi:
            if d.phase.name == "ENCHERES":
                c = choisir_enchere(d.mains[p.moi], d.tour_encheres, d.retournee)
                app.reseau.envoyer("PASSE" if c is None else f"ENCH {c}")
                continue
            # Capture : deuxième manche, plusieurs plis joués, deux cartes au pli.
            if sum(table.scores) > 0 and len(d.pli) == 2 and 2 <= d.nb_plis <= 4:
                break
            app.reseau.envoyer(f"COUP {choisir_carte(d.mains[p.moi], d.pli, d.atout, p.moi, d.jouees, d.preneur)}")
    app.sel = 0
    app.dessiner_jeu()
    rendre(app.ecran)

asyncio.run(principal())
