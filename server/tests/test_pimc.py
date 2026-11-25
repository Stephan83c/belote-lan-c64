"""Bots PIMC (4.4) : coups toujours légaux, repli, intégration à la table."""

import asyncio
import random
from concurrent.futures import ThreadPoolExecutor

from belote import pimc
from belote.bots import choisir_carte, choisir_enchere
from belote.moteur import Donne, Phase, coups_legaux, couleur
from belote.table import Table


def _donne_en_jeu(graine):
    rng = random.Random(graine)
    d = Donne(graine % 4, rng)
    while d.phase is Phase.ENCHERES:
        p = d.joueur
        choix = choisir_enchere(d.mains[p], d.tour_encheres, d.retournee)
        d.passer(p) if choix is None else d.prendre(p, choix)
    return d if d.phase is Phase.JEU else None


def _une_donne():
    return next(d for d in map(_donne_en_jeu, range(20)) if d is not None)


def test_choisir_donne_toujours_un_coup_legal():
    rng = random.Random(5)
    jouees = 0
    for graine in range(40):
        d = _donne_en_jeu(graine)
        if d is None:
            continue
        while d.phase is Phase.JEU:
            p = d.joueur
            c = pimc.choisir(d.mains[p], d.pli, d.plis, d.jouees, d.atout, p, d.preneur, d.retournee,
                             d.points_cartes, d.plis_gagnes, tirages=8, rng=rng)
            assert c in coups_legaux(d.mains[p], d.pli, d.atout, p)
            d.jouer(p, c)
            jouees += 1
    assert jouees > 200


def test_choisir_ne_modifie_pas_la_donne():
    d = _une_donne()
    p = d.joueur
    avant = ([list(m) for m in d.mains], list(d.pli), list(d.jouees), list(d.points_cartes))
    pimc.choisir(d.mains[p], d.pli, d.plis, d.jouees, d.atout, p, d.preneur, d.retournee,
                 d.points_cartes, d.plis_gagnes, tirages=5)
    assert avant == (d.mains, d.pli, d.jouees, d.points_cartes)


def test_donne_garde_les_plis_termines():
    d = _une_donne()
    while d.phase is Phase.JEU:
        d.jouer(d.joueur, choisir_carte(d.mains[d.joueur], d.pli, d.atout, d.joueur, d.jouees, d.preneur))
    assert len(d.plis) == 8 and all(len(p) == 4 for p in d.plis)


def _humain():
    class Faux:
        def __init__(self):
            self.lignes = []

        def envoyer(self, ligne):
            self.lignes.append(ligne)

        def fermer(self):
            pass
    return Faux()


def _passer_si_attendu(t, h):
    """L'humain (place 0) passe aux enchères : la donne ne reste pas bloquée sur lui."""
    d = t.donne
    if d is not None and d.phase is Phase.ENCHERES and d.joueur == 0:
        t.recevoir(h, "PASSE")


def test_table_un_bot_joue_par_pimc():
    """Avec un exécuteur, le bot joue sa carte en tâche asynchrone, légalement."""
    async def corps():
        t = Table(rng=random.Random(1), delai_bot=0)
        t.executeur = ThreadPoolExecutor(2)
        h = _humain()
        t.recevoir(h, "JOIN A")
        t.recevoir(h, "LANCER")
        for _ in range(300):
            await asyncio.sleep(0.01)
            _passer_si_attendu(t, h)
            if any(l.startswith("JOUE") for l in h.lignes):
                break
        assert any(l.startswith("JOUE") for l in h.lignes)
        t.executeur.shutdown()
        if t._minuteur_bot:
            t._minuteur_bot.cancel()
    asyncio.run(corps())


def test_table_repli_si_le_pool_echoue():
    class Casse:
        def submit(self, *a, **k):
            raise RuntimeError("pool cassé")

    async def corps():
        t = Table(rng=random.Random(1), delai_bot=0)
        t.executeur = Casse()
        h = _humain()
        t.recevoir(h, "JOIN A")
        t.recevoir(h, "LANCER")
        for _ in range(300):
            await asyncio.sleep(0.01)
            _passer_si_attendu(t, h)
            if any(l.startswith("JOUE") for l in h.lignes):
                break
        assert any(l.startswith("JOUE") for l in h.lignes)
        if t._minuteur_bot:
            t._minuteur_bot.cancel()
    asyncio.run(corps())
