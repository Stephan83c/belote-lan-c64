"""Règles de la section 5 : donne, enchères, légalité, belote."""

import random

import pytest

from belote.moteur import (
    AS,
    CARREAU,
    COEUR,
    DAME,
    DIX,
    HUIT,
    NEUF,
    PIQUE,
    ROI,
    SEPT,
    TREFLE,
    VALET,
    CoupRefuse,
    Donne,
    PasTonTour,
    Phase,
    carte,
    coups_legaux,
    couleur,
    force,
    gagnant_pli,
    points_carte,
)


def P(r):
    return carte(PIQUE, r)


def H(r):
    return carte(COEUR, r)


def T(r):
    return carte(TREFLE, r)


def K(r):
    return carte(CARREAU, r)


def paquet_pour(donneur, mains, retournee, preneur):
    """Paquet produisant exactement `mains` (8 cartes par place, retournée comprise)."""
    restes = [list(m) for m in mains]
    restes[preneur].remove(retournee)
    premier = (donneur + 1) % 4
    ordre = [(premier + i) % 4 for i in range(4)]
    paquet = []
    for nb in (3, 2):
        for p in ordre:
            paquet += restes[p][:nb]
            del restes[p][:nb]
    paquet.append(retournee)
    for p in ordre:
        paquet += restes[p]
    return paquet


# ---- 5.1 Paquet, ordre, points ------------------------------------------


def test_codes_des_cartes():
    assert carte(PIQUE, SEPT) == 0
    assert carte(COEUR, AS) == 15
    assert carte(CARREAU, AS) == 31
    assert couleur(14) == COEUR


def test_ordre_sans_atout():
    ordre = [SEPT, HUIT, NEUF, VALET, DAME, ROI, DIX, AS]
    forces = [force(T(r), PIQUE) for r in ordre]
    assert forces == sorted(forces) and len(set(forces)) == 8


def test_ordre_atout():
    ordre = [SEPT, HUIT, DAME, ROI, DIX, AS, NEUF, VALET]
    forces = [force(P(r), PIQUE) for r in ordre]
    assert forces == sorted(forces) and len(set(forces)) == 8


@pytest.mark.parametrize(
    "r,normal,atout",
    [(SEPT, 0, 0), (HUIT, 0, 0), (NEUF, 0, 14), (DIX, 10, 10), (VALET, 2, 20), (DAME, 3, 3), (ROI, 4, 4), (AS, 11, 11)],
)
def test_points_par_rang(r, normal, atout):
    assert points_carte(T(r), PIQUE) == normal
    assert points_carte(P(r), PIQUE) == atout


def test_total_des_cartes_152():
    assert sum(points_carte(c, PIQUE) for c in range(32)) == 152


# ---- 5.2 Donne et enchères ----------------------------------------------


def test_premiere_distribution_cinq_cartes_et_retournee():
    d = Donne(0, random.Random(1))
    assert d.nb_cartes() == [5, 5, 5, 5]
    toutes = sum(d.mains, []) + [d.retournee]
    assert len(set(toutes)) == 21


def test_distribution_3_puis_2_depuis_la_droite_du_donneur():
    paquet = list(range(32))
    d = Donne(0, paquet=paquet)
    # Droite du donneur P0 = P1 : 3 premières cartes, puis 2 au second passage.
    assert d.mains[1] == [0, 1, 2, 12, 13]
    assert d.mains[2] == [3, 4, 5, 14, 15]
    assert d.mains[3] == [6, 7, 8, 16, 17]
    assert d.mains[0] == [9, 10, 11, 18, 19]
    assert d.retournee == 20


def test_le_preneur_recoit_retournee_plus_deux_les_autres_trois():
    d = Donne(0, paquet=list(range(32)))
    d.prendre(1, couleur(20))
    assert d.nb_cartes() == [8, 8, 8, 8]
    assert 20 in d.mains[1]
    assert sorted(sum(d.mains, [])) == list(range(32))


def test_les_encheres_commencent_a_droite_du_donneur():
    d = Donne(2, random.Random(1))
    assert d.joueur == 3
    with pytest.raises(PasTonTour):
        d.passer(0)


def test_tour_1_seule_la_couleur_retournee():
    d = Donne(0, random.Random(1))
    autre = (couleur(d.retournee) + 1) % 4
    with pytest.raises(CoupRefuse):
        d.prendre(1, autre)
    assert d.phase is Phase.ENCHERES
    d.prendre(1, couleur(d.retournee))
    assert d.atout == couleur(d.retournee)
    assert d.preneur == 1


