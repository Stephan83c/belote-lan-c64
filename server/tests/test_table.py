"""Table : connexion, chef, paramètres, messages, bots, inactivité, reconnexion."""

import asyncio
import random

import pytest

from belote.moteur import Donne, Phase, compter_manche, couleur
from belote.table import ATTENTE, EN_COURS, FIN_MANCHE, FIN_PARTIE, Table


class FauxClient:
    def __init__(self):
        self.lignes = []
        self.ferme = False

    def envoyer(self, ligne):
        self.lignes.append(ligne)

    def fermer(self):
        self.ferme = True

    def vider(self):
        lignes, self.lignes = self.lignes, []
        return lignes

    def dernier(self, mot):
        return next((l for l in reversed(self.lignes) if l.split(" ")[0] == mot), None)


def dans_boucle(corps):
    """Exécute un test synchrone dans une boucle asyncio (minuteurs des bots)."""
    def lanceur():
        async def principal():
            corps()
        asyncio.run(principal())
    lanceur.__name__ = corps.__name__
    return lanceur


def rejoindre(table, nom="JEAN"):
    client = FauxClient()
    table.recevoir(client, f"JOIN {nom}")
    return client


def table_ne_jouant_pas():
    """Table dont les bots n'agissent jamais sans qu'on les déclenche."""
    return Table(rng=random.Random(1), delai_bot=3600)


# ---- Connexion ----------------------------------------------------------


@dans_boucle
def test_premiere_connexion_sequence_de_la_spec():
    t = table_ne_jouant_pas()
    c = rejoindre(t)
    assert c.lignes == [
        "BIENVENUE JEAN 0",
        "SIEGE 0 H JEAN",
        "SIEGE 1 B BOT",
        "SIEGE 2 B BOT",
        "SIEGE 3 B BOT",
        "CHEF 0",
        "ETAT ATTENTE",
        "PARAM CIBLE 1000",
        "PARAM INACTIF 3",
    ]


@dans_boucle
def test_nom_invalide_refuse():
    t = table_ne_jouant_pas()
    for ligne in ("JOIN", "JOIN TROPLONG", "JOIN A-B", "JOIN A B"):
        c = FauxClient()
        t.recevoir(c, ligne)
        assert c.lignes == ["ERR NOM"]


@dans_boucle
def test_commande_avant_join_refusee():
    c = FauxClient()
    table_ne_jouant_pas().recevoir(c, "LANCER")
    assert c.lignes == ["ERR NOM"]


@dans_boucle
def test_doublon_dernier_caractere_remplace():
    t = table_ne_jouant_pas()
    rejoindre(t)
    c = rejoindre(t)
    assert "BIENVENUE JEA2 1" in c.lignes


@dans_boucle
def test_nom_final_court():
    t = table_ne_jouant_pas()
    rejoindre(t, "A")
    assert "BIENVENUE 2 1" in rejoindre(t, "A").lignes


@dans_boucle
def test_noms_de_bots_refuses():
    t = table_ne_jouant_pas()
    for nom in ("BOT", "BOT1", "BOT4", "BOT12"):
        c = FauxClient()
        t.recevoir(c, f"JOIN {nom}")
        assert c.lignes == ["ERR NOM RESERVE"]
        assert not c.ferme
    # Le client peut réessayer sur la même connexion avec un autre nom.
    t.recevoir(c, "JOIN BOTTE")
    assert "BIENVENUE BOTTE 0" in c.lignes
    assert "BIENVENUE BOB 1" in rejoindre(t, "BOB").lignes


@dans_boucle
def test_suffixe_ne_donne_pas_un_nom_de_bot():
    t = table_ne_jouant_pas()
    rejoindre(t, "BOTA")
    c = rejoindre(t, "BOTA")
    assert c.lignes == ["ERR NOM"]  # BOT2 à BOT9 et BOT1 sont réservés


@dans_boucle
def test_cinquieme_connexion_refusee():
    t = table_ne_jouant_pas()
    for n in "ABCD":
        rejoindre(t, n)
    c = rejoindre(t, "E")
    assert c.lignes == ["ERR TABLE PLEINE"]
    assert c.ferme


@dans_boucle
def test_diffusion_de_l_arrivee_aux_autres():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    a.vider()
    rejoindre(t, "B")
    assert a.lignes == ["SIEGE 1 H B"]


