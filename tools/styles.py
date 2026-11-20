#!/usr/bin/env python3
"""Prototype : bots à style (BOT1x attaquant, BOT2x défenseur, BOT3x modéré, BOT4x adaptatif).

python3 tools/styles.py [N] [--tirages T] [--processus P] [--graine G] [--cible C] [--duel A B]

Hors serveur : rien de ce fichier n'est utilisé par le jeu. Un style règle deux choses :
  - les enchères : seuil de prise (valeur de la main, bots.valeur_main) ;
  - le jeu de la carte : le PIMC (belote.pimc) simule la fin de donne et note chaque carte
    selon l'objectif du style (voir `utilite`).
Le tournoi joue des PARTIES entières jusqu'à la cible (1000), chaque style contre chaque autre,
équipes de deux bots du même style, chaque partie jouée deux fois avec les mêmes paquets, camps
échangés. On mesure le taux de victoire de la partie (le vrai enjeu pour un style qui attaque
ou se défend) et la part des points.
"""

from __future__ import annotations

import argparse
import itertools
import random
import sys
import time
from dataclasses import dataclass, replace
from multiprocessing import Pool
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "server"))

from belote import bots  # noqa: E402
from belote.moteur import (DAME, ROI, Donne, Phase, carte, compter_manche, coups_legaux,  # noqa: E402
                           equipe, equipe_gagnante)
from belote.pimc import finir, tirer  # noqa: E402

CIBLE = 1000


@dataclass(frozen=True)
class Style:
    code: int          # premier chiffre du nom : BOT<code><variante>
    nom: str
    seuil: int         # seuil de prise (valeur de la main) ; 32 = bots actuels
    objectif: str      # 'attaque', 'defense', 'ecart', 'adaptatif'
    decalage: int = 0  # variante : décale tous les seuils (BOT11 -2, BOT12 0, BOT13 +2)
    tolerance: float = 0.0  # feinteur : points d'écart qu'il accepte de perdre pour surprendre


STYLES = {
    1: Style(1, "attaquant", 26, "attaque"),
    2: Style(2, "defenseur", 34, "defense"),
    3: Style(3, "modere", 32, "ecart"),
    4: Style(4, "adaptatif", 32, "adaptatif"),
    5: Style(5, "feinteur", 32, "ecart", tolerance=3.0),
}

# Compteurs du feinteur (par processus, remis à zéro à chaque partie).
FEINTES = [0, 0, 0]   # ses coups décidés par le PIMC, feintes possibles, feintes réellement jouées


# Second chiffre du nom : de petits décalages des seuils de prise, pour que deux bots du même style
# à la même table ne jouent pas tout à fait pareil.
VARIANTES = {1: -2, 2: 0, 3: 2}


