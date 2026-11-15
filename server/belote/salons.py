"""Plusieurs tables sur un même serveur : les salons (SPEC 4.5).

Chaque salon est une Table complète (sièges, chef, partie, bots, inactivité).
Les Salons aiguillent les lignes : avant JOIN, une connexion peut demander la
liste (SALONS) ; JOIN NOM S la place dans le salon S, JOIN NOM sans numéro dans
le salon 1, comme le font les clients d'avant le multi-salon. Ensuite, tout ce
qu'elle envoie va à sa table.
"""

from __future__ import annotations

import asyncio

from .table import Client, Table

NB_SALONS = 9


class Salons:
    def __init__(self, tables: list[Table]):
        self.tables = tables
        self._table_de: dict[int, Table] = {}  # id(client) -> sa table
        self._liste: set[int] = set()            # id(client) ayant demandé SALONS

    # Même interface que Table pour la boucle réseau (__main__.gerer_client).

    def est_assis(self, client: Client) -> bool:
        table = self._table_de.get(id(client))
        return table is not None and table.est_assis(client)

    def recevoir(self, client: Client, ligne: str) -> None:
        table = self._table_de.get(id(client))
        if table is not None and table.est_assis(client):
            table.recevoir(client, ligne)
            return
        mot, _, reste = ligne.strip(" ").partition(" ")
        if mot == "SALONS":
            self._liste.add(id(client))
            client.envoyer(f"SALONS {len(self.tables)}")
            for n, t in enumerate(self.tables, 1):
                client.envoyer(f"SALON {n} {len(t._humains())} {t.etat}")
        elif mot == "JOIN":
            self._join(client, reste.strip(" "))
        elif mot == "LEAVE":
            client.fermer()
        elif mot:
            client.envoyer("ERR NOM")  # JOIN obligatoire d'abord

    def _join(self, client: Client, reste: str) -> None:
        nom, _, num = reste.partition(" ")
        num = num.strip(" ")
        if not num:
            table = self.tables[0]
        elif num.isascii() and num.isdigit() and 1 <= int(num) <= len(self.tables):
            table = self.tables[int(num) - 1]
            # Salon choisi plein : la connexion reste ouverte pour en choisir un autre.
            if all(s.humain is not None for s in table.sieges) and table._place_fantome(client, nom) is None:
                client.envoyer("ERR TABLE PLEINE")
                return
        else:
            client.envoyer("ERR SALON")
            return
        table.recevoir(client, f"JOIN {nom}")
        if table.est_assis(client):
            self._table_de[id(client)] = table

    def a_demande_liste(self, client: Client) -> bool:
        return id(client) in self._liste

    def deconnexion(self, client: Client) -> None:
        self._liste.discard(id(client))
        table = self._table_de.pop(id(client), None)
        if table is not None:
            table.deconnexion(client)

    def raz(self, numero: int | None = None) -> bool:
        """RAZ de la console : un salon, ou tous sans numéro ; True si une partie est effacée."""
        tables = self.tables if numero is None else [self.tables[numero - 1]]
        return any([t.raz() for t in tables])

    async def boucle_inactivite(self, periode: float = 1.0) -> None:
        while True:
            await asyncio.sleep(periode)
            for t in self.tables:
                t.verifier_inactivite()