# ---- Chef ---------------------------------------------------------------


@dans_boucle
def test_chef_seul_peut_lancer_et_regler():
    t = table_ne_jouant_pas()
    rejoindre(t, "A")
    b = rejoindre(t, "B")
    b.vider()
    for ligne in ("LANCER", "PARAM CIBLE 500", "REJOUER"):
        t.recevoir(b, ligne)
    assert b.lignes == ["ERR CHEF SEUL"] * 3
    assert t.etat == ATTENTE


@dans_boucle
def test_passation_du_chef_au_premier_humain_restant():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    c = rejoindre(t, "C")
    b.vider(); c.vider()
    t.recevoir(a, "LEAVE")
    assert a.ferme
    assert "SIEGE 0 B BOT" in c.lignes
    assert "CHEF 1" in c.lignes
    assert t.chef == 1


@dans_boucle
def test_table_sans_humain_sans_chef_puis_nouveau_chef():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    t.recevoir(a, "LEAVE")
    assert t.chef == -1
    b = rejoindre(t, "B")
    assert t.chef == 0
    assert "BIENVENUE B 0" in b.lignes


@dans_boucle
def test_lancer_deux_fois():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    t.recevoir(a, "LANCER")
    a.vider()
    t.recevoir(a, "LANCER")
    assert a.lignes == ["ERR DEJA LANCEE"]


@dans_boucle
def test_premier_donneur_est_le_chef():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    rejoindre(t, "B")
    t.recevoir(a, "LANCER")
    assert t.donneur == 0
    assert t.donne.joueur == 1


# ---- Paramètres ---------------------------------------------------------


@pytest.mark.parametrize(
    "ligne,attendu",
    [
        ("PARAM CIBLE 500", "PARAM CIBLE 500"),
        ("PARAM CIBLE 5000", "PARAM CIBLE 5000"),
        ("PARAM CIBLE 499", "ERR PARAM"),
        ("PARAM CIBLE 5001", "ERR PARAM"),
        ("PARAM CIBLE X", "ERR PARAM"),
        ("PARAM INACTIF 1", "PARAM INACTIF 1"),
        ("PARAM INACTIF 10", "PARAM INACTIF 10"),
        ("PARAM INACTIF 0", "ERR PARAM"),
        ("PARAM INACTIF 11", "ERR PARAM"),
        ("PARAM AUTRE 1", "ERR PARAM"),
    ],
)
def test_param_bornes(ligne, attendu):
    async def corps():
        t = table_ne_jouant_pas()
        a = rejoindre(t, "A")
        a.vider()
        t.recevoir(a, ligne)
        assert a.lignes == [attendu]
    asyncio.run(corps())


@dans_boucle
def test_param_refuse_apres_lancement():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    t.recevoir(a, "LANCER")
    a.vider()
    t.recevoir(a, "PARAM CIBLE 500")
    assert a.lignes == ["ERR DEJA LANCEE"]


# ---- Manche : séquence, secret des mains, refus -------------------------


@dans_boucle
def test_sequence_de_lancement():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    a.vider()
    t.recevoir(a, "LANCER")
    d = t.donne
    assert a.lignes == [
        "ETAT LANCEE",
        "SCORE 0 0",
        "ETAT EN COURS",
        "DONNEUR 0",
        "MAIN " + " ".join(map(str, d.mains[0])),
        "NBCARTES 5 5 5 5",
        f"RETOURNE {d.retournee}",
        "ENCHERES 1",
        "TOUR 1",
    ]


@dans_boucle
def test_main_triee_et_jamais_celle_des_autres():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    t.recevoir(a, "LANCER")
    main_a = a.dernier("MAIN")
    main_b = b.dernier("MAIN")
    assert main_a != main_b
    assert sum(1 for l in a.lignes if l.startswith("MAIN")) == 1
    cartes = list(map(int, main_a.split()[1:]))
    assert cartes == sorted(cartes) and len(cartes) == 5


def table_lancee_toute_humaine():
    t = table_ne_jouant_pas()
    clients = [rejoindre(t, n) for n in "ABCD"]
    t.recevoir(clients[0], "LANCER")
    for c in clients:
        c.vider()
    return t, clients


