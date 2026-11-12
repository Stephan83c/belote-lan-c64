"""Bout en bout sur une vraie socket TCP, comme le ferait nc."""

import asyncio
import random

from belote.__main__ import commande_console, demarrer
from belote.table import Table


class Joueur:
    """Client minimal : ne connaît que le protocole, essaie ses cartes tour à tour."""

    def __init__(self, reader, writer):
        self.reader, self.writer = reader, writer
        self.recu = []

    async def envoyer(self, ligne):
        self.writer.write(ligne.encode() + b"\n")
        await self.writer.drain()

    async def lire(self):
        ligne = await asyncio.wait_for(self.reader.readline(), 5)
        ligne = ligne.decode().rstrip("\n")
        self.recu.append(ligne)
        return ligne

    async def lire_jusqu_a(self, attendu):
        while True:
            ligne = await self.lire()
            if ligne == attendu:
                return


async def serveur(graine=3, delai=0.0):
    table = Table(rng=random.Random(graine), delai_bot=delai)
    srv = await demarrer(table, "127.0.0.1", 0)
    port = srv.sockets[0].getsockname()[1]
    return table, srv, port


async def connecter(port):
    return Joueur(*await asyncio.open_connection("127.0.0.1", port))


async def jouer_partie(j, place):
    main = []
    cartes_essayees = []
    manches = 0
    while True:
        ligne = await asyncio.wait_for(j.lire(), 5)
        mot, _, reste = ligne.partition(" ")
        if mot == "MAIN":
            main = reste.split()
        elif mot == "TOUR" and int(reste) == place:
            if not en_jeu:
                await j.envoyer("PASSE")
            else:
                cartes_essayees = list(main)
                await j.envoyer(f"COUP {cartes_essayees.pop(0)}")
        elif mot == "ERR":
            assert reste == "COUP REFUSE"
            await j.envoyer(f"COUP {cartes_essayees.pop(0)}")
        elif mot == "PREND":
            en_jeu = True
        elif mot == "ETAT" and reste == "EN COURS":
            en_jeu = False
        elif mot == "ETAT" and reste == "FIN MANCHE":
            manches += 1
            await j.envoyer("REJOUER")
        elif mot == "ETAT" and reste == "FIN PARTIE":
            return manches


def test_partie_complete_sur_socket():
    async def corps():
        table, srv, port = await serveur()
        j = await connecter(port)
        await j.envoyer("join jean")  # minuscules acceptées, comme au clavier
        await j.lire_jusqu_a("PARAM INACTIF 3")
        await j.envoyer("PARAM CIBLE 500")
        await j.lire_jusqu_a("PARAM CIBLE 500")
        await j.envoyer("LANCER")
        await asyncio.wait_for(jouer_partie(j, 0), 60)

        assert max(table.scores) >= 500
        assert any(l.startswith("GAGNANT") for l in j.recu)
        for ligne in j.recu:
            assert len(ligne) + 1 <= 64
            assert all(32 <= ord(ch) <= 95 for ch in ligne)
        j.writer.close()
        srv.close()
    asyncio.run(corps())


def test_ligne_trop_longue_ignoree_sur_socket():
    async def corps():
        _, srv, port = await serveur()
        j = await connecter(port)
        await j.envoyer("TCHAT " + "X" * 100)
        assert await j.lire() == "ERR TROP LONG"
        await j.envoyer("JOIN A")
        assert await j.lire() == "BIENVENUE A 0"
        j.writer.close()
        srv.close()
    asyncio.run(corps())


def test_coupure_brutale_le_bot_reprend_la_place():
    async def corps():
        table, srv, port = await serveur(delai=3600)
        a = await connecter(port)
        await a.envoyer("JOIN A")
        await a.lire_jusqu_a("PARAM INACTIF 3")
        b = await connecter(port)
        await b.envoyer("JOIN B")
        await b.lire_jusqu_a("PARAM INACTIF 3")
        b.writer.close()
        await a.lire_jusqu_a("SIEGE 1 H B")
        await a.lire_jusqu_a("SIEGE 1 B BOT")
        assert table.sieges[1].humain is None
        a.writer.close()
        srv.close()
    asyncio.run(corps())


def test_leave_ferme_la_connexion():
    async def corps():
        _, srv, port = await serveur()
        a = await connecter(port)
        await a.envoyer("JOIN A")
        await a.lire_jusqu_a("PARAM INACTIF 3")
        await a.envoyer("LEAVE")
        assert await asyncio.wait_for(a.reader.read(), 5) == b""
        srv.close()
    asyncio.run(corps())


def test_commande_console():
    async def corps():
        table = Table(rng=random.Random(1), delai_bot=3600)
        assert commande_console(table, "RAZ") == "aucune partie a effacer"
        assert commande_console(table, "") is None
        assert "inconnue" in commande_console(table, "XYZ")
    asyncio.run(corps())


def test_c64_redemarre_reprend_sa_place_sur_vraie_socket():
    async def principal():
        table, srv, port = await serveur(delai=3600)
        async with srv:
            ancien = await connecter(port)
            await ancien.envoyer("JOIN JEAN")
            await ancien.lire_jusqu_a("PARAM INACTIF 3")
            # Reset du C64 : pas de LEAVE, la vieille socket reste ouverte.
            nouveau = await connecter(port)
            await nouveau.envoyer("JOIN JEAN")
            assert await nouveau.lire() == "BIENVENUE JEAN 0"
            # Le serveur ferme l'ancienne connexion.
            assert await asyncio.wait_for(ancien.reader.read(), 5) == b""
            await asyncio.sleep(0.05)
            assert table.sieges[0].humain is not None and table.chef == 0
            nouveau.writer.close()
    asyncio.run(principal())
