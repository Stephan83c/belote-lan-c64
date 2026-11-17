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


def vides(plis: list[list[tuple[int, int]]], atout: int) -> list[set[int]]:
    """Couleurs qu'une place n'a plus, déduites de ce qu'elle a joué (règles 5.3)."""
    v: list[set[int]] = [set() for _ in range(4)]
    for pli in plis:
        if not pli:
            continue
        demandee = couleur(pli[0][1])
        for place, c in pli[1:]:
            if couleur(c) != demandee:
                v[place].add(demandee)                 # n'avait pas la couleur demandée
    return v


def tirer(main: list[int], place: int, plis: list[list[tuple[int, int]]], pli: list[tuple[int, int]],
          atout: int, preneur: int, retournee: int, rng: random.Random) -> list[list[int]] | None:
    """Une répartition plausible des mains des autres places ; None si introuvable."""
    posees = [c for p in plis + [pli] for _, c in p]
    joues_par = [0] * 4
    for p in plis + [pli]:
        for pl, _ in p:
            joues_par[pl] += 1
    besoin = [8 - joues_par[p] for p in range(4)]
    besoin[place] = 0
    connues = set(main) | set(posees)
    inconnues = [c for c in range(32) if c not in connues]
    interdit = vides(plis + [pli], atout)

    for _ in range(60):
        mains: list[list[int]] = [[] for _ in range(4)]
        reste = list(besoin)
        cartes = list(inconnues)
        if preneur != place and retournee in cartes:
            mains[preneur].append(retournee)
            reste[preneur] -= 1
            cartes.remove(retournee)
        rng.shuffle(cartes)
        # les cartes les plus contraintes d'abord
        cartes.sort(key=lambda c: -sum(1 for p in range(4) if p != place and couleur(c) in interdit[p]))
        ok = True
        for c in cartes:
            possibles = [p for p in range(4) if p != place and reste[p] > 0 and couleur(c) not in interdit[p]]
            if not possibles:
                ok = False
                break
            p = rng.choices(possibles, weights=[reste[q] for q in possibles])[0]
            mains[p].append(c)
            reste[p] -= 1
        if ok:
            mains[place] = list(main)
            return mains
    return None


def finir(mains: list[list[int]], pli: list[tuple[int, int]], jouees: list[int], atout: int,
          joueur: int, preneur: int, pts: list[int], plis: list[int], equipe_belote: int | None,
          premiere: int | None) -> tuple[int, int]:
    """Fait jouer les bots actuels jusqu'au bout ; `premiere` : carte imposée à `joueur`."""
    mains = [list(m) for m in mains]
    pli = list(pli)
    jouees = list(jouees)
    pts = list(pts)
    plis = list(plis)
    nb = sum(plis)
    while True:
        if premiere is not None:
            c, premiere = premiere, None
        else:
            c = bots.choisir_carte(mains[joueur], pli, atout, joueur, jouees, preneur)
        mains[joueur].remove(c)
        pli.append((joueur, c))
        jouees.append(c)
        if len(pli) < 4:
            joueur = (joueur + 1) % 4
            continue
        gagnant = gagnant_pli(pli, atout)
        camp = equipe(gagnant)
        pts[camp] += sum(points_carte(x, atout) for _, x in pli)
        plis[camp] += 1
        nb += 1
        pli = []
        joueur = gagnant
        if nb == 8:
            pts[camp] += DIX_DE_DER
            break
    return compter_manche(equipe(preneur), (pts[0], pts[1]), (plis[0], plis[1]), equipe_belote).points


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


def jouer(paquet: list[int], donneur: int, equipe_pimc: int, tirages: int, rng: random.Random):
    d = Donne(donneur, paquet=paquet)
    while d.phase is Phase.ENCHERES:
        p = d.joueur
        choix = bots.choisir_enchere(d.mains[p], d.tour_encheres, d.retournee)
        d.passer(p) if choix is None else d.prendre(p, choix)
    if d.phase is not Phase.JEU:
        return None
    plis: list[list[tuple[int, int]]] = []
    while d.phase is Phase.JEU:
        p = d.joueur
        if equipe(p) == equipe_pimc:
            c = choisir_pimc(d, p, plis, tirages, rng)
        else:
            c = bots.choisir_carte(d.mains[p], d.pli, d.atout, p, d.jouees, d.preneur)
        avant = list(d.pli)
        d.jouer(p, c)
        if not d.pli:
            plis.append(avant + [(p, c)])
    return d.resultat().points


def une_donne(args):
    i, paquet, tirages, graine = args
    rng = random.Random(graine * 100003 + i)
    pimc = actuels = 0
    redonnes = 0
    for equipe_pimc in (0, 1):
        pts = jouer(paquet, i % 4, equipe_pimc, tirages, rng)
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
    ap.add_argument("--graine", type=int, default=1)
    args = ap.parse_args()

    rng = random.Random(args.graine)
    travaux = []
    for i in range(args.n):
        paquet = list(range(32))
        rng.shuffle(paquet)
        travaux.append((i, paquet, args.tirages, args.graine))

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
