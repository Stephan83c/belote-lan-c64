"""Bots (4.4) : stratégie et légalité sur un grand nombre de donnes simulées."""

import random

import pytest

from belote.bots import choisir_carte, choisir_enchere
from belote.moteur import (
    AS,
    COEUR,
    DIX,
    HUIT,
    NEUF,
    PIQUE,
    ROI,
    SEPT,
    TREFLE,
    VALET,
    Donne,
    Phase,
    carte,
    coups_legaux,
    couleur,
    points_carte,
)


def test_enchere_tour_1_deux_atouts_potentiels():
    main = [carte(PIQUE, SEPT), carte(PIQUE, AS), carte(COEUR, AS)]
    assert choisir_enchere(main, 1, PIQUE) == PIQUE
    assert choisir_enchere(main, 1, COEUR) is None


def test_enchere_tour_2_jamais_la_couleur_retournee():
    main = [carte(PIQUE, SEPT), carte(PIQUE, AS), carte(PIQUE, ROI), carte(COEUR, AS), carte(COEUR, ROI)]
    assert choisir_enchere(main, 2, PIQUE) == COEUR


def test_enchere_tour_2_passe_sans_deux_cartes():
    main = [carte(PIQUE, SEPT), carte(PIQUE, AS), carte(COEUR, AS), carte(TREFLE, AS), carte(3, AS)]
    assert choisir_enchere(main, 2, PIQUE) is None


def test_carte_faible_si_partenaire_maitre():
    main = [carte(COEUR, DIX), carte(COEUR, SEPT)]
    pli = [(2, carte(COEUR, AS)), (3, carte(COEUR, HUIT))]
    assert choisir_carte(main, pli, PIQUE, 0) == carte(COEUR, SEPT)


def test_carte_gagnante_si_adversaire_maitre():
    main = [carte(COEUR, DIX), carte(COEUR, SEPT), carte(COEUR, AS)]
    pli = [(3, carte(COEUR, ROI))]
    assert choisir_carte(main, pli, PIQUE, 0) == carte(COEUR, DIX)


def test_carte_faible_si_impossible_de_gagner():
    main = [carte(COEUR, DIX), carte(COEUR, SEPT)]
    pli = [(3, carte(COEUR, AS))]
    assert choisir_carte(main, pli, PIQUE, 0) == carte(COEUR, SEPT)


def test_coupe_au_plus_petit_atout_gagnant():
    main = [carte(PIQUE, NEUF), carte(PIQUE, VALET), carte(PIQUE, SEPT)]
    pli = [(3, carte(COEUR, AS))]
    assert choisir_carte(main, pli, PIQUE, 0) == carte(PIQUE, SEPT)


@pytest.mark.parametrize("graine", range(300))
def test_donne_complete_entre_bots(graine):
    rng = random.Random(graine)
    d = Donne(graine % 4, rng)

    while d.phase is Phase.ENCHERES:
        p = d.joueur
        choix = choisir_enchere(d.mains[p], d.tour_encheres, couleur(d.retournee))
        if choix is None:
            d.passer(p)
        else:
            d.prendre(p, choix)
    if d.phase is Phase.ANNULEE:
        return

    assert d.nb_cartes() == [8, 8, 8, 8]
    assert sorted(sum(d.mains, [])) == list(range(32))

    while d.phase is Phase.JEU:
        p = d.joueur
        c = choisir_carte(d.mains[p], d.pli, d.atout, p)
        assert c in coups_legaux(d.mains[p], d.pli, d.atout, p)
        d.jouer(p, c)

    assert d.nb_cartes() == [0, 0, 0, 0]
    assert sum(d.plis_gagnes) == 8
    assert sum(d.points_cartes) == 162
    assert sum(points_carte(c, d.atout) for c in range(32)) == 152
    res = d.resultat()
    assert res.points[0] >= 0 and res.points[1] >= 0
