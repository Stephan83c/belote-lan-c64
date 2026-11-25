"""Bots à style (SPEC 4.4) : chaque bot a un style, tiré au sort, qui donne son nom.

Un style règle deux choses : le seuil de prise aux enchères (valeur de la main, bots.valeur_main)
et l'objectif du PIMC au jeu de la carte (pimc.choisir). Le feinteur joue parfois une carte
presque aussi bonne que la meilleure, mais pas celle qu'un joueur attendrait.

Noms : BOT<style> pour la variante 1, BOT<style><variante> pour les variantes 2 et 3 (BOT12,
BOT13...). Une variante décale tous les seuils de prise du style (-2, 0, +2), pour que deux bots du
même style ne jouent pas tout à fait pareil. Mesuré avec tools/styles.py (R&D, étape 51 de la
SPEC) : les styles sont à égalité en tables tirées au hasard, avec ou sans doublons.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    code: int               # premier chiffre du nom
    nom: str
    seuil: int              # seuil de prise ; 32 = stratégie simple (bots.SEUIL_PRISE)
    objectif: str           # 'attaque', 'defense', 'ecart', 'adaptatif'
    tolerance: float = 0.0  # feinteur : points d'écart moyen acceptés pour surprendre


STYLES = {
    1: Style(1, "attaquant", 26, "attaque"),
    2: Style(2, "defenseur", 34, "defense"),
    3: Style(3, "modere", 32, "ecart"),
    4: Style(4, "adaptatif", 32, "adaptatif"),
    5: Style(5, "feinteur", 32, "ecart", tolerance=3.0),
}
VARIANTES = {1: -2, 2: 0, 3: 2}

# Numéros des bots : dizaine = style, unité = variante (11 à 53).
NUMEROS = [10 * s + v for s in STYLES for v in VARIANTES]


def nom_bot(numero: int) -> str:
    """BOT1 pour 11, BOT12 pour 12, BOT13 pour 13, BOT2 pour 21..."""
    return f"BOT{numero // 10}" if numero % 10 == 1 else f"BOT{numero}"


def tirer_numero(pris: set[int], rng: random.Random) -> int:
    """Un numéro de bot au hasard parmi ceux que la table n'utilise pas."""
    return rng.choice([n for n in NUMEROS if n not in pris])


def mode(numero: int, mon_score: int, son_score: int, cible: int) -> tuple[str, int, float]:
    """(objectif du PIMC, seuil de prise, tolérance de feinte) du bot `numero` selon le score.

    L'adaptatif attaque s'il est mené de 150 points ou si l'adversaire approche de la cible, se
    défend s'il mène de 150 points, joue l'écart de points sinon.
    """
    style, d = STYLES[numero // 10], VARIANTES[numero % 10]
    if style.objectif != "adaptatif":
        return style.objectif, style.seuil + d, style.tolerance
    retard = son_score - mon_score
    if retard >= 150 or son_score >= cible - 200 > mon_score:
        return "attaque", 26 + d, 0.0
    if retard <= -150:
        return "defense", 38 + d, 0.0
    return "ecart", 32 + d, 0.0


def utilite(objectif: str, mes: int, leurs: int) -> float:
    """Note d'une fin de donne simulée (points de mon camp, points de l'autre)."""
    if objectif == "attaque":       # convexe : le capot et les grosses manches pèsent lourd
        return (mes / 100) ** 2 - (leurs / 100) ** 2 * 0.5
    if objectif == "defense":       # gagner la manche (réussir le contrat ou le faire chuter)
        return 100.0 * (mes > leurs) + 0.1 * (mes - leurs)
    return float(mes - leurs)       # écart de points
