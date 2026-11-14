"""Serveur TCP : python -m belote [--host H] [--port 6464] [--delai-bot 1.0] [--delai-manche 10]"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

from .protocole import TROP_LONG, Cadreur
from .table import DELAI_BOT, DELAI_MANCHE, Table

log = logging.getLogger("belote")

TAMPON_ENVOI_MAX = 64 * 1024
# Une connexion sans place à la table au bout de ce délai est fermée : sur un serveur
# public, des connexions vides ne s'accumulent pas. Le C64 envoie JOIN aussitôt connecté.
DELAI_JOIN = 60.0


class ConnexionTCP:
    def __init__(self, writer: asyncio.StreamWriter):
        self.writer = writer
        pair = writer.get_extra_info("peername")
        self.adresse = pair[0] if pair else None

    def envoyer(self, ligne: str) -> None:
        if self.writer.is_closing():
            return
        self.writer.write(ligne.encode("ascii") + b"\n")
        # La logique de table est synchrone : un client qui ne lit plus est coupé.
        if self.writer.transport.get_write_buffer_size() > TAMPON_ENVOI_MAX:
            self.writer.transport.abort()

    def fermer(self) -> None:
        self.writer.close()


async def gerer_client(table: Table, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                       delai_join: float = DELAI_JOIN) -> None:
    pair = writer.get_extra_info("peername")
    log.info("connexion %s", pair)
    client = ConnexionTCP(writer)
    cadreur = Cadreur()

    def sans_place() -> None:
        if not table.est_assis(client):
            log.info("sans JOIN depuis %.0f s, fermee %s", delai_join, pair)
            client.fermer()

    minuteur = asyncio.get_running_loop().call_later(delai_join, sans_place)
    try:
        while not writer.is_closing():
            bloc = await reader.read(256)
            if not bloc:
                break
            for ligne in cadreur.alimenter(bloc):
                if writer.is_closing():
                    break
                if ligne is TROP_LONG:
                    client.envoyer("ERR TROP LONG")
                else:
                    table.recevoir(client, ligne)
    except ConnectionError:
        pass
    finally:
        minuteur.cancel()
        table.deconnexion(client)
        client.fermer()
        log.info("deconnexion %s", pair)


def commande_console(table: Table, ligne: str) -> str | None:
    """Commande tapée dans le terminal du serveur ; renvoie la réponse à afficher."""
    mot = ligne.strip(" ")
    if not mot:
        return None
    if mot == "RAZ":
        return "partie effacee" if table.raz() else "aucune partie a effacer"
    return "commande inconnue (disponible : RAZ)"


def ecouter_console(table: Table) -> None:
    """Lit stdin sans bloquer la boucle ; ignoré si stdin n'est pas surveillable."""
    boucle = asyncio.get_running_loop()
    fd = sys.stdin.fileno()
    cadreur = Cadreur()

    def lire() -> None:
        bloc = os.read(fd, 256)
        if not bloc:  # fin de stdin : le serveur continue sans console
            boucle.remove_reader(fd)
            return
        for ligne in cadreur.alimenter(bloc):
            if ligne is not TROP_LONG and (reponse := commande_console(table, ligne)):
                log.info("console : %s", reponse)

    try:
        boucle.add_reader(fd, lire)
    except OSError:  # /dev/null ou fichier ordinaire
        log.info("console indisponible")


async def demarrer(table: Table, host: str | None, port: int,
                   delai_join: float = DELAI_JOIN) -> asyncio.Server:
    async def rappel(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await gerer_client(table, reader, writer, delai_join)

    return await asyncio.start_server(rappel, host, port)


async def principal(host: str, port: int, delai_bot: float, delai_manche: float) -> None:
    table = Table(delai_bot=delai_bot, delai_manche=delai_manche)
    serveur = await demarrer(table, host, port)
    inactivite = asyncio.create_task(table.boucle_inactivite())
    ecouter_console(table)
    log.info("serveur de belote sur %s:%d (console : RAZ efface la partie)", host, port)
    try:
        async with serveur:
            await serveur.serve_forever()
    finally:
        inactivite.cancel()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serveur de belote C64")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=6464)
    parser.add_argument("--delai-bot", type=float, default=DELAI_BOT, help="secondes par action de bot")
    parser.add_argument("--delai-manche", type=float, default=DELAI_MANCHE,
                        help="secondes de pause en fin de manche avant la suivante")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    try:
        asyncio.run(principal(args.host, args.port, args.delai_bot, args.delai_manche))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
