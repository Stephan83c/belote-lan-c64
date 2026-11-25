"""Bots PIMC (Perfect Information Monte Carlo) pour le jeu de la carte (SPEC 4.4).

Pour chaque carte jouable, on tire `tirages` répartitions plausibles des cartes cachées
(couleurs manquantes déduites des plis, retournée chez le preneur), on finit la donne en
faisant jouer la stratégie simple (bots.py) à tout le monde, et on garde la carte qui
rapporte le plus d'écart de points en moyenne. Mesuré avec tools/pimc.py : environ 56 %
des points contre la stratégie simple. Les fonctions ne prennent que des données simples
(listes, entiers) : elles tournent dans un autre processus (voir Table._action_bot).
"""

from __future__ import annotations

import random

from . import bots
from .styles import utilite
from .moteur import (DIX_DE_DER, ROI, DAME, carte, compter_manche, couleur, coups_legaux,
                     equipe, gagnant_pli, points_carte)

TIRAGES = 100

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


def choisir(main: list[int], pli: list[tuple[int, int]], plis: list[list[tuple[int, int]]],
            jouees: list[int], atout: int, place: int, preneur: int, retournee: int,
            points_cartes: list[int], plis_gagnes: list[int], tirages: int = TIRAGES,
            rng: random.Random | None = None, objectif: str = "ecart", tolerance: float = 0.0) -> int:
    """Carte à jouer ; toujours un coup légal (repli : stratégie simple).

    `objectif` note chaque fin de donne simulée (styles.utilite). Avec une `tolerance` (feinteur),
    parmi les cartes à moins de `tolerance` d'écart moyen de la meilleure, joue une carte autre que
    celle de la stratégie simple, sauf quand le partenaire tient le pli.
    """
    rng = rng or random.Random()
    legaux = coups_legaux(main, pli, atout, place)
    if len(legaux) == 1:
        return legaux[0]
    pose_par: list[set[int]] = [set() for _ in range(4)]
    for p in plis + [pli]:
        for pl, c in p:
            pose_par[pl].add(c)
    roi, dame = carte(atout, ROI), carte(atout, DAME)
    total = {c: 0.0 for c in legaux}
    valides = 0
    for _ in range(tirages):
        mains = tirer(main, place, plis, pli, atout, preneur, retournee, rng)
        if mains is None:
            continue
        valides += 1
        eb = None
        for p in range(4):
            if roi in set(mains[p]) | pose_par[p] and dame in set(mains[p]) | pose_par[p]:
                eb = equipe(p)
        for c in legaux:
            pts = finir(mains, pli, jouees, atout, place, preneur, points_cartes, plis_gagnes, eb, c)
            total[c] += utilite(objectif, pts[equipe(place)], pts[1 - equipe(place)])
    if not valides:
        return bots.choisir_carte(main, pli, atout, place, jouees, preneur)
    meilleure = max(legaux, key=lambda c: total[c])
    if tolerance <= 0 or (pli and gagnant_pli(pli, atout) == (place + 2) % 4):
        return meilleure
    proches = [c for c in legaux if (total[meilleure] - total[c]) / valides <= tolerance]
    naturelle = bots.choisir_carte(main, pli, atout, place, jouees, preneur)
    autres = [c for c in proches if c != naturelle]
    if naturelle not in proches or not autres:
        return meilleure        # la meilleure n'est déjà pas la carte attendue, ou pas d'autre choix
    return rng.choice(autres)