def faire_prendre(t, clients):
    """P1 prend la couleur retournée."""
    t.recevoir(clients[1], f"ENCH {couleur(t.donne.retournee)}")
    for c in clients:
        c.vider()


@dans_boucle
def test_enchere_hors_tour_et_mauvaise_couleur():
    t, c = table_lancee_toute_humaine()
    t.recevoir(c[0], "PASSE")
    assert c[0].lignes == ["ERR PAS TON TOUR"]
    autre = (couleur(t.donne.retournee) + 1) % 4
    t.recevoir(c[1], f"ENCH {autre}")
    assert c[1].lignes == ["ERR COUP REFUSE"]
    t.recevoir(c[1], "ENCH X")
    assert c[1].lignes[-1] == "ERR COUP REFUSE"
    assert t.donne.joueur == 1


@dans_boucle
def test_coup_pendant_les_encheres_refuse():
    t, c = table_lancee_toute_humaine()
    t.recevoir(c[1], "COUP 0")
    assert c[1].lignes == ["ERR COUP REFUSE"]


@dans_boucle
def test_coup_hors_partie():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    a.vider()
    t.recevoir(a, "COUP 0")
    assert a.lignes == ["ERR PAS TON TOUR"]


@dans_boucle
def test_prise_diffusee_et_seconde_distribution():
    t, c = table_lancee_toute_humaine()
    atout = couleur(t.donne.retournee)
    t.recevoir(c[1], f"ENCH {atout}")
    assert c[0].lignes == [
        f"PREND 1 {atout}",
        "MAIN " + " ".join(map(str, t.donne.mains[0])),
        "NBCARTES 8 8 8 8",
        "TOUR 1",
    ]


@dans_boucle
def test_coup_accepte_diffuse_et_main_renvoyee_au_seul_joueur():
    t, c = table_lancee_toute_humaine()
    faire_prendre(t, c)
    carte_jouee = t.donne.mains[1][0]
    t.recevoir(c[1], f"COUP {carte_jouee}")
    assert f"JOUE 1 {carte_jouee}" in c[0].lignes
    assert "TOUR 2" in c[0].lignes
    assert not any(l.startswith("MAIN") for l in c[0].lignes)
    assert any(l.startswith("MAIN") for l in c[1].lignes)
    assert carte_jouee not in t.donne.mains[1]


@dans_boucle
def test_coup_refuse_le_meme_joueur_garde_la_main():
    t, c = table_lancee_toute_humaine()
    faire_prendre(t, c)
    absente = next(x for x in range(32) if x not in t.donne.mains[1])
    t.recevoir(c[1], f"COUP {absente}")
    assert c[1].lignes == ["ERR COUP REFUSE"]
    assert c[0].lignes == []
    assert t.donne.joueur == 1


@dans_boucle
def test_tout_le_monde_passe_redonne_et_donneur_suivant():
    t, c = table_lancee_toute_humaine()
    for tour in range(8):
        t.recevoir(c[(1 + tour) % 4], "PASSE")
    assert "REDONNE" in c[0].lignes
    i = c[0].lignes.index("REDONNE")
    assert c[0].lignes[i + 1:i + 3] == ["ETAT EN COURS", "DONNEUR 1"]
    assert t.donneur == 1
    assert t.donne.joueur == 2


@dans_boucle
def test_tchat_diffuse_et_tronque():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    a.vider(); b.vider()
    t.recevoir(a, "TCHAT " + "X" * 40)
    assert b.lignes == ["TCHAT A " + "X" * 30]
    assert a.lignes == b.lignes
    b.vider()
    t.recevoir(a, "TCHAT    ")
    assert b.lignes == []


@dans_boucle
def test_commande_inconnue():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    a.vider()
    t.recevoir(a, "XYZ")
    assert a.lignes == ["ERR INCONNU"]


# ---- Fin de manche, F5, fin de partie -----------------------------------


class DonneTruquee(Donne):
    """Donne dont le résultat est imposé, pour tester la fin de manche."""

    def __init__(self, resultat_):
        self._res = resultat_

    def resultat(self, reserve=0):
        return self._res(reserve)


def fin_manche(t, resultat_):
    t.donne = DonneTruquee(resultat_)
    t.etat = EN_COURS
    t._appliquer([("FIN",)])


