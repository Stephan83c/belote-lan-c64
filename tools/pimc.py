#!/usr/bin/env python3
"""Prototype PIMC (Perfect Information Monte Carlo) pour le jeu de la carte.

python3 tools/pimc.py [N] [--tirages T] [--processus P] [--graine G]

Le bot PIMC joue contre les bots actuels (server/belote/bots.py). Les enchères restent
celles des bots actuels : seul le choix de la carte change. Pour chaque carte jouable, le
bot tire T répartitions plausibles des cartes cachées (couleurs manquantes déduites des
plis, retournée chez le preneur), finit la donne en faisant jouer les bots actuels à
tout le monde, et garde la carte qui rapporte le plus d'écart de points en moyenne.
Chaque donne est jouée deux fois, équipes échangées (même paquet, même donneur).
Prototype : le serveur n'est pas touché.
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "server"))

from belote import bots  # noqa: E402
from belote.moteur import (DIX_DE_DER, ROI, DAME, Donne, Phase, carte, compter_manche,  # noqa: E402
                           couleur, coups_legaux, equipe, gagnant_pli, partenaire, points_carte)


from belote.pimc import choisir, finir, tirer, vides  # noqa: E402,F401


def choisir_pimc(d: Donne, place: int, plis: list[list[tuple[int, int]]], tirages: int,
                 rng: random.Random) -> int:
    main = d.mains[place]
    legaux = coups_legaux(main, d.pli, d.atout, place)
    if len(legaux) == 1:
        return legaux[0]

    # Points et plis déjà faits, et qui a posé quoi (pour la belote).
    pts = list(d.points_cartes)
    plis_g = list(d.plis_gagnes)
    pose_par: list[set[int]] = [set() for _ in range(4)]
    for p in plis + [d.pli]:
        for pl, c in p:
            pose_par[pl].add(c)
    roi, dame = carte(d.atout, ROI), carte(d.atout, DAME)

    total = {c: 0 for c in legaux}
    valides = 0
    for _ in range(tirages):
        mains = tirer(main, place, plis, d.pli, d.atout, d.preneur, d.retournee, rng)
        if mains is None:
            continue
        valides += 1
        eb = None
        for p in range(4):
            tout = set(mains[p]) | pose_par[p]
            if roi in tout and dame in tout:
                eb = equipe(p)
        for c in legaux:
            pts_f = finir(mains, d.pli, d.jouees, d.atout, place, d.preneur, pts, plis_g, eb, c)
            total[c] += pts_f[equipe(place)] - pts_f[1 - equipe(place)]
    if not valides:
        return bots.choisir_carte(main, d.pli, d.atout, place, d.jouees, d.preneur)
    return max(legaux, key=lambda c: total[c])


def valeur_prise(main: list[int], place: int, donneur: int, retournee: int, atout: int,
                 tirages: int, rng: random.Random) -> float:
    """Écart moyen de points (mon camp moins l'autre) si `place` prend à `atout` : elle ramasse
    la retournée et 2 cartes du talon tirées au hasard, les autres complètent à 8 cartes."""
    inconnues = [c for c in range(32) if c not in main and c != retournee]
    roi, dame = carte(atout, ROI), carte(atout, DAME)
    meme_camp = equipe(place)
    total = 0
    for _ in range(tirages):
        rng.shuffle(inconnues)
        mains: list[list[int]] = [[] for _ in range(4)]
        mains[place] = main + [retournee] + inconnues[:2]
        reste = inconnues[2:]
        k = 0
        for p in range(4):
            if p != place:
                mains[p] = reste[k:k + 8]
                k += 8
        eb = None
        for p in range(4):
            if roi in mains[p] and dame in mains[p]:
                eb = equipe(p)
        pts = finir(mains, [], [], atout, (donneur + 1) % 4, place, [0, 0], [0, 0], eb, None)
        total += pts[meme_camp] - pts[1 - meme_camp]
    return total / tirages


def enchere_pimc(main: list[int], tour: int, retournee: int, place: int, donneur: int,
                 tirages: int, seuil: float, rng: random.Random) -> int | None:
    if tour == 1:
        candidates = [couleur(retournee)]
    else:
        candidates = [c for c in range(4) if c != couleur(retournee)]
    meilleur, v = max(((c, valeur_prise(main, place, donneur, retournee, c, tirages, rng))
                       for c in candidates), key=lambda x: x[1])
    return meilleur if v >= seuil else None


def jouer(paquet: list[int], donneur: int, equipe_pimc: int, tirages: int, rng: random.Random,
          enchere: str = "actuel", cartes: str = "pimc", seuil: float = 0.0):
    d = Donne(donneur, paquet=paquet)
    while d.phase is Phase.ENCHERES:
        p = d.joueur
        if enchere == "pimc" and equipe(p) == equipe_pimc:
            choix = enchere_pimc(d.mains[p], d.tour_encheres, d.retournee, p, donneur, tirages, seuil, rng)
        else:
            choix = bots.choisir_enchere(d.mains[p], d.tour_encheres, d.retournee)
        d.passer(p) if choix is None else d.prendre(p, choix)
    if d.phase is not Phase.JEU:
        return None
    plis: list[list[tuple[int, int]]] = []
    while d.phase is Phase.JEU:
        p = d.joueur
        if cartes == "pimc" and equipe(p) == equipe_pimc:
            c = choisir_pimc(d, p, plis, tirages, rng)
        else:
            c = bots.choisir_carte(d.mains[p], d.pli, d.atout, p, d.jouees, d.preneur)
        avant = list(d.pli)
        d.jouer(p, c)
        if not d.pli:
            plis.append(avant + [(p, c)])
    return d.resultat().points


def une_donne(args):
    i, paquet, tirages, graine, enchere, cartes, seuil = args
    rng = random.Random(graine * 100003 + i)
    pimc = actuels = 0
    redonnes = 0
    for equipe_pimc in (0, 1):
        pts = jouer(paquet, i % 4, equipe_pimc, tirages, rng, enchere, cartes, seuil)
        if pts is None:
            redonnes += 1
            continue
        pimc += pts[equipe_pimc]
        actuels += pts[1 - equipe_pimc]
    return i, pimc, actuels, redonnes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("n", nargs="?", type=int, default=100, help="donnes (chacune jouée deux fois)")
    ap.add_argument("--tirages", type=int, default=30, help="répartitions tirées par coup")
    ap.add_argument("--processus", type=int, default=8)
    ap.add_argument("--encheres", choices=("actuel", "pimc"), default="actuel")
    ap.add_argument("--cartes", choices=("actuel", "pimc"), default="pimc")
    ap.add_argument("--seuil", type=float, default=0.0, help="écart moyen minimal pour prendre (PIMC)")
    ap.add_argument("--graine", type=int, default=1)
    args = ap.parse_args()

    rng = random.Random(args.graine)
    travaux = []
    for i in range(args.n):
        paquet = list(range(32))
        rng.shuffle(paquet)
        travaux.append((i, paquet, args.tirages, args.graine, args.encheres, args.cartes, args.seuil))

    debut = time.time()
    pimc = actuels = redonnes = faites = 0
    with Pool(args.processus) as pool:
        for _, a, b, r in pool.imap_unordered(une_donne, travaux):
            pimc += a
            actuels += b
            redonnes += r
            faites += 1
            if faites % 10 == 0 or faites == args.n:
                part = 100 * pimc / max(1, pimc + actuels)
                print(f"{faites}/{args.n} donnes, {time.time() - debut:.0f} s : PIMC {part:.2f} %", flush=True)
    total = 2 * args.n
    print(f"{total} parties ({redonnes} redonnées), {args.tirages} tirages : PIMC {pimc} points, "
          f"actuels {actuels} points")
    print(f"part du PIMC : {100 * pimc / (pimc + actuels):.2f} %, écart moyen {(pimc - actuels) / total:+.2f} "
          f"points par donne ; {(time.time() - debut) / total:.2f} s par partie")


if __name__ == "__main__":
    main()
