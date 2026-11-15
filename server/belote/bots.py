"""Stratégie des bots (SPEC 4.4), réglée avec tools/duel_bots.py."""

from __future__ import annotations

from collections.abc import Iterable

from .moteur import (AS, DAME, DIX, HUIT, NEUF, ROI, SEPT, VALET, carte, couleur, coups_legaux,
                     force, gagnant_pli, partenaire, points_carte, rang)


# Valeur d'une carte pour juger une main aux enchères (proche de ses points à l'atout).
VALEUR_ATOUT = {VALET: 20, NEUF: 14, AS: 11, DIX: 10, ROI: 4, DAME: 3, HUIT: 2, SEPT: 2}
VALEUR_AS = 10           # as hors atout : un pli presque sûr
VALEUR_DIX_GARDE = 5     # dix hors atout avec son as
BONUS_BELOTE = 10        # roi et dame d'atout
SEUIL_PRISE = 35


def valeur_main(main: list[int], atout: int, retournee: int) -> int:
    """Force estimée d'une main si l'on prend à `atout` (la retournée est ramassée)."""
    cartes = main + [retournee]
    v = 0
    for c in cartes:
        if couleur(c) == atout:
            v += VALEUR_ATOUT[rang(c)]
        elif rang(c) == AS:
            v += VALEUR_AS
        elif rang(c) == DIX and carte(couleur(c), AS) in cartes:
            v += VALEUR_DIX_GARDE
    if carte(atout, ROI) in cartes and carte(atout, DAME) in cartes:
        v += BONUS_BELOTE
    return v


def choisir_enchere(main: list[int], tour_encheres: int, retournee: int) -> int | None:
    """Couleur prise si la main, retournée comprise, vaut au moins SEUIL_PRISE ; sinon None.

    Au premier tour, seule la couleur de la retournée ; au second, la meilleure des
    trois autres.
    """
    if tour_encheres == 1:
        candidates = [couleur(retournee)]
    else:
        candidates = [c for c in range(4) if c != couleur(retournee)]
    meilleure = max(candidates, key=lambda c: valeur_main(main, c, retournee))
    return meilleure if valeur_main(main, meilleure, retournee) >= SEUIL_PRISE else None


TIRER_ATOUTS = 1       # 0 : jamais ; 1 : le preneur ; 2 : le preneur et son partenaire
TIRER_PETIT = 3        # avec au moins N atouts sans le maître, entamer le plus petit (0 : non)
CHARGER_TROISIEME = 2  # 0 : jamais ; 1 : partenaire maître à l'atout ; 2 : aussi hors atout


def _maitre(pli: list[tuple[int, int]], atout: int, cachees: list[int]) -> bool:
    """La carte gagnante du pli ne peut plus être battue par une carte cachée.

    Hors atout, le dernier joueur pourrait couper s'il n'a plus la couleur :
    accepté en mode 2 seulement."""
    c = max((c for _, c in pli), key=lambda x: (couleur(x) == atout, couleur(x) == couleur(pli[0][1]),
                                                force(x, atout)))
    plus_fortes = [x for x in cachees if couleur(x) == couleur(c) and force(x, atout) > force(c, atout)]
    if plus_fortes:
        return False
    return couleur(c) == atout or CHARGER_TROISIEME == 2


def choisir_carte(main: list[int], pli: list[tuple[int, int]], atout: int, place: int,
                  jouees: Iterable[int] = (), preneur: int | None = None) -> int:
    """Toujours un coup légal : le preneur tire les atouts ; on charge le partenaire
    maître (dernier à jouer, ou sa carte imbattable), on gagne au plus juste contre
    l'adversaire, sinon la carte la plus faible.

    jouees : cartes déjà posées dans la donne (pli en cours compris ou non). Le bot
    s'en souvient pour entamer la plus forte carte restante d'une couleur.
    preneur : place du preneur (None : inconnu, comme avant la v2.0).

    Essayé puis écarté (simulation de 20 000 donnes contre l'ancienne stratégie) :
    gagner un pli avec une carte que personne ne peut battre (atout maître) plutôt
    qu'avec la plus petite carte gagnante. Le bot brûle trop tôt ses valet et 9
    d'atout : -6,8 % de points (-0,6 % en le limitant aux plis de 10 points et plus)."""
    legaux = coups_legaux(main, pli, atout, place)
    vues = set(main) | set(jouees) | {c for _, c in pli}
    cachees = [c for c in range(32) if c not in vues]

    def faiblesse(c: int) -> tuple[bool, int, int]:
        return (couleur(c) == atout, points_carte(c, atout), force(c, atout))

    def plus_forte_de_sa_couleur(c: int) -> bool:
        return all(force(x, atout) < force(c, atout) for x in cachees if couleur(x) == couleur(c))

    if not pli and TIRER_ATOUTS and preneur in (place, partenaire(place) if TIRER_ATOUTS == 2 else place):
        # Le preneur fait tomber les atouts adverses avec son atout maître, tant
        # qu'il en reste dehors.
        atouts = [c for c in legaux if couleur(c) == atout]
        dehors = [c for c in cachees if couleur(c) == atout]
        if atouts and dehors:
            meilleur = max(atouts, key=lambda c: force(c, atout))
            if all(force(x, atout) < force(meilleur, atout) for x in dehors):
                return meilleur
            if TIRER_PETIT and len(atouts) >= TIRER_PETIT:
                return min(atouts, key=lambda c: force(c, atout))

    if not pli:
        # Entame : la plus forte carte restante d'une couleur hors atout (l'as, ou le
        # 10 quand l'as est tombé...). Un adversaire peut couper : le risque est accepté.
        sures = [c for c in legaux if couleur(c) != atout and plus_forte_de_sa_couleur(c)]
        return max(sures, key=lambda c: points_carte(c, atout)) if sures else min(legaux, key=faiblesse)

    if gagnant_pli(pli, atout) != partenaire(place):
        gagnants = [c for c in legaux if gagnant_pli(pli + [(place, c)], atout) == place]
        if gagnants:
            return min(gagnants, key=faiblesse)
    elif len(pli) == 3 or (CHARGER_TROISIEME and len(pli) == 2 and _maitre(pli, atout, cachees)):
        # Le pli est au partenaire (dernier à jouer, ou sa carte imbattable) : on le
        # charge (10, as) sans sacrifier d'atout.
        hors_atout = [c for c in legaux if couleur(c) != atout]
        if hors_atout:
            return max(hors_atout, key=lambda c: (points_carte(c, atout), -force(c, atout)))
    return min(legaux, key=faiblesse)
