"""Serveur TCP : python -m belote [--host H] [--port 6464] [--delai-bot 1.0] [--delai-manche 10]
[--delai-attente 600] [--salons 9] [--max-connexions 64] [--max-par-ip 8]"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
import os
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import sys

from .protocole import TROP_LONG, Cadreur
from .salons import NB_SALONS, Salons
from .table import DELAI_ATTENTE, DELAI_BOT, DELAI_MANCHE, Table

log = logging.getLogger("belote")

TAMPON_ENVOI_MAX = 64 * 1024
# Une connexion sans place à la table au bout de ce délai est fermée : sur un serveur
# public, des connexions vides ne s'accumulent pas. Le C64 envoie JOIN aussitôt connecté.
DELAI_JOIN = 60.0
# Une connexion qui a demandé la liste des salons a ce délai pour en choisir un.
DELAI_LISTE = 300.0
# Limites du serveur entier (toutes tables confondues, pour le multi-salon) :
# 8 connexions par IP laissent jouer 4 C64 derrière une même box.
MAX_CONNEXIONS = 64
MAX_PAR_IP = 8


class Limites:
    """Compte les connexions ouvertes, en tout et par adresse IP."""

    def __init__(self, total: int = MAX_CONNEXIONS, par_ip: int = MAX_PAR_IP):
        self.total, self.par_ip = total, par_ip
        self.ouvertes: dict[str, int] = {}

    def prendre(self, ip: str) -> bool:
        if sum(self.ouvertes.values()) >= self.total or self.ouvertes.get(ip, 0) >= self.par_ip:
            return False
        self.ouvertes[ip] = self.ouvertes.get(ip, 0) + 1
        return True

    def rendre(self, ip: str) -> None:
        self.ouvertes[ip] -= 1
        if not self.ouvertes[ip]:
            del self.ouvertes[ip]


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


async def gerer_client(table: Table | Salons, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                       delai_join: float = DELAI_JOIN, delai_liste: float = DELAI_LISTE) -> None:
    pair = writer.get_extra_info("peername")
    log.info("connexion %s", pair)
    client = ConnexionTCP(writer)
    cadreur = Cadreur()
    debut = time.monotonic()
    octets = 0
    premiere = None
    derniere = None
    a_ete_assis = False
    type_client = "inconnu"       # CLIENT C64 2.1, CLIENT PC 2.1 ; absent avant la v2.1

    minuteur = None

    def sans_place(prolonge: bool = False) -> None:
        nonlocal minuteur
        if table.est_assis(client):
            return
        # Devant la liste des salons (SALONS demandé), le joueur a le temps de choisir.
        if not prolonge and isinstance(table, Salons) and table.a_demande_liste(client):
            minuteur = asyncio.get_running_loop().call_later(delai_liste - delai_join, sans_place, True)
            return
        log.info("sans JOIN a temps, fermee %s", pair)
        client.fermer()

    minuteur = asyncio.get_running_loop().call_later(delai_join, sans_place)
    try:
        while not writer.is_closing():
            bloc = await reader.read(256)
            if not bloc:
                break
            octets += len(bloc)
            for ligne in cadreur.alimenter(bloc):
                if premiere is None:
                    premiere = ligne if isinstance(ligne, str) else "(trop long)"
                if writer.is_closing():
                    break
                if ligne is TROP_LONG:
                    client.envoyer("ERR TROP LONG")
                elif ligne.startswith("CLIENT ") and not table.est_assis(client):
                    # Type de client, pour les logs ; réponse attendue par les clients v2.1.
                    type_client = "".join(c for c in ligne[7:27] if " " <= c <= "~")
                    log.info("client %s : %s", pair, type_client)
                    client.envoyer("CLIENT OK")
                else:
                    table.recevoir(client, ligne)
                    a_ete_assis = a_ete_assis or table.est_assis(client)
                derniere = ligne if isinstance(ligne, str) else "(trop long)"
    except ConnectionError:
        pass
    finally:
        minuteur.cancel()
        assis = a_ete_assis or table.est_assis(client)
        table.deconnexion(client)
        client.fermer()
        log.info("deconnexion %s (%s) apres %.1f s, %d octets recus, %s, 1re ligne : %s, derniere : %s",
                 pair, type_client, time.monotonic() - debut, octets, "assis" if assis else "jamais assis",
                 ascii(premiere[:40]) if premiere is not None else "aucune",
                 ascii(derniere[:40]) if derniere is not None else "aucune")


def commande_console(salle: Table | Salons, ligne: str) -> str | None:
    """Commande tapée dans le terminal du serveur ; renvoie la réponse à afficher.

    RAZ efface la partie de chaque salon, RAZ N celle du salon N seulement.
    """
    mot, _, num = ligne.strip(" ").partition(" ")
    if not mot:
        return None
    if mot == "RAZ" and not num:
        return "partie effacee" if salle.raz() else "aucune partie a effacer"
    if mot == "RAZ" and isinstance(salle, Salons) and num.isdigit() and 1 <= int(num) <= len(salle.tables):
        return "partie effacee" if salle.raz(int(num)) else "aucune partie a effacer"
    return "commande inconnue (disponible : RAZ, RAZ N)"


def ecouter_console(table: Table | Salons) -> None:
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


async def demarrer(table: Table | Salons, host: str | None, port: int,
                   delai_join: float = DELAI_JOIN, limites: Limites | None = None,
                   delai_liste: float = DELAI_LISTE) -> asyncio.Server:
    """Écoute ; une Table seule est servie comme un serveur à un salon."""
    limites = limites or Limites()
    if isinstance(table, Table):
        table = Salons([table])

    async def rappel(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        pair = writer.get_extra_info("peername")
        ip = pair[0] if pair else "?"
        if not limites.prendre(ip):
            # Refusée avant tout, puis fermée. ERR TABLE PLEINE : tous les clients,
            # même ceux d'avant le multi-salon, le traduisent (« réessayez plus tard »).
            log.info("refusee (trop de connexions) %s", pair)
            writer.write(b"ERR TABLE PLEINE\n")
            writer.close()
            return
        try:
            await gerer_client(table, reader, writer, delai_join, delai_liste)
        finally:
            limites.rendre(ip)

    return await asyncio.start_server(rappel, host, port)


async def principal(host: str, port: int, delai_bot: float, delai_manche: float,
                    delai_attente: float, limites: Limites, nb_salons: int, pimc: int = 0,
                    styles: bool = True) -> None:
    tables = [Table(delai_bot=delai_bot, delai_manche=delai_manche, delai_attente=delai_attente,
                    styles=styles)
              for _ in range(nb_salons)]
    executeur = None
    if pimc > 0:
        # Les bots calculent leur carte par PIMC dans pimc processus (4.4) ; spawn : sûr avec asyncio.
        executeur = ProcessPoolExecutor(pimc, mp_context=multiprocessing.get_context("spawn"))
        executeur.submit(int).result()
        for t in tables:
            t.executeur = executeur
    salons = Salons(tables)
    serveur = await demarrer(salons, host, port, limites=limites)
    inactivite = asyncio.create_task(salons.boucle_inactivite())
    ecouter_console(salons)
    log.info("serveur de belote sur %s:%d, %d salons (console : RAZ ou RAZ N efface les parties)",
             host, port, nb_salons)
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
    parser.add_argument("--delai-attente", type=float, default=DELAI_ATTENTE,
                        help="secondes sans message avant le lancement : la place est rendue")
    parser.add_argument("--salons", type=int, default=NB_SALONS, choices=range(1, 10),
                        metavar="1-9", help="nombre de salons (tables de 4 places)")
    parser.add_argument("--pimc", type=int, default=2, metavar="N",
                        help="processus de calcul des bots PIMC (0 : stratégie simple seulement)")
    parser.add_argument("--sans-styles", action="store_true",
                        help="bots sans style, tous nommés BOT (comme en v2.0)")
    parser.add_argument("--max-connexions", type=int, default=MAX_CONNEXIONS,
                        help="connexions ouvertes au plus, en tout")
    parser.add_argument("--max-par-ip", type=int, default=MAX_PAR_IP,
                        help="connexions ouvertes au plus depuis une même adresse IP")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    try:
        asyncio.run(principal(args.host, args.port, args.delai_bot, args.delai_manche,
                              args.delai_attente, Limites(args.max_connexions, args.max_par_ip),
                              args.salons, args.pimc, not args.sans_styles))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
