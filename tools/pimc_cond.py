#!/usr/bin/env python3
"""Test : PIMC dont les tirages tiennent compte des enchères, contre le PIMC actuel.

python3 tools/pimc_cond.py [N] [--tirages T] [--processus P] [--graine G] [--essais K]

Les deux camps jouent la carte avec le PIMC (belote.pimc) et font leurs enchères avec les règles
actuelles (bots.choisir_enchere) ; seule différence : le camp « conditionné » rejette les
répartitions de cartes cachées incompatibles avec ce que les autres ont dit aux enchères (passé aux
deux tours, ou pris telle couleur). Une répartition est compatible pour un joueur si, parmi K choix
au hasard de 5 cartes de sa main de 8 (ses 5 cartes avant la prise, car les 3 autres viennent du
talon), l'un reproduit exactement ses enchères avec la règle des bots. Les adversaires jouent
justement cette règle : c'est donc un MAJORANT du gain contre des bots, moins sûr contre des humains.
Chaque donne est jouée deux fois, camps échangés (même paquet, même donneur). Prototype : hors serveur.
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

from belote import bots, pimc  # noqa: E402
from belote.moteur import (DAME, ROI, Donne, Phase, carte, coups_legaux, equipe)  # noqa: E402

STATS = [0, 0, 0]       # répartitions tirées, rejetées, coups où aucune répartition compatible n'a été trouvée


def compatible(joueur: int, full8: list[int], preneur: int, retournee: int,
               historique: list[tuple[int, int, int | None]], rng: random.Random, essais: int) -> bool:
    """Un choix de 5 cartes parmi `full8` (sans la retournée pour le preneur) redonne ses enchères."""
    evts = [(t, c) for p, t, c in historique if p == joueur]
    if not evts:
        return True
    pool = [c for c in full8 if not (joueur == preneur and c == retournee)]
    for _ in range(essais):
        initiale = rng.sample(pool, 5)
        if all(bots.choisir_enchere(initiale, t, retournee) == c for t, c in evts):
            return True
    return False


def choisir(d: Donne, place: int, plis: list, historique: list, tirages: int, rng: random.Random,
            conditionne: bool, essais: int) -> int:
    main = d.mains[place]
    legaux = coups_legaux(main, d.pli, d.atout, place)
    if len(legaux) == 1:
        return legaux[0]
    pose_par: list[list[int]] = [[] for _ in range(4)]
    for p in plis + [d.pli]:
        for pl, c in p:
            pose_par[pl].append(c)
    roi, dame = carte(d.atout, ROI), carte(d.atout, DAME)
    total = {c: 0 for c in legaux}
    valides = 0
    for _ in range(tirages):
        mains = None
        for _essai in range(40 if conditionne else 1):
            m = pimc.tirer(main, place, plis, d.pli, d.atout, d.preneur, d.retournee, rng)
            if m is None:
                continue
            if conditionne:
                STATS[0] += 1
            if not conditionne or all(
                    q == place or compatible(q, m[q] + pose_par[q], d.preneur, d.retournee, historique, rng, essais)
                    for q in range(4)):
                mains = m
                break
            STATS[1] += 1
        if mains is None:
            if conditionne:
                STATS[2] += 1
            continue
        valides += 1
        eb = None
        for p in range(4):
            tout = set(mains[p]) | set(pose_par[p])
            if roi in tout and dame in tout:
                eb = equipe(p)
        for c in legaux:
            pts = pimc.finir(mains, d.pli, d.jouees, d.atout, place, d.preneur,
                             list(d.points_cartes), list(d.plis_gagnes), eb, c)
            total[c] += pts[equipe(place)] - pts[1 - equipe(place)]
    if not valides:
        return bots.choisir_carte(main, d.pli, d.atout, place, d.jouees, d.preneur)
    return max(legaux, key=lambda c: total[c])


def jouer(paquet: list[int], donneur: int, equipe_cond: int, tirages: int, rng: random.Random, essais: int):
    d = Donne(donneur, paquet=paquet)
    historique: list[tuple[int, int, int | None]] = []
    while d.phase is Phase.ENCHERES:
        p, tour = d.joueur, d.tour_encheres
        choix = bots.choisir_enchere(d.mains[p], tour, d.retournee)
        historique.append((p, tour, choix))
        d.passer(p) if choix is None else d.prendre(p, choix)
    if d.phase is not Phase.JEU:
        return None
    plis: list[list[tuple[int, int]]] = []
    while d.phase is Phase.JEU:
        p = d.joueur
        c = choisir(d, p, plis, historique, tirages, rng, equipe(p) == equipe_cond, essais)
        avant = list(d.pli)
        d.jouer(p, c)
        if not d.pli:
            plis.append(avant + [(p, c)])
    return d.resultat().points


def une_donne(args):
    i, paquet, tirages, graine, essais = args
    rng = random.Random(graine * 100003 + i)
    STATS[:] = [0, 0, 0]
    cond = simple = redonnes = 0
    for equipe_cond in (0, 1):
        pts = jouer(paquet, i % 4, equipe_cond, tirages, rng, essais)
        if pts is None:
            redonnes += 1
            continue
        cond += pts[equipe_cond]
        simple += pts[1 - equipe_cond]
    return cond, simple, redonnes, tuple(STATS)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("n", nargs="?", type=int, default=2000, help="donnes (chacune jouée deux fois)")
    ap.add_argument("--tirages", type=int, default=30)
    ap.add_argument("--essais", type=int, default=8, help="choix de 5 cartes testés par joueur et par répartition")
    ap.add_argument("--processus", type=int, default=8)
    ap.add_argument("--graine", type=int, default=1)
    args = ap.parse_args()

    rng = random.Random(args.graine)
    travaux = []
    for i in range(args.n):
        paquet = list(range(32))
        rng.shuffle(paquet)
        travaux.append((i, paquet, args.tirages, args.graine, args.essais))

    debut = time.time()
    cond = simple = redonnes = faites = 0
    st = [0, 0, 0]
    with Pool(args.processus) as pool:
        for a, b, r, s in pool.imap_unordered(une_donne, travaux):
            cond += a
            simple += b
            redonnes += r
            st = [x + y for x, y in zip(st, s)]
            faites += 1
            if faites % 100 == 0 or faites == args.n:
                print(f"{faites}/{args.n} donnes, {time.time() - debut:.0f} s : conditionné "
                      f"{100 * cond / max(1, cond + simple):.2f} %", flush=True)
    total = 2 * args.n
    print(f"{total} parties ({redonnes} redonnées), {args.tirages} tirages : conditionné {cond} points, "
          f"simple {simple} points")
    print(f"part du PIMC conditionné : {100 * cond / (cond + simple):.2f} %, écart moyen "
          f"{(cond - simple) / total:+.2f} points par donne ; {(time.time() - debut) / total:.2f} s par partie")
    print(f"répartitions tirées par le conditionné : {st[0]}, rejetées {100 * st[1] / max(1, st[0]):.1f} %, "
          f"coups sans répartition compatible {st[2]}")


if __name__ == "__main__":
    main()
