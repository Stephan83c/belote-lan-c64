#!/usr/bin/env python3
"""Duel de stratégies de bots : python3 tools/duel_bots.py [N] [--ref REF]

Les bots actuels (server/belote/bots.py) jouent contre ceux d'une version du
dépôt (REF, main par défaut, lue avec git show). Chaque donne est jouée deux
fois, équipes échangées (même paquet, même donneur), pour ôter la chance des
cartes : seule la stratégie fait la différence. Affiche la part des points
marqués par les bots actuels (50 % : aussi forts) et l'écart moyen par donne.
"""

from __future__ import annotations

import argparse
import inspect
import random
import subprocess
import sys
import types
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "server"))

from belote import bots as actuels  # noqa: E402
from belote.moteur import Donne, Phase, couleur  # noqa: E402


def bots_de(ref: str) -> types.ModuleType:
    source = subprocess.run(["git", "-C", str(RACINE), "show", f"{ref}:server/belote/bots.py"],
                            capture_output=True, text=True, check=True).stdout
    module = types.ModuleType(f"bots_{ref}")
    module.__package__ = "belote"
    exec(compile(source, f"{ref}:bots.py", "exec"), module.__dict__)
    return module


def jouer(paquet: list[int], donneur: int, strategies) -> tuple[int, int] | None:
    """Une donne ; strategies[p % 2] joue la place p. None si tout le monde passe."""
    d = Donne(donneur, paquet=paquet)
    while d.phase is Phase.ENCHERES:
        p = d.joueur
        s = strategies[p % 2]
        # Avant la v2.0, les bots ne recevaient que la couleur de la retournée.
        ancienne = "couleur_retournee" in inspect.signature(s.choisir_enchere).parameters
        choix = s.choisir_enchere(d.mains[p], d.tour_encheres,
                                  couleur(d.retournee) if ancienne else d.retournee)
        if choix is None:
            d.passer(p)
        else:
            d.prendre(p, choix)
    if d.phase is not Phase.JEU:
        return None
    while d.phase is Phase.JEU:
        p = d.joueur
        s = strategies[p % 2]
        if "preneur" in inspect.signature(s.choisir_carte).parameters:
            c = s.choisir_carte(d.mains[p], d.pli, d.atout, p, d.jouees, d.preneur)
        else:
            c = s.choisir_carte(d.mains[p], d.pli, d.atout, p, d.jouees)
        d.jouer(p, c)
    return d.resultat().points


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("n", nargs="?", type=int, default=20000, help="donnes (chacune jouée deux fois)")
    ap.add_argument("--ref", default="main", help="version git des bots adverses")
    ap.add_argument("--graine", type=int, default=1)
    args = ap.parse_args()

    anciens = bots_de(args.ref)
    rng = random.Random(args.graine)
    nous = eux = redonnes = 0
    for i in range(args.n):
        paquet = list(range(32))
        rng.shuffle(paquet)
        for actuels_en in (0, 1):                    # les actuels en équipe 0, puis en équipe 1
            strategies = (actuels, anciens) if actuels_en == 0 else (anciens, actuels)
            pts = jouer(paquet, i % 4, strategies)
            if pts is None:
                redonnes += 1
                continue
            nous += pts[actuels_en]
            eux += pts[1 - actuels_en]
    total = 2 * args.n
    print(f"{total} donnes ({redonnes} redonnées) : actuels {nous} points, {args.ref} {eux} points")
    print(f"part des actuels : {100 * nous / (nous + eux):.2f} %, écart moyen {(nous - eux) / total:+.2f} "
          f"points par donne")


if __name__ == "__main__":
    main()
