"""Bots à style (styles.py) : noms, tirage à la table, mode selon le score, PIMC à objectif."""

import random

from belote import pimc
from belote.bots import choisir_enchere
from belote.moteur import CARREAU, COEUR, PIQUE, TREFLE, AS, DIX, SEPT, VALET, NEUF, carte
from belote.styles import NUMEROS, mode, nom_bot
from belote.table import NOM_RESERVE, Table
from test_table import FauxClient, dans_boucle, rejoindre


def P(r):
    return carte(PIQUE, r)


def H(r):
    return carte(COEUR, r)


def T(r):
    return carte(TREFLE, r)


def K(r):
    return carte(CARREAU, r)


def noms_bots(t):
    return [s.nom for s in t.sieges if s.humain is None]


def test_quinze_noms_courts_et_reserves():
    noms = [nom_bot(n) for n in NUMEROS]
    assert len(set(noms)) == 15
    assert noms[:3] == ["BOT1", "BOT12", "BOT13"] and "BOT5" in noms and "BOT53" in noms
    assert all(NOM_RESERVE.fullmatch(n) and len(n) <= 6 for n in noms)


@dans_boucle
def test_bots_de_la_table_ont_des_noms_differents():
    for graine in range(50):
        t = Table(rng=random.Random(graine), delai_bot=3600)
        noms = noms_bots(t)
        assert len(set(noms)) == 4 and "BOT" not in noms


@dans_boucle
def test_un_humain_prend_la_place_d_un_bot():
    t = Table(rng=random.Random(1), delai_bot=3600)
    a = rejoindre(t, "A")
    assert t.sieges[0].nom == "A" and t.sieges[0].numero is None
    assert f"SIEGE 1 B {t.sieges[1].nom}" in a.lignes and t.sieges[1].nom != "BOT"


@dans_boucle
def test_nouvelle_partie_retire_les_styles_et_les_annonce():
    t = Table(rng=random.Random(1), delai_bot=3600)
    a = rejoindre(t, "A")
    a.vider()
    t.recevoir(a, "LANCER")
    sieges = [l for l in a.lignes if l.startswith("SIEGE")]
    assert [l.split()[1] for l in sieges] == ["1", "2", "3"]
    assert a.lignes.index(sieges[-1]) < a.lignes.index("ETAT LANCEE")
    assert len(set(noms_bots(t))) == 3


@dans_boucle
def test_bot_qui_remplace_un_humain_prend_un_nom_libre():
    t = Table(rng=random.Random(2), delai_bot=3600)
    a, b = rejoindre(t, "A"), rejoindre(t, "B")
    t.recevoir(a, "LANCER")
    a.vider()
    t.deconnexion(b)
    nom = t.sieges[1].nom
    assert t.sieges[1].numero is not None and NOM_RESERVE.fullmatch(nom) and nom != "BOT"
    assert f"SIEGE 1 B {nom}" in a.lignes
    assert len(set(noms_bots(t))) == 3


@dans_boucle
def test_sans_styles_tous_les_bots_s_appellent_bot():
    t = Table(rng=random.Random(1), delai_bot=3600, styles=False)
    assert noms_bots(t) == ["BOT"] * 4
    assert t._mode_bot(1) == ("ecart", 32, 0.0)


def test_mode_selon_le_style_la_variante_et_le_score():
    assert mode(11, 0, 0, 1000) == ("attaque", 24, 0.0)       # attaquant, variante 1 : -2
    assert mode(23, 0, 0, 1000) == ("defense", 36, 0.0)       # défenseur, variante 3 : +2
    assert mode(52, 0, 0, 1000) == ("ecart", 32, 3.0)         # feinteur
    assert mode(42, 300, 100, 1000) == ("defense", 38, 0.0)   # adaptatif en tête
    assert mode(42, 100, 300, 1000) == ("attaque", 26, 0.0)   # adaptatif mené
    assert mode(42, 600, 850, 1000) == ("attaque", 26, 0.0)   # adversaire près de la cible
    assert mode(42, 500, 520, 1000) == ("ecart", 32, 0.0)


def test_seuil_de_prise_du_style():
    main = [P(VALET), P(NEUF), P(AS), H(SEPT), K(SEPT)]
    retournee = P(DIX)
    assert choisir_enchere(main, 1, retournee, seuil=10) == PIQUE
    assert choisir_enchere(main, 1, retournee, seuil=200) is None


def test_pimc_a_objectif_joue_un_coup_legal():
    main = [P(SEPT), T(AS), K(SEPT), H(DIX)]
    pli = [(3, T(DIX))]
    for objectif in ("attaque", "defense", "ecart"):
        c = pimc.choisir(main, pli, [], [T(DIX)], PIQUE, 0, 1, P(NEUF), [0, 0], [0, 0],
                         tirages=10, rng=random.Random(4), objectif=objectif, tolerance=3.0)
        assert c == T(AS)                                     # fournir la couleur demandée


def test_feinteur_ne_trompe_pas_son_partenaire_maitre():
    main = [T(SEPT), K(SEPT), H(DIX), H(SEPT)]
    pli = [(1, P(SEPT)), (2, P(AS)), (3, P(DIX))]             # partenaire (2) maître
    sans = pimc.choisir(main, pli, [], [c for _, c in pli], COEUR, 0, 1, H(NEUF), [0, 0], [0, 0],
                        tirages=20, rng=random.Random(5))
    avec = pimc.choisir(main, pli, [], [c for _, c in pli], COEUR, 0, 1, H(NEUF), [0, 0], [0, 0],
                        tirages=20, rng=random.Random(5), tolerance=1000.0)
    assert avec == sans


@dans_boucle
def test_raz_retire_les_styles_des_bots():
    t = Table(rng=random.Random(3), delai_bot=3600)
    a = rejoindre(t, "A")
    t.recevoir(a, "LANCER")
    a.vider()
    assert t.raz()
    sieges = [l for l in a.lignes if l.startswith("SIEGE")]
    assert [l.split()[1] for l in sieges] == ["1", "2", "3"]
    assert a.lignes.index(sieges[-1]) < a.lignes.index("ETAT ATTENTE")
    assert len(set(noms_bots(t))) == 3