@dans_boucle
def test_fin_de_manche_messages_dans_l_ordre():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    t.recevoir(a, "LANCER")
    a.vider()
    fin_manche(t, lambda r: compter_manche(0, (90, 72), (5, 3), None, r))
    assert a.lignes == ["MANCHE 90 72", "SCORE 90 72", "ETAT FIN MANCHE"]
    assert t.etat == FIN_MANCHE


@dans_boucle
def test_capot_annonce():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    t.recevoir(a, "LANCER")
    a.vider()
    fin_manche(t, lambda r: compter_manche(1, (0, 162), (0, 8), None, r))
    assert a.lignes[:2] == ["CAPOT 1", "MANCHE 0 252"]


@dans_boucle
def test_litige_puis_reserve_attribuee_la_manche_suivante():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    t.recevoir(a, "LANCER")
    a.vider()
    fin_manche(t, lambda r: compter_manche(0, (81, 81), (4, 4), None, r))
    assert a.lignes == ["LITIGE 81", "MANCHE 0 81", "SCORE 0 81", "ETAT FIN MANCHE"]
    assert t.reserve == 81
    a.vider()
    fin_manche(t, lambda r: compter_manche(0, (90, 72), (5, 3), None, r))
    assert "MANCHE 171 72" in a.lignes
    assert "SCORE 171 153" in a.lignes
    assert t.reserve == 0


@dans_boucle
def test_donne_annulee_ne_solde_pas_la_reserve():
    t, c = table_lancee_toute_humaine()
    t.reserve = 81
    for tour in range(8):
        t.recevoir(c[(1 + tour) % 4], "PASSE")
    assert "REDONNE" in c[0].lignes
    assert t.reserve == 81
    assert t.scores == [0, 0]


@dans_boucle
def test_rejouer_manche_suivante_score_conserve_donneur_tourne():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    t.recevoir(a, "LANCER")
    fin_manche(t, lambda r: compter_manche(0, (90, 72), (5, 3), None, r))
    a.vider()
    t.recevoir(a, "REJOUER")
    assert a.lignes[:2] == ["ETAT EN COURS", "DONNEUR 1"]
    assert t.scores == [90, 72]


@dans_boucle
def test_rejouer_pendant_la_manche_refuse():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    t.recevoir(a, "LANCER")
    a.vider()
    t.recevoir(a, "REJOUER")
    assert a.lignes == ["ERR DEJA LANCEE"]


@dans_boucle
def test_rejouer_en_attente_refuse():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    a.vider()
    t.recevoir(a, "REJOUER")
    assert a.lignes == ["ERR PAS LANCEE"]


@dans_boucle
def test_gagnant_et_nouvelle_partie_scores_et_reserve_remis_a_zero():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    t.recevoir(a, "PARAM CIBLE 500")
    t.recevoir(a, "LANCER")
    t.scores = [450, 100]
    t.reserve = 81
    a.vider()
    # Litige : la défense (équipe 0) passe la cible, la réserve reste en jeu puis est perdue.
    fin_manche(t, lambda r: compter_manche(1, (81, 81), (4, 4), None, r))
    assert a.lignes[-2:] == ["GAGNANT 0", "ETAT FIN PARTIE"]
    assert t.etat == FIN_PARTIE
    a.vider()
    t.recevoir(a, "REJOUER")
    assert a.lignes[:4] == ["ETAT LANCEE", "SCORE 0 0", "ETAT EN COURS", "DONNEUR 1"]
    assert t.scores == [0, 0] and t.reserve == 0


@dans_boucle
def test_reconnexion_en_fin_de_partie_renvoie_le_gagnant():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    t.recevoir(a, "PARAM CIBLE 500")
    t.recevoir(a, "LANCER")
    t.scores = [100, 450]
    fin_manche(t, lambda r: compter_manche(1, (40, 122), (3, 5), None, r))
    assert t.etat == FIN_PARTIE
    t.deconnexion(b)
    retour = rejoindre(t, "B")
    assert "ETAT FIN PARTIE" in retour.lignes
    assert retour.lignes[-1] == "GAGNANT 1"


@dans_boucle
def test_egalite_parfaite_a_la_cible_manche_supplementaire():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    t.recevoir(a, "PARAM CIBLE 500")
    t.recevoir(a, "LANCER")
    t.scores = [420, 438]
    fin_manche(t, lambda r: compter_manche(0, (90, 72), (5, 3), None, r))
    assert t.scores == [510, 510]
    assert t.etat == FIN_MANCHE