def style_de(numero: int) -> Style:
    """5 -> rien ; 1 à 4 : le style tel quel ; 11 à 43 : style (dizaine) et variante (unité)."""
    if numero < 10:
        return STYLES[numero]
    return replace(STYLES[numero // 10], decalage=VARIANTES[numero % 10])


def nom_bot(code: int, variante: int) -> str:
    return f"BOT{code}{variante}"


def mode(style: Style, mon_score: int, son_score: int) -> tuple[str, int]:
    """(objectif, seuil) effectifs : l'adaptatif attaque s'il est mené, se défend s'il mène."""
    d = style.decalage
    if style.objectif != "adaptatif":
        return style.objectif, style.seuil + d
    retard = son_score - mon_score
    if retard >= 150 or son_score >= CIBLE - 200 > mon_score:
        return "attaque", 26 + d
    if retard <= -150:
        return "defense", 38 + d
    return "ecart", 32 + d


def utilite(objectif: str, mes: int, leurs: int) -> float:
    """Note d'une fin de donne simulée (points de mon camp, points de l'autre)."""
    if objectif == "attaque":       # convexe : le capot et les grosses manches pèsent lourd
        return (mes / 100) ** 2 - (leurs / 100) ** 2 * 0.5
    if objectif == "defense":       # gagner la manche (réussir le contrat ou le faire chuter)
        return 100.0 * (mes > leurs) + 0.1 * (mes - leurs)
    return float(mes - leurs)       # écart de points, comme le PIMC du serveur


def enchere(style: Style, d: Donne, p: int, scores: list[int]) -> int | None:
    _, seuil = mode(style, scores[equipe(p)], scores[1 - equipe(p)])
    main, r = d.mains[p], d.retournee
    if d.tour_encheres == 1:
        candidates = [r // 8]
    else:
        candidates = [c for c in range(4) if c != r // 8]
    meilleure = max(candidates, key=lambda c: bots.valeur_main(main, c, r))
    return meilleure if bots.valeur_main(main, meilleure, r) >= seuil else None


def choisir_carte(style: Style, d: Donne, place: int, plis: list, scores: list[int],
                  tirages: int, rng: random.Random) -> int:
    main = d.mains[place]
    legaux = coups_legaux(main, d.pli, d.atout, place)
    if len(legaux) == 1:
        return legaux[0]
    objectif, _ = mode(style, scores[equipe(place)], scores[1 - equipe(place)])
    pose_par: list[set[int]] = [set() for _ in range(4)]
    for p in plis + [d.pli]:
        for pl, c in p:
            pose_par[pl].add(c)
    roi, dame = carte(d.atout, ROI), carte(d.atout, DAME)
    mon_camp = equipe(place)
    total = {c: 0.0 for c in legaux}
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
            pts = finir(mains, d.pli, d.jouees, d.atout, place, d.preneur,
                        list(d.points_cartes), list(d.plis_gagnes), eb, c)
            total[c] += utilite(objectif, pts[mon_camp], pts[1 - mon_camp])
    if not valides:
        return bots.choisir_carte(main, d.pli, d.atout, place, d.jouees, d.preneur)
    meilleure = max(legaux, key=lambda c: total[c])
    if style.tolerance <= 0:
        return meilleure
    FEINTES[0] += 1
    # Feinte : parmi les cartes presque aussi bonnes que la meilleure, jouer une carte AUTRE que celle
    # que la règle habituelle (bots.choisir_carte) jouerait : un humain qui lit le jeu se trompe.
    # Jamais quand le partenaire tient le pli (on ne le trompe pas, on le charge).
    from belote.moteur import gagnant_pli, partenaire
    if d.pli and gagnant_pli(d.pli, d.atout) == partenaire(place):
        return meilleure
    proches = [c for c in legaux if (total[meilleure] - total[c]) / valides <= style.tolerance]
    naturelle = bots.choisir_carte(main, d.pli, d.atout, place, d.jouees, d.preneur)
    autres = [c for c in proches if c != naturelle]
    if naturelle not in proches or not autres:
        return meilleure        # la meilleure carte n'est déjà pas la règle, ou pas d'alternative
    FEINTES[1] += 1
    choix = rng.choice(autres)
    FEINTES[2] += choix != meilleure
    return choix


def manche(paquet: list[int], donneur: int, styles: list[Style], scores: list[int], reserve: int,
           tirages: int, rng: random.Random):
    """Une manche ; styles[p] joue la place p. Renvoie ResultatManche, ou None si tous passent."""
    d = Donne(donneur, paquet=paquet)
    while d.phase is Phase.ENCHERES:
        p = d.joueur
        choix = enchere(styles[p], d, p, scores)
        d.passer(p) if choix is None else d.prendre(p, choix)
    if d.phase is not Phase.JEU:
        return None
    plis: list[list[tuple[int, int]]] = []
    while d.phase is Phase.JEU:
        p = d.joueur
        c = choisir_carte(styles[p], d, p, plis, scores, tirages, rng)
        avant = list(d.pli)
        d.jouer(p, c)
        if not d.pli:
            plis.append(avant + [(p, c)])
    return d.resultat(reserve)


def partie(graine: int, a: Style, b: Style, a_equipe: int, tirages: int, cible: int = CIBLE):
    """Une partie entière ; a joue l'équipe `a_equipe`. Renvoie (équipe gagnante, scores, manches)."""
    return partie_styles(graine, [a if equipe(p) == a_equipe else b for p in range(4)], tirages, cible)


def partie_styles(graine: int, styles: list[Style], tirages: int, cible: int = CIBLE):
    """Une partie entière ; styles[p] joue la place p."""
    scores, reserve, donneur, k = [0, 0], 0, 0, 0
    rng = random.Random(graine)
    while k < 60:
        paquet = list(range(32))
        random.Random(graine * 1009 + k).shuffle(paquet)     # mêmes paquets dans les deux camps
        k += 1
        res = manche(paquet, donneur, styles, scores, reserve, tirages, rng)
        donneur = (donneur + 1) % 4
        if res is None:
            continue
        reserve = res.reserve
        scores[0] += res.points[0]
        scores[1] += res.points[1]
        g = equipe_gagnante(scores, cible)
        if g is not None:
            return g, scores, k
    return (0 if scores[0] >= scores[1] else 1), scores, k


def travail_table(args):
    """Une table au hasard SANS DOUBLON (4 styles différents parmi 5, variantes tirées), jouée deux
    fois avec les mêmes paquets : la 2e fois, chacun passe dans l'autre camp (décalage d'une place)."""
    i, graine, tirages, cible = args
    hasard = random.Random(graine)
    codes = hasard.sample(list(STYLES), 4)                  # pas deux fois le même style
    joueurs = [code * 10 + hasard.choice(list(VARIANTES)) for code in codes]
    sortie = []
    FEINTES[:] = [0, 0, 0]
    for decalage in (0, 1):
        place_de = [joueurs[(p + decalage) % 4] for p in range(4)]       # numero (style, variante) par place
        g, scores, k = partie_styles(graine, [style_de(n) for n in place_de], tirages, cible)
        for p, n in enumerate(place_de):
            sortie.append((n, equipe(p) == g, scores[equipe(p)], scores[1 - equipe(p)],
                           place_de[(p + 2) % 4]))
    return sortie


def travail(args):
    i, graine, ca, cb, a_equipe, tirages, cible = args
    FEINTES[:] = [0, 0, 0]
    g, scores, k = partie(graine, style_de(ca), style_de(cb), a_equipe, tirages, cible)
    return i, ca, cb, g == a_equipe, scores[a_equipe], scores[1 - a_equipe], k, tuple(FEINTES)


def tables(args) -> None:
    travaux = [(i, args.graine * 100003 + i, args.tirages, args.cible) for i in range(args.n)]
    par_style = {c: [0, 0, 0, 0] for c in STYLES}              # victoires, parties, points pour, contre
    par_duo = {}                                               # (style, style) trié : victoires, parties
    debut = time.time()
    with Pool(args.processus) as pool:
        for fait, sortie in enumerate(pool.imap_unordered(travail_table, travaux), 1):
            for n, gagne, pour, contre, partenaire_n in sortie:
                st = par_style[n // 10]
                st[0] += gagne
                st[1] += 1
                st[2] += pour
                st[3] += contre
                duo = par_duo.setdefault(tuple(sorted((n // 10, partenaire_n // 10))), [0, 0])
                duo[0] += gagne
                duo[1] += 1
            if fait % 50 == 0 or fait == len(travaux):
                print(f"{fait}/{len(travaux)} tables, {time.time() - debut:.0f} s", flush=True)
    print(f"\nTables aléatoires sans doublon : {args.n} tables x 2 (camps échangés), cible {args.cible}, "
          f"{args.tirages} tirages. 50 % = à égalité.")
    print("Par style (chaque joueur compté à chaque partie) :")
    for c, (v, n, pour, contre) in sorted(par_style.items(), key=lambda x: -x[1][0] / max(1, x[1][1])):
        print(f"  {STYLES[c].nom:<10} BOT{c}x : {100 * v / n:5.1f} % de victoires, "
              f"{100 * pour / (pour + contre):.1f} % des points ({n} parties)")
    print("Par duo de partenaires (victoires du duo) :")
    for (a, b), (v, n) in sorted(par_duo.items(), key=lambda x: -x[1][0] / x[1][1]):
        print(f"  {STYLES[a].nom} + {STYLES[b].nom} : {100 * v / n:5.1f} % ({n} parties)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("n", nargs="?", type=int, default=40, help="parties par paire (jouées deux fois)")
    ap.add_argument("--tirages", type=int, default=30)
    ap.add_argument("--processus", type=int, default=8)
    ap.add_argument("--graine", type=int, default=1)
    ap.add_argument("--cible", type=int, default=CIBLE)
    ap.add_argument("--duel", type=int, nargs=2, metavar=("A", "B"), help="une seule paire (codes 1 à 4)")
    ap.add_argument("--tables", action="store_true",
                    help="tables aléatoires sans doublon de style (N tables, chacune jouée deux fois)")
    ap.add_argument("--variantes", type=int, metavar="CODE",
                    help="compare entre elles les variantes 1, 2, 3 d'un style (BOT<CODE>1, 2, 3)")
    ap.add_argument("--tolerance", type=float, help="tolérance du feinteur (points d'écart), défaut 3")
    ap.add_argument("--seulement", type=int, metavar="CODE", help="seulement les paires où ce style joue")
    ap.add_argument("--seuil", type=int, nargs=2, action="append", default=[], metavar=("CODE", "SEUIL"),
                    help="change le seuil de prise d'un style (répétable)")
    args = ap.parse_args()
    if args.tolerance is not None:
        STYLES[5] = replace(STYLES[5], tolerance=args.tolerance)
    for code, seuil in args.seuil:
        STYLES[code] = replace(STYLES[code], seuil=seuil)

    if args.tables:
        tables(args)
        return
    if args.variantes:
        c = args.variantes
        paires = [(c * 10 + 1, c * 10 + 2), (c * 10 + 2, c * 10 + 3), (c * 10 + 1, c * 10 + 3)]
    else:
        paires = None
    if paires is None:
        paires = [tuple(args.duel)] if args.duel else list(itertools.combinations(STYLES, 2))
    if args.seulement:
        paires = [p for p in paires if args.seulement in p]
    travaux = [(i, args.graine * 100003 + i, a, b, eq, args.tirages, args.cible)
               for a, b in paires for i in range(args.n) for eq in (0, 1)]
    stats = {p: [0, 0, 0, 0, 0] for p in paires}      # victoires de a, parties, pts a, pts b, manches
    feintes = {p: [0, 0, 0] for p in paires}
    debut = time.time()
    with Pool(args.processus) as pool:
        for fait, (_, a, b, gagne, pa, pb, k, fe) in enumerate(pool.imap_unordered(travail, travaux), 1):
            s = stats[(a, b)]
            s[0] += gagne
            s[1] += 1
            s[2] += pa
            s[3] += pb
            s[4] += k
            feintes[(a, b)] = [x + y for x, y in zip(feintes[(a, b)], fe)]
            if fait % 20 == 0 or fait == len(travaux):
                print(f"{fait}/{len(travaux)} parties, {time.time() - debut:.0f} s", flush=True)

    if args.variantes:
        print(f"\nVariantes de {STYLES[args.variantes].nom} ({args.n} parties x 2 camps par paire) :")
        for (a, b), s in stats.items():
            print(f"  BOT{a} contre BOT{b} : {100 * s[0] / s[1]:.1f} % de victoires, "
                  f"{100 * s[2] / (s[2] + s[3]):.1f} % des points")
        return
    print(f"\nTaux de victoire de la partie à {args.cible} (ligne contre colonne), {args.n} parties "
          f"x 2 camps par paire, {args.tirages} tirages par coup")
    codes = list(STYLES)
    print(" " * 12 + "".join(f"{STYLES[c].nom[:9]:>11}" for c in codes) + "   moyenne")
    moyennes = {c: [] for c in codes}
    for a in codes:
        ligne = f"{STYLES[a].nom:<12}"
        for b in codes:
            if a == b:
                ligne += f"{'-':>11}"
                continue
            if (a, b) in stats:
                s = stats[(a, b)]
                taux = 100 * s[0] / s[1]
            elif (b, a) in stats:
                s = stats[(b, a)]
                taux = 100 - 100 * s[0] / s[1]
            else:
                ligne += f"{'':>11}"
                continue
            moyennes[a].append(taux)
            ligne += f"{taux:>10.1f}%"
        ligne += f"   {sum(moyennes[a]) / len(moyennes[a]):.1f} %" if moyennes[a] else ""
        print(ligne)
    if any(5 in p for p in paires):
        # Les compteurs mélangent les deux camps : on ne garde que les paires où joue le feinteur.
        tot = [sum(feintes[p][i] for p in paires if 5 in p) for i in range(3)]
        print(f"\nFeinteur : {tot[0]} coups à plusieurs cartes décidés par le PIMC, "
              f"{100 * tot[1] / max(1, tot[0]):.1f} % avec une feinte possible, "
              f"{100 * tot[2] / max(1, tot[0]):.1f} % de feintes réellement jouées")
    print("\nPart des points marqués et nombre moyen de manches par partie :")
    for (a, b), s in stats.items():
        print(f"  {STYLES[a].nom} - {STYLES[b].nom} : {100 * s[2] / (s[2] + s[3]):.1f} % des points, "
              f"{s[4] / s[1]:.1f} manches")


if __name__ == "__main__":
    main()
