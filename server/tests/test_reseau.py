"""Bout en bout sur une vraie socket TCP, comme le ferait nc."""

import asyncio
import random

from belote.__main__ import Limites, commande_console, demarrer
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


async def serveur(graine=3, delai=0.0, delai_join=60.0, limites=None):
    table = Table(rng=random.Random(graine), delai_bot=delai)
    srv = await demarrer(table, "127.0.0.1", 0, delai_join, limites)
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


def test_connexion_sans_join_fermee_apres_le_delai():
    async def corps():
        _, srv, port = await serveur(delai_join=0.2)
        muet = await connecter(port)
        assise = await connecter(port)
        await assise.envoyer("JOIN A")
        await assise.lire_jusqu_a("PARAM INACTIF 3")
        # Le muet est coupé ; la connexion assise reste ouverte et répond.
        assert await asyncio.wait_for(muet.reader.read(), 5) == b""
        await asyncio.sleep(0.3)
        await assise.envoyer("TCHAT TOUJOURS LA")
        assert await assise.lire() == "TCHAT A TOUJOURS LA"
        assise.writer.close()
        srv.close()
    asyncio.run(corps())


def test_trop_de_connexions_par_ip_refusees():
    async def corps():
        limites = Limites(total=64, par_ip=2)
        _, srv, port = await serveur(limites=limites)
        a, b = await connecter(port), await connecter(port)
        c = await connecter(port)
        assert await c.lire() == "ERR TABLE PLEINE"
        assert await asyncio.wait_for(c.reader.read(), 5) == b""
        # Une place se libère : la connexion suivante est acceptée.
        a.writer.close()
        await asyncio.sleep(0.1)
        d = await connecter(port)
        await d.envoyer("JOIN D")
        assert await d.lire() == "BIENVENUE D 0"
        assert limites.ouvertes == {"127.0.0.1": 2}
        b.writer.close()
        d.writer.close()
        await asyncio.sleep(0.1)
        assert limites.ouvertes == {}
        srv.close()
    asyncio.run(corps())


def test_trop_de_connexions_en_tout_refusees():
    async def corps():
        _, srv, port = await serveur(limites=Limites(total=3, par_ip=8))
        js = [await connecter(port) for _ in range(3)]
        e = await connecter(port)
        assert await e.lire() == "ERR TABLE PLEINE"
        for j in js:
            j.writer.close()
        srv.close()
    asyncio.run(corps())


def test_salons_par_le_reseau():
    from belote.salons import Salons

    async def corps():
        salons = Salons([Table(rng=random.Random(i), delai_bot=0.0) for i in range(2)])
        srv = await demarrer(salons, "127.0.0.1", 0)
        port = srv.sockets[0].getsockname()[1]
        a = await connecter(port)
        await a.envoyer("SALONS")
        assert [await a.lire() for _ in range(3)] == ["SALONS 2", "SALON 1 0 ATTENTE", "SALON 2 0 ATTENTE"]
        await a.envoyer("JOIN A 2")
        assert await a.lire() == "BIENVENUE A 0"
        b = await connecter(port)
        await b.envoyer("SALONS")
        assert [await b.lire() for _ in range(3)][2] == "SALON 2 1 ATTENTE"
        a.writer.close()
        b.writer.close()
        srv.close()
    asyncio.run(corps())


def test_liste_des_salons_laisse_le_temps_de_choisir():
    from belote.salons import Salons

    async def corps():
        salons = Salons([Table(rng=random.Random(i), delai_bot=0.0) for i in range(2)])
        srv = await demarrer(salons, "127.0.0.1", 0, delai_join=0.2, delai_liste=0.8)
        port = srv.sockets[0].getsockname()[1]
        muet, lecteur = await connecter(port), await connecter(port)
        await lecteur.envoyer("SALONS")
        await lecteur.lire_jusqu_a("SALON 2 0 ATTENTE")
        await asyncio.sleep(0.4)
        # Le muet est coupé au bout de 0,2 s ; celui qui regarde la liste reste.
        assert await asyncio.wait_for(muet.reader.read(), 1) == b""
        await lecteur.envoyer("JOIN L 2")
        assert await lecteur.lire() == "BIENVENUE L 0"
        # Assis : le délai ne le concerne plus.
        await asyncio.sleep(0.6)
        await lecteur.envoyer("TCHAT ENCORE LA")
        await lecteur.lire_jusqu_a("TCHAT L ENCORE LA")
        retard = await connecter(port)
        await retard.envoyer("SALONS")
        assert await asyncio.wait_for(retard.reader.read(), 2) != b""
        assert await asyncio.wait_for(retard.reader.read(), 2) == b""   # fermé après 0,8 s
        lecteur.writer.close()
        srv.close()
    asyncio.run(corps())