# ---- Bots ---------------------------------------------------------------


def test_bots_immobiles_tant_que_non_lancee():
    async def corps():
        t = Table(rng=random.Random(1), delai_bot=0)
        a = rejoindre(t, "A")
        a.vider()
        await asyncio.sleep(0.02)
        assert a.lignes == []
    asyncio.run(corps())


def test_delai_du_bot_respecte():
    async def corps():
        t = Table(rng=random.Random(1), delai_bot=0.1)
        a = rejoindre(t, "A")
        t.recevoir(a, "LANCER")
        a.vider()
        await asyncio.sleep(0.03)
        assert a.lignes == []
        await asyncio.sleep(0.12)
        assert a.lignes
    asyncio.run(corps())


def test_pause_apres_une_prise(monkeypatch):
    """Après une prise, le premier bot attend FACTEUR_PAUSE_PRISE délais, puis on
    revient au délai normal."""
    import belote.table as module

    async def corps():
        t = Table(rng=random.Random(1), delai_bot=10)
        a = rejoindre(t, "A")
        t.recevoir(a, "LANCER")
        d = t.donne
        assert t.sieges[d.joueur].humain is None
        monkeypatch.setattr(module, "choisir_enchere", lambda main, tour, c: c)
        boucle = asyncio.get_running_loop()
        t._action_bot()                        # le premier à parler prend
        assert d.phase is Phase.JEU
        assert t.sieges[d.joueur].humain is None  # et entame
        assert 29 < t._minuteur_bot.when() - boucle.time() <= 30
        t._action_bot()                        # première carte
        if t.sieges[d.joueur].humain is None:
            assert 9 < t._minuteur_bot.when() - boucle.time() <= 10
        if t._minuteur_bot:
            t._minuteur_bot.cancel()
    asyncio.run(corps())


def test_deconnexion_pendant_son_tour_le_bot_joue_immediatement():
    async def corps():
        t = Table(rng=random.Random(1), delai_bot=3600)
        a = rejoindre(t, "A")
        b = rejoindre(t, "B")
        t.recevoir(a, "LANCER")
        assert t.donne.joueur == 1
        a.vider()
        t.deconnexion(b)
        await asyncio.sleep(0.01)
        assert any(l.startswith(("PASSE 1", "PREND 1")) for l in a.lignes)
    asyncio.run(corps())


def test_sans_humain_les_bots_s_arretent():
    async def corps():
        t = Table(rng=random.Random(1), delai_bot=0)
        a = rejoindre(t, "A")
        t.recevoir(a, "LANCER")
        t.deconnexion(a)
        d = t.donne
        joueur = d.joueur
        await asyncio.sleep(0.02)
        assert t.donne is d and d.joueur == joueur
        assert t.etat == EN_COURS
    asyncio.run(corps())


def test_partie_complete_avec_un_humain_et_trois_bots():
    async def corps():
        t = Table(rng=random.Random(7), delai_bot=0)
        a = rejoindre(t, "A")
        t.recevoir(a, "PARAM CIBLE 500")
        t.recevoir(a, "LANCER")
        total_manches = 0
        for _ in range(100_000):
            await asyncio.sleep(0)
            if t.etat == FIN_PARTIE:
                break
            if t.etat == FIN_MANCHE:
                total_manches += 1
                t.recevoir(a, "REJOUER")
            elif t.etat == EN_COURS and t.donne.joueur == 0:
                d = t.donne
                if d.phase is Phase.ENCHERES:
                    t.recevoir(a, "PASSE")
                else:
                    t.recevoir(a, f"COUP {d.legaux(0)[0]}")
        assert t.etat == FIN_PARTIE
        assert max(t.scores) >= 500
        assert not any(l == "ERR COUP REFUSE" for l in a.lignes)
        assert a.dernier("GAGNANT") in ("GAGNANT 0", "GAGNANT 1")
    asyncio.run(corps())


# ---- Inactivité et reconnexion ------------------------------------------


