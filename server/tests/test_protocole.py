"""Cadrage et encodage (SPEC 7.1)."""

from belote.protocole import TROP_LONG, Cadreur, nettoyer


def test_majuscules_et_caracteres_interdits():
    assert nettoyer(b"tchat bonjour") == "TCHAT BONJOUR"
    assert nettoyer(b"a{b\tc") == "A?B?C"
    assert nettoyer("é".encode()) == "??"


def test_ascii_32_a_95_conserve():
    plage = bytes(range(32, 96))
    assert nettoyer(plage) == plage.decode("ascii")


def test_ligne_terminee_par_lf_et_cr_ignore():
    c = Cadreur()
    assert c.alimenter(b"JOIN A\nLANCER\r\n") == ["JOIN A", "LANCER"]


def test_ligne_recue_en_plusieurs_morceaux():
    c = Cadreur()
    assert c.alimenter(b"JO") == []
    assert c.alimenter(b"IN A\nLA") == ["JOIN A"]
    assert c.alimenter(b"NCER\n") == ["LANCER"]


def test_64_octets_lf_compris_acceptes():
    c = Cadreur()
    assert c.alimenter(b"A" * 63 + b"\n") == ["A" * 63]
    assert c.alimenter(b"A" * 63 + b"\r\n") == ["A" * 63]


def test_65_octets_refuses():
    c = Cadreur()
    assert c.alimenter(b"A" * 64 + b"\n") == [TROP_LONG]


def test_ligne_tres_longue_en_morceaux_un_seul_refus_puis_reprise():
    c = Cadreur()
    assert c.alimenter(b"A" * 200) == []
    assert c.alimenter(b"A" * 200) == []
    assert c.alimenter(b"A\nLANCER\n") == [TROP_LONG, "LANCER"]
