"""Comptage de la section 5.5 et fin de partie de la section 2.3."""

from belote.moteur import compter_manche, equipe_gagnante


def test_contrat_rempli_chaque_equipe_marque_ses_points():
    r = compter_manche(0, (90, 72), (5, 3))
    assert r.points == (90, 72)
    assert r.litige == 0 and r.capot is None


def test_contrat_a_82_sans_belote():
    assert compter_manche(0, (82, 80), (4, 4)).points == (82, 80)


def test_preneur_equipe_1():
    assert compter_manche(1, (72, 90), (3, 5)).points == (72, 90)


def test_contrat_compte_la_belote_du_preneur():
    # 72 + 20 = 92 contre 90 : rempli alors que le preneur a moins de cartes.
    assert compter_manche(0, (72, 90), (3, 5), equipe_belote=0).points == (92, 90)


def test_contrat_compte_la_belote_de_la_defense():
    # 90 contre 72 + 20 = 92 : dedans, à cause de la belote de la défense.
    assert compter_manche(0, (90, 72), (5, 3), equipe_belote=1).points == (0, 182)


def test_dedans_162_a_la_defense():
    assert compter_manche(0, (70, 92), (3, 5)).points == (0, 162)


def test_dedans_le_preneur_garde_sa_belote():
    # 40 + 20 = 60 contre 122.
    assert compter_manche(0, (40, 122), (2, 6), equipe_belote=0).points == (20, 162)


def test_litige_sans_belote_points_du_preneur_en_reserve():
    r = compter_manche(0, (81, 81), (4, 4))
    assert r.points == (0, 81)
    assert r.litige == 81
    assert r.reserve == 81


def test_litige_preneur_equipe_1():
    r = compter_manche(1, (81, 81), (4, 4))
    assert r.points == (81, 0)
    assert r.reserve == 81


def test_litige_avec_belote_du_preneur_la_belote_reste_acquise():
    # 71 + 20 = 91 contre 91 : seuls les 71 de cartes partent en réserve.
    r = compter_manche(0, (71, 91), (3, 5), equipe_belote=0)
    assert r.points == (20, 91)
    assert r.litige == 71


def test_litige_avec_belote_de_la_defense():
    # 91 contre 71 + 20 = 91.
    r = compter_manche(0, (91, 71), (5, 3), equipe_belote=1)
    assert r.points == (0, 91)
    assert r.litige == 91


def test_reserve_au_preneur_qui_reussit_la_manche_suivante():
    r = compter_manche(0, (90, 72), (5, 3), reserve=81)
    assert r.points == (171, 72)
    assert r.reserve == 0
    assert r.reserve_gagnee == (0, 81)


def test_reserve_a_la_defense_si_le_preneur_est_dedans():
    r = compter_manche(0, (70, 92), (3, 5), reserve=81)
    assert r.points == (0, 243)
    assert r.reserve_gagnee == (1, 81)


def test_nouveau_litige_cumule_la_reserve():
    r = compter_manche(1, (81, 81), (4, 4), reserve=81)
    assert r.points == (81, 0)
    assert r.reserve == 162
    assert r.reserve_gagnee is None


def test_capot_du_preneur_252():
    r = compter_manche(0, (162, 0), (8, 0))
    assert r.points == (252, 0)
    assert r.capot == 0


def test_capot_du_preneur_avec_sa_belote():
    assert compter_manche(0, (162, 0), (8, 0), equipe_belote=0).points == (272, 0)


def test_capot_du_preneur_la_defense_garde_sa_belote():
    assert compter_manche(0, (162, 0), (8, 0), equipe_belote=1).points == (252, 20)


def test_capot_de_la_defense_preneur_dedans():
    r = compter_manche(0, (0, 162), (0, 8))
    assert r.points == (0, 252)
    assert r.capot == 1


def test_capot_de_la_defense_le_preneur_garde_sa_belote():
    assert compter_manche(0, (0, 162), (0, 8), equipe_belote=0).points == (20, 252)


def test_capot_remporte_la_reserve():
    r = compter_manche(1, (0, 162), (0, 8), reserve=81)
    assert r.points == (0, 333)
    assert r.reserve == 0


def test_points_bruts_sans_arrondi():
    assert compter_manche(0, (97, 65), (5, 3)).points == (97, 65)


# ---- 2.3 Fin de partie --------------------------------------------------


def test_partie_continue_sous_la_cible():
    assert equipe_gagnante([999, 500], 1000) is None


def test_premiere_equipe_a_atteindre_la_cible_gagne():
    assert equipe_gagnante([1000, 500], 1000) == 0
    assert equipe_gagnante([500, 1040], 1000) == 1


def test_les_deux_a_la_cible_la_plus_haute_gagne():
    assert equipe_gagnante([1010, 1100], 1000) == 1


def test_egalite_parfaite_manche_supplementaire():
    assert equipe_gagnante([1100, 1100], 1000) is None