@dans_boucle
def test_inactif_a_son_tour_remplace_par_un_bot():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    t.recevoir(a, "LANCER")
    assert t.donne.joueur == 1
    a.vider()
    t.verifier_inactivite(t._attendu_depuis + 179)
    assert not b.ferme
    t.verifier_inactivite(t._attendu_depuis + 180)
    assert b.ferme
    assert "SIEGE 1 B BOT" in a.lignes


@dans_boucle
def test_inactivite_reglable():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    t.recevoir(a, "PARAM INACTIF 1")
    t.recevoir(a, "LANCER")
    t.verifier_inactivite(t._attendu_depuis + 60)
    assert b.ferme


@dans_boucle
def test_pas_d_inactivite_en_attente_ni_hors_de_son_tour():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    t.verifier_inactivite(t._attendu_depuis + 10_000)
    assert not a.ferme and not b.ferme
    t.recevoir(a, "LANCER")  # c'est à B : A n'est pas attendu
    t.sieges[1].actif_a = t._attendu_depuis
    t.verifier_inactivite(t._attendu_depuis + 10_000)
    assert not a.ferme and b.ferme


@dans_boucle
def test_tchat_compte_comme_activite():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    t.recevoir(a, "LANCER")
    t.recevoir(b, "TCHAT SALUT")
    t.verifier_inactivite(t.sieges[1].actif_a + 179)
    assert not b.ferme


@dans_boucle
def test_chef_inactif_en_fin_de_manche_passe_la_main():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    t.recevoir(a, "LANCER")
    fin_manche(t, lambda r: compter_manche(0, (90, 72), (5, 3), None, r))
    t.verifier_inactivite(t._attendu_depuis + 180)
    assert a.ferme and not b.ferme
    assert t.chef == 1


@dans_boucle
def test_reconnexion_retrouve_sa_place_et_sa_main():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    t.recevoir(a, "LANCER")
    atout = couleur(t.donne.retournee)
    t.recevoir(b, f"ENCH {atout}")
    c1 = t.donne.mains[1][0]
    t.recevoir(b, f"COUP {c1}")
    t.deconnexion(b)

    retour = rejoindre(t, "B")
    d = t.donne
    pli = ["-1", str(c1), "-1", "-1"]
    assert retour.lignes == [
        "BIENVENUE B 1",
        "SIEGE 0 H A",
        "SIEGE 1 H B",
        "SIEGE 2 B BOT",
        "SIEGE 3 B BOT",
        "CHEF 0",
        "ETAT EN COURS",
        "PARAM CIBLE 1000",
        "PARAM INACTIF 3",
        "SCORE 0 0",
        "DONNEUR 0",
        f"PREND 1 {atout}",
        "MAIN " + " ".join(map(str, d.mains[1])),
        "NBCARTES 8 7 8 8",
        "PLICOURS " + " ".join(pli),
        "TOUR 2",
    ]


@dans_boucle
def test_reconnexion_pendant_les_encheres():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    t.recevoir(a, "LANCER")
    t.deconnexion(b)
    retour = rejoindre(t, "B")
    assert f"RETOURNE {t.donne.retournee}" in retour.lignes
    assert "ENCHERES 1" in retour.lignes
    assert not any(l.startswith("PLICOURS") for l in retour.lignes)


@dans_boucle
def test_reconnexion_place_prise_autre_place_bot():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    t.recevoir(a, "LANCER")
    t.deconnexion(b)
    # Place 1 réservée à B : les nouveaux prennent d'abord les places neutres.
    rejoindre(t, "C")
    rejoindre(t, "D")
    assert t.sieges[1].humain is None
    e = rejoindre(t, "E")  # dernière place, prise à la réservation
    assert "BIENVENUE E 1" in e.lignes
    refuse = rejoindre(t, "B")
    assert refuse.lignes == ["ERR TABLE PLEINE"]


@dans_boucle
def test_join_en_cours_de_partie_prend_une_place_bot():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    t.recevoir(a, "LANCER")
    a.vider()
    b = rejoindre(t, "B")
    assert "BIENVENUE B 1" in b.lignes
    assert any(l.startswith("MAIN") for l in b.lignes)
    assert "SIEGE 1 H B" in a.lignes


# ---- RAZ (console du serveur ou chef) -------------------------------------


