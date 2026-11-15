"""Salons : plusieurs tables sur un même serveur (SPEC 4.5)."""

import random

from belote.__main__ import commande_console
from belote.salons import Salons
from belote.table import ATTENTE, EN_COURS, Table

from test_table import FauxClient, dans_boucle


def salons(n=3):
    return Salons([Table(rng=random.Random(i), delai_bot=3600) for i in range(n)])


def entrer(s, ligne, adresse=None):
    c = FauxClient()
    c.adresse = adresse
    s.recevoir(c, ligne)
    return c


@dans_boucle
def test_liste_des_salons():
    s = salons()
    entrer(s, "JOIN A 2")
    c = entrer(s, "SALONS")
    assert c.lignes == ["SALONS 3", "SALON 1 0 ATTENTE", "SALON 2 1 ATTENTE", "SALON 3 0 ATTENTE"]
    assert not c.ferme


@dans_boucle
def test_join_sans_numero_va_au_salon_1():
    # Les clients d'avant le multi-salon envoient JOIN NOM seul.
    s = salons()
    a = entrer(s, "JOIN A")
    assert a.lignes[0] == "BIENVENUE A 0"
    assert s.tables[0].est_assis(a) and s.est_assis(a)


@dans_boucle
def test_salons_separes():
    s = salons()
    a = entrer(s, "JOIN A 1")
    b = entrer(s, "JOIN B 2")
    assert b.lignes[0] == "BIENVENUE B 0"  # premier de son salon : place 0, chef
    a.lignes.clear()
    s.recevoir(b, "TCHAT SALUT")
    assert "TCHAT B SALUT" in b.lignes and not any("SALUT" in l for l in a.lignes)
    s.recevoir(b, "LANCER")
    assert s.tables[1].etat == EN_COURS and s.tables[0].etat == ATTENTE
    # Même nom dans deux salons : chacun le sien.
    c = entrer(s, "JOIN A 2")
    assert c.lignes[0].startswith("BIENVENUE A")


@dans_boucle
def test_salon_plein_garde_la_connexion():
    s = salons()
    for nom in "ABCD":
        entrer(s, f"JOIN {nom} 3")
    e = entrer(s, "JOIN E 3")
    assert e.lignes == ["ERR TABLE PLEINE"] and not e.ferme
    s.recevoir(e, "JOIN E 2")  # un autre salon : accepté
    assert e.lignes[-1] != "ERR TABLE PLEINE" and s.tables[1].est_assis(e)


@dans_boucle
def test_salon_plein_sans_numero_ferme_comme_avant():
    s = salons(1)
    for nom in "ABCD":
        entrer(s, f"JOIN {nom}")
    e = entrer(s, "JOIN E")
    assert e.lignes == ["ERR TABLE PLEINE"] and e.ferme


@dans_boucle
def test_numero_de_salon_invalide():
    s = salons()
    for ligne in ("JOIN A 0", "JOIN A 4", "JOIN A X", "JOIN A 99999999"):
        c = entrer(s, ligne)
        assert c.lignes == ["ERR SALON"] and not c.ferme


@dans_boucle
def test_avant_join_les_commandes_sont_refusees():
    s = salons()
    c = entrer(s, "TCHAT COUCOU")
    assert c.lignes == ["ERR NOM"]


@dans_boucle
def test_deconnexion_libere_la_place_dans_son_salon():
    s = salons()
    a = entrer(s, "JOIN A 2")
    b = entrer(s, "JOIN B 2")
    s.deconnexion(a)
    assert s.tables[1].sieges[0].humain is None
    assert "SIEGE 0 B BOT" in b.lignes and s.tables[1].chef == 1
    s.deconnexion(a)  # deux fois : sans effet


@dans_boucle
def test_c64_redemarre_reprend_sa_place_dans_un_salon_plein():
    s = salons()
    vieux = entrer(s, "JOIN A 3", adresse="10.0.0.5")
    for nom in "BCD":
        entrer(s, f"JOIN {nom} 3")
    neuf = entrer(s, "JOIN A 3", adresse="10.0.0.5")
    assert neuf.lignes[0] == "BIENVENUE A 0" and vieux.ferme
    assert s.est_assis(neuf)


@dans_boucle
def test_inactivite_verifiee_dans_chaque_salon():
    s = salons()
    a = entrer(s, "JOIN A 1")
    b = entrer(s, "JOIN B 3")
    s.tables[2].sieges[0].actif_a = 0.0
    for t in s.tables:
        t.verifier_inactivite(s.tables[2].delai_attente)
    assert b.ferme and not a.ferme


@dans_boucle
def test_raz_par_salon_a_la_console():
    s = salons()
    a = entrer(s, "JOIN A 1")
    b = entrer(s, "JOIN B 2")
    s.recevoir(a, "LANCER")
    s.recevoir(b, "LANCER")
    assert commande_console(s, "RAZ 2") == "partie effacee"
    assert s.tables[1].etat == ATTENTE and s.tables[0].etat == EN_COURS
    assert commande_console(s, "RAZ") == "partie effacee"
    assert s.tables[0].etat == ATTENTE
    assert commande_console(s, "RAZ 9").startswith("commande inconnue")
