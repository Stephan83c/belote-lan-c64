"""Bots (4.4) : stratégie et légalité sur un grand nombre de donnes simulées."""

import random

import pytest

from belote.bots import choisir_carte, choisir_enchere
from belote.moteur import (
    AS,
    CARREAU,
    DAME,
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


def test_enchere_prend_avec_valet_et_neuf():
    main = [carte(PIQUE, VALET), carte(PIQUE, NEUF), carte(COEUR, SEPT), carte(TREFLE, HUIT), carte(CARREAU, SEPT)]
    assert choisir_enchere(main, 1, carte(PIQUE, SEPT)) == PIQUE


def test_enchere_passe_avec_deux_petits_atouts():
    # Les anciens bots prenaient dès deux cartes de la couleur, même le 7 et le 8.
    main = [carte(PIQUE, SEPT), carte(PIQUE, HUIT), carte(COEUR, SEPT), carte(TREFLE, HUIT), carte(CARREAU, DAME)]
    assert choisir_enchere(main, 1, carte(PIQUE, DAME)) is None


def test_enchere_compte_le_valet_retourne():
    main = [carte(COEUR, NEUF), carte(COEUR, SEPT), carte(PIQUE, SEPT), carte(TREFLE, HUIT), carte(CARREAU, DAME)]
    assert choisir_enchere(main, 1, carte(COEUR, VALET)) == COEUR
    assert choisir_enchere(main, 1, carte(COEUR, HUIT)) is None


def test_enchere_tour_2_jamais_la_couleur_retournee():
    main = [carte(PIQUE, VALET), carte(PIQUE, NEUF), carte(PIQUE, AS), carte(COEUR, VALET), carte(COEUR, NEUF)]
    assert choisir_enchere(main, 2, carte(PIQUE, SEPT)) == COEUR


def test_enchere_tour_2_passe_avec_une_main_faible():
    main = [carte(PIQUE, SEPT), carte(COEUR, HUIT), carte(TREFLE, DAME), carte(CARREAU, SEPT), carte(CARREAU, HUIT)]
    assert choisir_enchere(main, 2, carte(PIQUE, ROI)) is None


def test_charge_le_partenaire_en_dernier():
    # Partenaire (2) maître ; dernier à jouer, sans la couleur : on lui donne l'as.
    pli = [(1, carte(TREFLE, SEPT)), (2, carte(TREFLE, AS)), (3, carte(TREFLE, HUIT))]
    main = [carte(COEUR, AS), carte(COEUR, SEPT), carte(CARREAU, ROI)]
    assert choisir_carte(main, pli, PIQUE, 0) == carte(COEUR, AS)


def test_preneur_tire_son_atout_maitre():
    main = [carte(PIQUE, VALET), carte(PIQUE, SEPT), carte(COEUR, AS)]
    assert choisir_carte(main, [], PIQUE, 0, (), preneur=0) == carte(PIQUE, VALET)
    # Pas preneur : il entame son as, comme avant.
    assert choisir_carte(main, [], PIQUE, 0, (), preneur=1) == carte(COEUR, AS)


def test_carte_faible_si_partenaire_maitre_mais_battable():
    # Le partenaire gagne avec le roi, mais l'as est encore dehors : petite carte.
    main = [carte(COEUR, DIX), carte(COEUR, SEPT)]
    pli = [(2, carte(COEUR, ROI)), (3, carte(COEUR, HUIT))]
    assert choisir_carte(main, pli, PIQUE, 0) == carte(COEUR, SEPT)


def test_charge_le_partenaire_imbattable_en_troisieme():
    # Le partenaire a l'as : on lui donne le dix.
    main = [carte(COEUR, DIX), carte(COEUR, SEPT)]
    pli = [(2, carte(COEUR, AS)), (3, carte(COEUR, HUIT))]
    assert choisir_carte(main, pli, PIQUE, 0) == carte(COEUR, DIX)


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


def test_entame_un_dix_devenu_maitre():
    main = [carte(TREFLE, DIX), carte(TREFLE, SEPT), carte(CARREAU, HUIT)]
    jouees = [carte(TREFLE, AS)]
    assert choisir_carte(main, [], PIQUE, 0, jouees) == carte(TREFLE, DIX)
    # Tant que l'as n'est pas tombé, le 10 n'est pas entamé.
    assert choisir_carte(main, [], PIQUE, 0) != carte(TREFLE, DIX)


def test_entame_la_carte_maitresse_qui_rapporte_le_plus():
    main = [carte(TREFLE, AS), carte(CARREAU, DIX), carte(COEUR, ROI)]
    jouees = [carte(CARREAU, AS)]
    # As de trèfle (11) plutôt que 10 de carreau (10), tous deux maîtres.
    assert choisir_carte(main, [], PIQUE, 0, jouees) == carte(TREFLE, AS)


@pytest.mark.parametrize("graine", range(300))
def test_donne_complete_entre_bots(graine):
    rng = random.Random(graine)
    d = Donne(graine % 4, rng)

    while d.phase is Phase.ENCHERES:
        p = d.joueur
        choix = choisir_enchere(d.mains[p], d.tour_encheres, d.retournee)
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
        c = choisir_carte(d.mains[p], d.pli, d.atout, p, d.jouees, d.preneur)
        assert c in coups_legaux(d.mains[p], d.pli, d.atout, p)
        d.jouer(p, c)

    assert d.nb_cartes() == [0, 0, 0, 0]
    assert sum(d.plis_gagnes) == 8
    assert sum(d.points_cartes) == 162
    assert sum(points_carte(c, d.atout) for c in range(32)) == 152
    res = d.resultat()
    assert res.points[0] >= 0 and res.points[1] >= 0
