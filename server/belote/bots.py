"""Stratégie simple des bots (SPEC 4.4)."""

from __future__ import annotations

from collections.abc import Iterable

from .moteur import couleur, coups_legaux, force, gagnant_pli, partenaire, points_carte


def choisir_enchere(main: list[int], tour_encheres: int, couleur_retournee: int) -> int | None:
    """Couleur prise si la main contient au moins deux atouts potentiels, sinon None."""
    def nb(c: int) -> int:
        return sum(1 for x in main if couleur(x) == c)

    if tour_encheres == 1:
        return couleur_retournee if nb(couleur_retournee) >= 2 else None

    def poids(c: int) -> tuple[int, int]:
        return (nb(c), sum(points_carte(x, c) for x in main if couleur(x) == c))

    meilleure = max((c for c in range(4) if c != couleur_retournee), key=poids)
    return meilleure if nb(meilleure) >= 2 else None


def choisir_carte(main: list[int], pli: list[tuple[int, int]], atout: int, place: int,
                  jouees: Iterable[int] = ()) -> int:
    """Toujours un coup légal : faible si le partenaire est maître, gagnant sinon.

    jouees : cartes déjà posées dans la donne (pli en cours compris ou non). Le bot
    s'en souvient pour entamer la plus forte carte restante d'une couleur.

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

    if not pli:
        # Entame : la plus forte carte restante d'une couleur hors atout (l'as, ou le
        # 10 quand l'as est tombé...). Un adversaire peut couper : le risque est accepté.
        sures = [c for c in legaux if couleur(c) != atout and plus_forte_de_sa_couleur(c)]
        return max(sures, key=lambda c: points_carte(c, atout)) if sures else min(legaux, key=faiblesse)

    if gagnant_pli(pli, atout) != partenaire(place):
        gagnants = [c for c in legaux if gagnant_pli(pli + [(place, c)], atout) == place]
        if gagnants:
            return min(gagnants, key=faiblesse)
    return min(legaux, key=faiblesse)