def test_tour_2_couleur_retournee_interdite():
    d = Donne(0, random.Random(1))
    for p in (1, 2, 3, 0):
        d.passer(p)
    assert d.tour_encheres == 2
    assert d.joueur == 1
    with pytest.raises(CoupRefuse):
        d.prendre(1, couleur(d.retournee))
    autre = (couleur(d.retournee) + 1) % 4
    d.prendre(1, autre)
    assert d.atout == autre


def test_couleur_inexistante_refusee():
    d = Donne(0, random.Random(1))
    with pytest.raises(CoupRefuse):
        d.prendre(1, 4)


def test_les_encheres_s_arretent_des_qu_un_joueur_prend():
    d = Donne(0, random.Random(1))
    d.passer(1)
    evts = d.prendre(2, couleur(d.retournee))
    assert d.phase is Phase.JEU
    assert evts[0] == ("PREND", 2, couleur(d.retournee))
    with pytest.raises(CoupRefuse):
        d.passer(1)  # c'est à P1 d'entamer, mais plus d'enchères


def test_premier_tour_passe_annonce_le_second():
    d = Donne(0, random.Random(1))
    for p in (1, 2, 3):
        assert d.passer(p) == [("PASSE", p), ("TOUR", (p + 1) % 4)]
    assert d.passer(0) == [("PASSE", 0), ("ENCHERES", 2), ("TOUR", 1)]


def test_tous_passent_deux_tours_donne_annulee():
    d = Donne(0, random.Random(1))
    for p in (1, 2, 3, 0, 1, 2, 3):
        d.passer(p)
    assert d.passer(0) == [("PASSE", 0), ("REDONNE",)]
    assert d.phase is Phase.ANNULEE


def test_l_entame_revient_a_droite_du_donneur_meme_si_un_autre_prend():
    d = Donne(0, random.Random(1))
    d.passer(1)
    d.passer(2)
    d.prendre(3, couleur(d.retournee))
    assert d.joueur == 1


# ---- 5.3 Gagnant du pli -------------------------------------------------


def test_pli_sans_atout_la_plus_forte_de_la_couleur_demandee():
    pli = [(0, H(ROI)), (1, H(DIX)), (2, T(AS)), (3, H(SEPT))]
    assert gagnant_pli(pli, PIQUE) == 1


def test_pli_le_plus_fort_atout_gagne():
    pli = [(0, H(AS)), (1, P(SEPT)), (2, P(NEUF)), (3, H(DIX))]
    assert gagnant_pli(pli, PIQUE) == 2


def test_pli_le_valet_d_atout_bat_tout():
    pli = [(0, P(AS)), (1, P(NEUF)), (2, P(VALET)), (3, P(DIX))]
    assert gagnant_pli(pli, PIQUE) == 2


# ---- 5.3 Légalité (atout = pique sauf mention) --------------------------


def test_entame_libre():
    main = [P(SEPT), H(AS), T(DIX)]
    assert coups_legaux(main, [], PIQUE, 0) == main


def test_couleur_demandee_fournir_n_importe_quelle_carte():
    main = [H(SEPT), H(AS), T(DIX), P(VALET)]
    pli = [(3, H(ROI))]
    assert sorted(coups_legaux(main, pli, PIQUE, 0)) == sorted([H(SEPT), H(AS)])


def test_atout_demande_monter_obligatoire():
    main = [P(SEPT), P(NEUF), P(AS), H(AS)]
    pli = [(3, P(DIX))]
    assert sorted(coups_legaux(main, pli, PIQUE, 0)) == sorted([P(NEUF), P(AS)])


def test_atout_demande_monter_meme_si_partenaire_maitre():
    main = [P(SEPT), P(VALET)]
    pli = [(2, P(NEUF)), (3, P(HUIT))]  # partenaire P2 maître, P0 doit tout de même monter
    assert coups_legaux(main, pli, PIQUE, 0) == [P(VALET)]
    main = [P(SEPT), P(AS)]
    pli = [(2, P(DIX)), (3, P(HUIT))]
    assert coups_legaux(main, pli, PIQUE, 0) == [P(AS)]


