#!/usr/bin/env python3
"""Test : PIMC qui déduit « plus d'atout » d'une défausse, contre le PIMC actuel (règle v2.1).

python3 tools/pimc_atout.py [N] [--tirages T] [--processus P] [--graine G]

Depuis la v2.1 (sous-coupe obligatoire), un joueur qui n'a pas la couleur demandée et dont
l'adversaire est maître doit jouer atout, même plus faible. S'il se défausse d'une autre couleur,
c'est qu'il n'a plus aucun atout. Le PIMC actuel (belote.pimc.vides) ne déduit que les couleurs
non fournies ; le camp « déduction » ajoute l'atout aux couleurs vides de ce joueur.
Attention : contre un humain sur client v2.0, la tolérance du serveur (coups_toleres) laisse
encore passer la défausse avec un petit atout en main ; la déduction serait alors fausse.
Les deux camps font leurs enchères avec les règles actuelles (bots.choisir_enchere).
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
from belote.moteur import (DAME, ROI, Donne, Phase, carte, couleur, coups_legaux, equipe,  # noqa: E402
                           gagnant_pli, partenaire)

VIDES_ACTUEL = pimc.vides
STATS = [0]   # déductions « plus d'atout » ajoutées


def vides_atout(plis: list[list[tuple[int, int]]], atout: int) -> list[set[int]]:
    """Comme pimc.vides, plus : défausse alors qu'un adversaire est maître = plus d'atout."""
    v = VIDES_ACTUEL(plis, atout)
    for pli in plis:
        if not pli:
            continue
        demandee = couleur(pli[0][1])
        if demandee == atout:
            continue                                   # déjà couvert : pas d'atout fourni = plus d'atout
        for k in range(1, len(pli)):
            place, c = pli[k]
            if couleur(c) in (demandee, atout):
                continue
            if gagnant_pli(pli[:k], atout) != partenaire(place) and atout not in v[place]:
                v[place].add(atout)
                STATS[0] += 1
    return v


def choisir(d: Donne, place: int, plis: list, tirages: int, rng: random.Random, deduction: bool) -> int:
    main = d.mains[place]
    legaux = coups_legaux(main, d.pli, d.atout, place)
    if len(legaux) == 1:
        return legaux[0]
    pimc.vides = vides_atout if deduction else VIDES_ACTUEL
    pose_par: list[list[int]] = [[] for _ in range(4)]
    for p in plis + [d.pli]:
        for pl, c in p:
            pose_par[pl].append(c)
    roi, dame = carte(d.atout, ROI), carte(d.atout, DAME)
    total = {c: 0 for c in legaux}
    valides = 0
    for _ in range(tirages):
        mains = pimc.tirer(main, place, plis, d.pli, d.atout, d.preneur, d.retournee, rng)
        if mains is None:
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
    pimc.vides = VIDES_ACTUEL
    if not valides:
        return bots.choisir_carte(main, d.pli, d.atout, place, d.jouees, d.preneur)
    return max(legaux, key=lambda c: total[c])


def jouer(paquet: list[int], donneur: int, equipe_ded: int, tirages: int, rng: random.Random):
    d = Donne(donneur, paquet=paquet)
    while d.phase is Phase.ENCHERES:
        p, tour = d.joueur, d.tour_encheres
        choix = bots.choisir_enchere(d.mains[p], tour, d.retournee)
        d.passer(p) if choix is None else d.prendre(p, choix)
    if d.phase is not Phase.JEU:
        return None
    plis: list[list[tuple[int, int]]] = []
    while d.phase is Phase.JEU:
        p = d.joueur
        c = choisir(d, p, plis, tirages, rng, equipe(p) == equipe_ded)
        avant = list(d.pli)
        d.jouer(p, c)
        if not d.pli:
            plis.append(avant + [(p, c)])
    return d.resultat().points


def une_donne(args):
    i, paquet, tirages, graine = args
    rng = random.Random(graine * 100003 + i)
    STATS[0] = 0
    ded = simple = redonnes = 0
    for equipe_ded in (0, 1):
        pts = jouer(paquet, i % 4, equipe_ded, tirages, rng)
        if pts is None:
            redonnes += 1
            continue
        ded += pts[equipe_ded]
        simple += pts[1 - equipe_ded]
    return ded, simple, redonnes, STATS[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("n", nargs="?", type=int, default=2000, help="donnes (chacune jouée deux fois)")
    ap.add_argument("--tirages", type=int, default=30)
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
    ded = simple = redonnes = faites = deductions = 0
    with Pool(args.processus) as pool:
        for a, b, r, s in pool.imap_unordered(une_donne, travaux):
            ded += a
            simple += b
            redonnes += r
            deductions += s
            faites += 1
            if faites % 200 == 0 or faites == args.n:
                print(f"{faites}/{args.n} donnes, {time.time() - debut:.0f} s : déduction "
                      f"{100 * ded / max(1, ded + simple):.2f} %", flush=True)
    total = 2 * args.n
    print(f"{total} parties ({redonnes} redonnées), {args.tirages} tirages : déduction {ded} points, "
          f"actuel {simple} points")
    print(f"part du PIMC avec déduction : {100 * ded / (ded + simple):.2f} %, écart moyen "
          f"{(ded - simple) / total:+.2f} points par donne ; {(time.time() - debut) / total:.2f} s par partie")
    print(f"déductions « plus d'atout » ajoutées (appels de vides) : {deductions}")


if __name__ == "__main__":
    main()