def test_raz_efface_la_partie_et_arrete_les_bots():
    async def corps():
        t = Table(rng=random.Random(1), delai_bot=0)
        a = rejoindre(t, "A")
        t.recevoir(a, "PARAM CIBLE 500")
        t.recevoir(a, "LANCER")
        t.scores = [90, 72]
        t.reserve = 81
        a.vider()
        assert t.raz() is True
        assert a.lignes == ["INFO PARTIE EFFACEE", "SCORE 0 0", "ETAT ATTENTE"]
        assert t.donne is None and t.scores == [0, 0] and t.reserve == 0
        assert t.cible == 500
        a.vider()
        await asyncio.sleep(0.02)
        assert a.lignes == []  # le coup de bot planifié est annulé
    asyncio.run(corps())


@dans_boucle
def test_raz_efface_les_places_reservees_et_le_chef_peut_relancer():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    t.recevoir(a, "LANCER")
    t.deconnexion(b)
    t.raz()
    assert t.sieges[1].nom_reserve is None
    t.recevoir(a, "LANCER")
    assert t.etat == EN_COURS and t.donne is not None


@dans_boucle
def test_raz_sans_partie():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    a.vider()
    assert t.raz() is False
    assert a.lignes == []


@dans_boucle
def test_raz_table_vide_le_prochain_arrivant_trouve_une_table_neuve():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    t.recevoir(a, "LANCER")
    t.deconnexion(a)
    assert t.raz() is True
    b = rejoindre(t, "B")
    assert "BIENVENUE B 0" in b.lignes
    assert "ETAT ATTENTE" in b.lignes
    assert t.chef == 0


@dans_boucle
def test_raz_par_le_chef():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    b = rejoindre(t, "B")
    t.recevoir(a, "LANCER")
    a.vider()
    b.vider()
    t.recevoir(b, "RAZ")
    assert b.lignes == ["ERR CHEF SEUL"]
    assert t.etat == EN_COURS
    t.recevoir(a, "RAZ")
    assert a.lignes == ["INFO PARTIE EFFACEE", "SCORE 0 0", "ETAT ATTENTE"]
    assert t.etat == ATTENTE


@dans_boucle
def test_raz_par_le_chef_sans_partie():
    t = table_ne_jouant_pas()
    a = rejoindre(t, "A")
    a.vider()
    t.recevoir(a, "RAZ")
    assert a.lignes == ["ERR PAS LANCEE"]


# ---- Connexion fantôme d'un C64 redémarré ---------------------------------


def rejoindre_depuis(table, nom, adresse):
    client = FauxClient()
    client.adresse = adresse
    table.recevoir(client, f"JOIN {nom}")
    return client


@dans_boucle
def test_meme_nom_meme_adresse_reprend_la_place_en_cours_de_partie():
    t = table_ne_jouant_pas()
    a = rejoindre_depuis(t, "A", "192.168.1.27")
    b = rejoindre_depuis(t, "B", "192.168.1.30")
    t.recevoir(a, "LANCER")
    b.vider()

    a2 = rejoindre_depuis(t, "A", "192.168.1.27")
    assert a.ferme
    assert a2.lignes[0] == "BIENVENUE A 0"
    assert "MAIN " + " ".join(map(str, t.donne.mains[0])) in a2.lignes
    assert t.sieges[0].humain is a2 and t.chef == 0
    assert b.lignes == ["INFO A RECONNECTE"]

    # La fermeture de l'ancienne connexion ne libère pas la place reprise.
    t.deconnexion(a)
    assert t.sieges[0].humain is a2
    t.recevoir(a2, "TCHAT ME REVOILA")
    assert b.dernier("TCHAT") == "TCHAT A ME REVOILA"


@dans_boucle
def test_meme_nom_autre_adresse_garde_le_suffixe():
    t = table_ne_jouant_pas()
    a = rejoindre_depuis(t, "JEAN", "192.168.1.27")
    autre = rejoindre_depuis(t, "JEAN", "192.168.1.30")
    assert not a.ferme
    assert "BIENVENUE JEA2 1" in autre.lignes


@dans_boucle
def test_meme_adresse_autre_nom_prend_une_nouvelle_place():
    t = table_ne_jouant_pas()
    a = rejoindre_depuis(t, "A", "192.168.1.27")
    b = rejoindre_depuis(t, "B", "192.168.1.27")
    assert not a.ferme
    assert "BIENVENUE B 1" in b.lignes