def test_atout_demande_sans_atout_superieur_atout_inferieur():
    main = [P(SEPT), P(HUIT), H(AS)]
    pli = [(3, P(VALET))]
    assert sorted(coups_legaux(main, pli, PIQUE, 0)) == sorted([P(SEPT), P(HUIT)])


def test_atout_demande_sans_atout_defausse_libre():
    main = [H(AS), T(SEPT)]
    pli = [(3, P(VALET))]
    assert coups_legaux(main, pli, PIQUE, 0) == main


def test_couleur_absente_partenaire_maitre_libre():
    main = [P(SEPT), T(SEPT), K(AS)]
    pli = [(2, H(AS)), (3, H(SEPT))]
    assert coups_legaux(main, pli, PIQUE, 0) == main


def test_couleur_absente_partenaire_maitre_par_coupe_reste_libre():
    # Le partenaire a coupé : décision « libre si partenaire maître », y compris
    # un atout inférieur (section 11).
    main = [P(SEPT), T(SEPT)]
    pli = [(1, H(AS)), (2, P(AS)), (3, H(SEPT))]
    assert coups_legaux(main, pli, PIQUE, 0) == main


def test_couleur_absente_adversaire_maitre_couper_obligatoire():
    main = [P(SEPT), P(AS), T(AS)]
    pli = [(3, H(AS))]
    assert sorted(coups_legaux(main, pli, PIQUE, 0)) == sorted([P(SEPT), P(AS)])


def test_adversaire_a_coupe_surcouper_obligatoire():
    main = [P(SEPT), P(NEUF), T(AS)]
    pli = [(1, H(AS)), (2, H(SEPT)), (3, P(AS))]
    assert coups_legaux(main, pli, PIQUE, 0) == [P(NEUF)]


def test_partenaire_coupe_puis_adversaire_surcoupe_il_faut_surcouper():
    main = [P(SEPT), P(VALET), T(AS)]
    pli = [(1, H(AS)), (2, P(DIX)), (3, P(AS))]
    assert coups_legaux(main, pli, PIQUE, 0) == [P(VALET)]


def test_sous_coupe_interdite_defausser_autre_couleur():
    main = [P(SEPT), T(AS), K(SEPT)]
    pli = [(1, H(AS)), (2, H(SEPT)), (3, P(VALET))]
    assert sorted(coups_legaux(main, pli, PIQUE, 0)) == sorted([T(AS), K(SEPT)])


def test_sous_coupe_permise_s_il_ne_reste_que_de_l_atout():
    main = [P(SEPT), P(HUIT)]
    pli = [(1, H(AS)), (2, H(SEPT)), (3, P(VALET))]
    assert sorted(coups_legaux(main, pli, PIQUE, 0)) == sorted(main)


def test_ni_couleur_ni_atout_defausse_libre():
    main = [T(AS), K(SEPT)]
    pli = [(3, H(AS))]
    assert coups_legaux(main, pli, PIQUE, 0) == main


def test_refus_carte_absente_et_tour():
    d = Donne(0, paquet=list(range(32)))
    d.prendre(1, couleur(d.retournee))
    assert d.joueur == 1
    absente = next(c for c in range(32) if c not in d.mains[1])
    with pytest.raises(CoupRefuse):
        d.jouer(1, absente)
    with pytest.raises(PasTonTour):
        d.jouer(2, d.mains[2][0])


def test_refus_coup_illegal_laisse_l_etat_inchange():
    d = donne_capot()
    d.jouer(0, P(AS))
    d.jouer(1, H(AS))
    d.jouer(2, T(AS))
    d.jouer(3, K(AS))
    d.jouer(0, P(ROI))
    # P0 a tout l'atout : tout est libre pour P1, mais une carte déjà jouée est refusée.
    main, pli = list(d.mains[1]), list(d.pli)
    with pytest.raises(CoupRefuse):
        d.jouer(1, H(AS))
    assert (d.joueur, d.mains[1], d.pli) == (1, main, pli)


def test_refus_de_ne_pas_fournir():
    mains = [
        [P(r) for r in (SEPT, HUIT, NEUF, DIX, VALET, DAME, ROI)] + [H(SEPT)],
        [H(r) for r in (HUIT, NEUF, DIX, VALET, DAME, ROI, AS)] + [P(AS)],
        [T(r) for r in (SEPT, HUIT, NEUF, DIX, VALET, DAME, ROI, AS)],
        [K(r) for r in (SEPT, HUIT, NEUF, DIX, VALET, DAME, ROI, AS)],
    ]
    d = Donne(3, paquet=paquet_pour(3, mains, P(DIX), 0))
    d.prendre(0, PIQUE)
    d.jouer(0, H(SEPT))
    atout_interdit = P(AS)  # P1 a du cœur : il ne peut pas couper
    with pytest.raises(CoupRefuse):
        d.jouer(1, atout_interdit)
    assert d.joueur == 1 and len(d.pli) == 1


