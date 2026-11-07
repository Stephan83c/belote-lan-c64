"""Stratégie simple des bots (SPEC 4.4)."""

from __future__ import annotations

from .moteur import AS, couleur, coups_legaux, force, gagnant_pli, partenaire, points_carte, rang


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


def choisir_carte(main: list[int], pli: list[tuple[int, int]], atout: int, place: int) -> int:
    """Toujours un coup légal : faible si le partenaire est maître, gagnant sinon."""
    legaux = coups_legaux(main, pli, atout, place)

    def faiblesse(c: int) -> tuple[bool, int, int]:
        return (couleur(c) == atout, points_carte(c, atout), force(c, atout))

    if not pli:
        as_maitres = [c for c in legaux if rang(c) == AS and couleur(c) != atout]
        return as_maitres[0] if as_maitres else min(legaux, key=faiblesse)

    if gagnant_pli(pli, atout) != partenaire(place):
        gagnants = [c for c in legaux if gagnant_pli(pli + [(place, c)], atout) == place]
        if gagnants:
            return min(gagnants, key=faiblesse)
    return min(legaux, key=faiblesse)
