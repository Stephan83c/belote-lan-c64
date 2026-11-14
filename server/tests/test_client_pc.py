"""Client PC (pc/belote_lan.py) : règles recopiées du serveur, suivi de la partie, clavier."""

import asyncio
import importlib.util
import random
import re
from pathlib import Path

import pytest

from belote import moteur
from belote.__main__ import demarrer
from belote.table import Table

_RACINE = Path(__file__).resolve().parents[2]
_CHEMIN = _RACINE / "pc" / "belote_lan.py"
if not _CHEMIN.exists():          # paquet du serveur (make paquet-serveur) : pas de client PC
    pytest.skip("client PC absent", allow_module_level=True)
_spec = importlib.util.spec_from_file_location("belote_lan", _CHEMIN)
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)


def test_version_identique_au_makefile():
    makefile = (_RACINE / "Makefile").read_text(encoding="utf-8")
    assert re.search(r"^VERSION := (\S+)", makefile, re.M).group(1) == pc.VERSION


def test_coups_legaux_identiques_au_serveur():
    rng = random.Random(7)
    for _ in range(20000):
        paquet = list(range(32))
        rng.shuffle(paquet)
        atout = rng.randrange(4)
        main = sorted(paquet[: rng.randint(1, 8)])
        nb = rng.randrange(4)
        entame = rng.randrange(4)
        pli = [((entame + i) % 4, c) for i, c in enumerate(paquet[8: 8 + nb])]
        place = (entame + nb) % 4
        assert pc.coups_legaux(main, pli, atout, place) == moteur.coups_legaux(main, pli, atout, place)


def test_points_et_gagnant_identiques_au_serveur():
    for atout in range(4):
        for c in range(32):
            assert pc.points_carte(c, atout) == moteur.points_carte(c, atout)
            assert pc.force(c, atout) == moteur.force(c, atout)


def test_plicours_retrouve_l_ordre_du_pli():
    p = pc.Partie()
    p.recevoir("PLICOURS -1 -1 14 3")          # P2 a entamé, puis P3
    assert p.pli == [(2, 14), (3, 3)]
    p.recevoir("PLICOURS 5 -1 -1 7")           # P3 a entamé, puis P0
    assert p.pli == [(3, 7), (0, 5)]
    p.recevoir("PLICOURS -1 -1 -1 -1")
    assert p.pli == []


def test_reconnexion_en_jeu_sans_points_inconnus():
    p = pc.Partie()
    for ligne in ("BIENVENUE JEAN 1", "ETAT EN COURS", "PREND 2 1", "MAIN 3 9",
                  "PLICOURS 4 -1 -1 -1", "TOUR 1"):
        p.recevoir(ligne)
    assert p.points is None and p.atout == 1 and p.a_moi()
    assert p.jouables() == [3]                 # pique demandé : fournir le 10 de pique


def test_infos_et_erreurs():
    p = pc.Partie()
    p.recevoir("ERR NOM RESERVE")
    assert p.erreur_join == "NOM RESERVE"
    p.recevoir("BIENVENUE JEAN 0")
    p.recevoir("INFO MARC INACTIF REMPLACE PAR UN BOT")
    p.recevoir("INFO RESERVE 81 POUR EQUIPE 1")
    p.recevoir("ERR COUP REFUSE")
    assert p.journal[-3:] == [("i_inactif_bot", "MARC"), ("i_reserve_eux", "81"),
                              ("j_refus", ("err", "COUP REFUSE"))]


def test_touches_unix():
    assert pc.decouper_touches("\x1b[A\x1b[Dx\r\x1bOP\x1b[15~\x7f\x1b") == [
        "UP", "LEFT", "x", "ENTER", "F1", "F5", "BACK", "ESC"]


def test_en_ascii():
    assert pc.en_ascii("Été à Noël ♥") == "ETE A NOEL ?"


async def _partie_complete(graine):
    """Le client joue des cartes au hasard parmi ses jouables() contre le vrai serveur :
    aucun refus, et 162 points de cartes comptés à chaque manche."""
    table = Table(rng=random.Random(graine), delai_bot=0.0, delai_manche=0.0)
    srv = await demarrer(table, "127.0.0.1", 0)
    port = srv.sockets[0].getsockname()[1]
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    rng = random.Random(graine)
    p = pc.Partie()

    async def envoyer(ligne):
        writer.write(ligne.encode() + b"\n")
        await writer.drain()

    await envoyer("JOIN JEAN")
    await envoyer("PARAM CIBLE 500")
    await envoyer("LANCER")
    manches = 0
    try:
        while p.etat != pc.FIN_PARTIE:
            ligne = (await asyncio.wait_for(reader.readline(), 5)).decode().rstrip("\n")
            assert not ligne.startswith("ERR"), ligne
            p.recevoir(ligne)
            if ligne.startswith("MANCHE "):
                manches += 1
                assert sum(p.points) == 162 and sum(p.plis) == 8
            if p.a_moi():
                choix = p.choix_encheres()
                if choix:
                    c = rng.choice(choix)
                    await envoyer("PASSE" if c[0] == "PASSE" else "ENCH %d" % c[1])
                else:
                    await envoyer("COUP %d" % rng.choice(p.jouables()))
                p.tour = -1
    finally:
        writer.close()
        srv.close()
        await srv.wait_closed()
    assert manches >= 2 and p.gagnant is not None


def test_parties_completes_contre_le_serveur():
    for graine in range(4):
        asyncio.run(_partie_complete(graine))