# ---- 5.4 Belote-rebelote et déroulé complet -----------------------------


def donne_capot():
    mains = [
        [P(r) for r in (SEPT, HUIT, NEUF, DIX, VALET, DAME, ROI, AS)],
        [H(r) for r in (SEPT, HUIT, NEUF, DIX, VALET, DAME, ROI, AS)],
        [T(r) for r in (SEPT, HUIT, NEUF, DIX, VALET, DAME, ROI, AS)],
        [K(r) for r in (SEPT, HUIT, NEUF, DIX, VALET, DAME, ROI, AS)],
    ]
    d = Donne(3, paquet=paquet_pour(3, mains, P(AS), 0))
    d.prendre(0, PIQUE)
    return d


def test_belote_rebelote_annoncees_automatiquement():
    d = donne_capot()
    assert d.place_belote == 0
    annonces = []
    for i in range(8):
        c = [P(DAME), P(ROI), P(SEPT), P(HUIT), P(NEUF), P(DIX), P(VALET), P(AS)][i]
        for evt in d.jouer(0, c):
            if evt[0] in ("BELOTE", "REBELOTE"):
                annonces.append(evt)
        for p in (1, 2, 3):
            d.jouer(p, d.mains[p][0])
    assert annonces == [("BELOTE", 0), ("REBELOTE", 0)]


def test_belote_annoncee_a_la_premiere_carte_quelle_qu_elle_soit():
    d = donne_capot()
    evts = d.jouer(0, P(ROI))
    assert ("BELOTE", 0) in evts


def test_pas_de_belote_si_roi_et_dame_separes():
    mains = [
        [P(r) for r in (SEPT, HUIT, NEUF, DIX, VALET, DAME, AS)] + [H(SEPT)],
        [H(r) for r in (HUIT, NEUF, DIX, VALET, DAME, ROI, AS)] + [P(ROI)],
        [T(r) for r in (SEPT, HUIT, NEUF, DIX, VALET, DAME, ROI, AS)],
        [K(r) for r in (SEPT, HUIT, NEUF, DIX, VALET, DAME, ROI, AS)],
    ]
    d = Donne(3, paquet=paquet_pour(3, mains, P(AS), 0))
    d.prendre(0, PIQUE)
    assert d.place_belote is None
    evts = d.jouer(0, P(DAME))
    assert not any(e[0] == "BELOTE" for e in evts)


def test_belote_du_defenseur_detectee():
    mains = [
        [P(r) for r in (SEPT, HUIT, NEUF, DIX, VALET, AS)] + [H(SEPT), H(HUIT)],
        [P(DAME), P(ROI)] + [H(r) for r in (NEUF, DIX, VALET, DAME, ROI, AS)],
        [T(r) for r in (SEPT, HUIT, NEUF, DIX, VALET, DAME, ROI, AS)],
        [K(r) for r in (SEPT, HUIT, NEUF, DIX, VALET, DAME, ROI, AS)],
    ]
    d = Donne(3, paquet=paquet_pour(3, mains, P(AS), 0))
    d.prendre(0, PIQUE)
    assert d.place_belote == 1


def test_capot_du_preneur_de_bout_en_bout():
    d = donne_capot()
    evenements = []
    for _ in range(8):
        evenements += d.jouer(0, d.mains[0][-1])
        for p in (1, 2, 3):
            evenements += d.jouer(p, d.mains[p][0])
    assert d.phase is Phase.FINIE
    assert evenements[-1] == ("FIN",)
    assert d.plis_gagnes == [8, 0]
    assert d.points_cartes == [162, 0]
    res = d.resultat()
    assert res.capot == 0
    assert res.points == (272, 0)


def test_le_gagnant_du_pli_entame_le_suivant():
    d = donne_capot()
    d.jouer(0, P(AS))
    d.jouer(1, H(AS))
    d.jouer(2, T(AS))
    evts = d.jouer(3, K(AS))
    assert evts[-2:] == [("PLI", 0), ("TOUR", 0)]
    assert d.pli == []
