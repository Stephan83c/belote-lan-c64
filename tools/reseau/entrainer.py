#!/usr/bin/env python3
"""Réseau de neurones qui imite le bot PIMC pour jouer la carte (prototype, hors serveur).

    nice -n 19 tools/reseau/.venv/bin/python tools/reseau/entrainer.py --heures 8 --processus 6

Trois phases, reprenables (on relance la même commande, rien n'est perdu) :
  1. données : le PIMC (server/belote/pimc.py) joue contre lui-même ; on note l'état visible et
     la carte choisie (fichiers donnees/part_*.npz) ;
  2. entraînement : petit réseau (MLP) en NumPy, il apprend à choisir la même carte ;
  3. mesure : le réseau joue contre la stratégie simple (bots.py), chaque donne jouée deux fois,
     équipes échangées ; part des points écrite dans resultat.txt (cible : 55 % ou plus).

Le budget --heures est partagé : 35 % données, 50 % entraînement, le reste pour la mesure.
Tout est écrit dans travail/ (ignoré par git). Voir memo.txt.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE / "server"))

# Les bibliothèques de calcul ne doivent pas dépasser le nombre de processus demandé.
_pre = argparse.ArgumentParser(add_help=False)
_pre.add_argument("--processus", type=int, default=6)
_nb = str(max(1, _pre.parse_known_args()[0].processus))
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, _nb)

import numpy as np  # noqa: E402

from belote import bots, pimc  # noqa: E402
from belote.moteur import Donne, Phase, coups_legaux, equipe, gagnant_pli, points_carte  # noqa: E402

N_CARACT = 248
H = 256


# ---- Caractéristiques (état visible d'une place) --------------------------------------------


def caracteristiques(main, pli, plis, atout, place, preneur, retournee, points_cartes, plis_gagnes):
    """Vecteur de N_CARACT nombres : tout ce que la place sait, vu depuis elle (0 moi, 1 suivant,
    2 partenaire, 3 précédent). Pure Python : ce code devra servir au serveur."""
    x = [0.0] * N_CARACT
    for c in main:
        x[c] = 1.0
    for p in plis + [pli]:                       # 32 + 32*r + carte : posée par la place relative r
        for pl, c in p:
            x[32 + 32 * ((pl - place) % 4) + c] = 1.0
    for _, c in pli:                             # 160 : dans le pli en cours
        x[160 + c] = 1.0
    if pli:                                      # 192 : meneur du pli
        x[192 + (pli[0][0] - place) % 4] = 1.0
    x[196 + atout] = 1.0                         # 196 : atout
    x[200 + (preneur - place) % 4] = 1.0         # 200 : preneur
    x[204 + retournee] = 1.0                     # 204 : retournée
    vides = pimc.vides(plis + [pli], atout)      # 236 : couleurs manquantes des 3 autres
    for pl in range(4):
        r = (pl - place) % 4
        if r:
            for s in vides[pl]:
                x[236 + (r - 1) * 4 + s] = 1.0
    nous, eux = equipe(place), 1 - equipe(place)  # 248-4 .. : points et plis
    x[244] = (points_cartes[nous] - points_cartes[eux]) / 162.0
    x[245] = sum(plis_gagnes) / 8.0
    x[246] = plis_gagnes[nous] / 8.0
    x[247] = plis_gagnes[eux] / 8.0
    return x


# ---- Phase 1 : données ------------------------------------------------------------------------


def une_partie(rng, tirages):
    """Une donne jouée par quatre PIMC ; liste de (x, carte, masque) ou None si tous passent."""
    paquet = list(range(32))
    rng.shuffle(paquet)
    d = Donne(rng.randrange(4), paquet=paquet)
    while d.phase is Phase.ENCHERES:
        p = d.joueur
        choix = bots.choisir_enchere(d.mains[p], d.tour_encheres, d.retournee)
        d.passer(p) if choix is None else d.prendre(p, choix)
    if d.phase is not Phase.JEU:
        return None
    lignes = []
    while d.phase is Phase.JEU:
        p = d.joueur
        main = d.mains[p]
        legaux = coups_legaux(main, d.pli, d.atout, p)
        c = pimc.choisir(main, d.pli, d.plis, d.jouees, d.atout, p, d.preneur, d.retournee,
                         d.points_cartes, d.plis_gagnes, tirages, rng)
        if len(legaux) > 1:
            x = caracteristiques(main, d.pli, d.plis, d.atout, p, d.preneur, d.retournee,
                                 d.points_cartes, d.plis_gagnes)
            masque = sum(1 << k for k in legaux)
            lignes.append((x, c, masque))
        d.jouer(p, c)
    return lignes


def fabriquer(args):
    """Un fichier de données : nb_parties donnes. Tourne dans un processus du pool."""
    dossier, numero, nb_parties, tirages, charge = args
    debut = time.time()
    rng = random.Random(numero * 7919 + 13)
    X, Y, M = [], [], []
    faites = 0
    while faites < nb_parties:
        lignes = une_partie(rng, tirages)
        if lignes is None:
            continue
        faites += 1
        for x, c, m in lignes:
            X.append(x)
            Y.append(c)
            M.append(m)
    chemin = Path(dossier) / f"part_{numero:05d}.npz"
    tmp = Path(dossier) / f"tmp_{numero:05d}.npz"
    np.savez_compressed(tmp, x=np.array(X, dtype=np.float16), y=np.array(Y, dtype=np.uint8),
                        m=np.array(M, dtype=np.uint32))
    os.replace(tmp, chemin)
    travail = time.time() - debut
    if charge < 1:                               # cycle de travail : on laisse refroidir
        time.sleep(travail * (1 / charge - 1))
    return len(Y)


def phase_donnees(a, travail, jr):
    dossier = travail / "donnees"
    dossier.mkdir(exist_ok=True)
    limite = time.time() + a.budget_donnees
    existants = sorted(dossier.glob("part_*.npz"))
    numero = max([int(p.stem[5:]) for p in existants], default=-1) + 1
    jr(f"données : {len(existants)} fichiers déjà là, {a.budget_donnees / 3600:.2f} h de budget")
    total = 0
    with Pool(a.processus) as pool:
        while time.time() < limite:
            lot = [(str(dossier), numero + i, a.parties_par_fichier, a.tirages, a.charge)
                   for i in range(a.processus)]
            numero += a.processus
            total += sum(pool.map(fabriquer, lot))
            n = len(list(dossier.glob("part_*.npz")))
            jr(f"données : {n} fichiers, +{total} échantillons cette fois")


# ---- Phase 2 : entraînement --------------------------------------------------------------------


def charger(dossier, maximum):
    fichiers = sorted(dossier.glob("part_*.npz"))
    X, Y, M = [], [], []
    n = 0
    for f in reversed(fichiers):                 # les plus récents d'abord si on plafonne
        with np.load(f) as z:
            X.append(z["x"]); Y.append(z["y"]); M.append(z["m"])
            n += len(z["y"])
        if n >= maximum:
            break
    return np.concatenate(X[::-1]), np.concatenate(Y[::-1]), np.concatenate(M[::-1])


def masques(bits):
    return ((bits[:, None] >> np.arange(32, dtype=np.uint32)) & 1).astype(np.float32)


def avant(P, x, mask=None):
    z1 = x @ P["W1"] + P["b1"]
    a1 = np.maximum(z1, 0)
    z2 = a1 @ P["W2"] + P["b2"]
    a2 = np.maximum(z2, 0)
    z3 = a2 @ P["W3"] + P["b3"]
    if mask is not None:
        z3 = np.where(mask > 0, z3, -1e9)
    return z1, a1, z2, a2, z3


def precision(P, X, Y, M, taille=4096):
    ok = 0
    for i in range(0, len(Y), taille):
        z = avant(P, X[i:i + taille].astype(np.float32), masques(M[i:i + taille]))[4]
        ok += int((z.argmax(1) == Y[i:i + taille]).sum())
    return ok / max(1, len(Y))


def phase_entrainement(a, travail, jr):
    X, Y, M = charger(travail / "donnees", a.max_echantillons)
    n = len(Y)
    if n < 2000:
        jr(f"entraînement : seulement {n} échantillons, lancer d'abord la phase données")
        return
    nv = max(1000, n // 20)                      # validation : les plus récents
    Xv, Yv, Mv = X[-nv:], Y[-nv:], M[-nv:]
    X, Y, M = X[:-nv], Y[:-nv], M[:-nv]
    n = len(Y)
    jr(f"entraînement : {n} échantillons + {nv} de validation, {a.budget_entrainement / 3600:.2f} h")

    reprise = travail / "reprise.npz"
    rng = np.random.default_rng(1)
    if reprise.exists():
        z = np.load(reprise)
        P = {k: z[k] for k in ("W1", "b1", "W2", "b2", "W3", "b3")}
        m = {k: z["m_" + k] for k in P}
        v = {k: z["v_" + k] for k in P}
        pas = int(z["pas"])
        jr(f"entraînement : reprise au pas {pas}")
    else:
        P = {"W1": (rng.standard_normal((N_CARACT, H)) * math.sqrt(2 / N_CARACT)).astype(np.float32),
             "b1": np.zeros(H, np.float32),
             "W2": (rng.standard_normal((H, H)) * math.sqrt(2 / H)).astype(np.float32),
             "b2": np.zeros(H, np.float32),
             "W3": (rng.standard_normal((H, 32)) * math.sqrt(1 / H)).astype(np.float32),
             "b3": np.zeros(32, np.float32)}
        m = {k: np.zeros_like(p) for k, p in P.items()}
        v = {k: np.zeros_like(p) for k, p in P.items()}
        pas = 0

    debut = time.time()
    meilleure = precision(P, Xv, Yv, Mv)
    jr(f"entraînement : précision de départ {100 * meilleure:.1f} %")
    B = 512
    epoque = 0
    dernier = time.time()
    while time.time() - debut < a.budget_entrainement:
        ordre = rng.permutation(n)
        for i in range(0, n - B + 1, B):
            frac = min(1.0, (time.time() - debut) / a.budget_entrainement)
            lr = 1e-5 + a.lr * 0.5 * (1 + math.cos(math.pi * frac))
            idx = np.sort(ordre[i:i + B])
            x = X[idx].astype(np.float32)
            mask = masques(M[idx])
            z1, a1, z2, a2, z3 = avant(P, x, mask)
            z3 = z3 - z3.max(1, keepdims=True)
            p = np.exp(z3)
            p /= p.sum(1, keepdims=True)
            p[np.arange(B), Y[idx]] -= 1
            dz3 = p / B
            g = {"W3": a2.T @ dz3, "b3": dz3.sum(0)}
            da2 = dz3 @ P["W3"].T
            dz2 = da2 * (z2 > 0)
            g["W2"] = a1.T @ dz2
            g["b2"] = dz2.sum(0)
            dz1 = (dz2 @ P["W2"].T) * (z1 > 0)
            g["W1"] = x.T @ dz1
            g["b1"] = dz1.sum(0)
            pas += 1
            for k in P:                          # Adam
                m[k] = 0.9 * m[k] + 0.1 * g[k]
                v[k] = 0.999 * v[k] + 0.001 * g[k] * g[k]
                mh = m[k] / (1 - 0.9 ** pas)
                vh = v[k] / (1 - 0.999 ** pas)
                P[k] -= (lr * mh / (np.sqrt(vh) + 1e-8)).astype(np.float32)
            if a.charge < 1 and pas % 50 == 0:
                time.sleep(0.02 * (1 / a.charge - 1))
            if time.time() - debut >= a.budget_entrainement:
                break
        epoque += 1
        if time.time() - dernier < 60 and time.time() - debut < a.budget_entrainement:
            continue                             # petit jeu de données : pas de journal à chaque tour
        dernier = time.time()
        acc = precision(P, Xv, Yv, Mv)
        jr(f"entraînement : époque {epoque}, pas {pas}, précision validation {100 * acc:.2f} %")
        np.savez(reprise, pas=pas, **P, **{"m_" + k: m[k] for k in P}, **{"v_" + k: v[k] for k in P})
        if acc >= meilleure:
            meilleure = acc
            np.savez(travail / "poids.npz", **P)
            (travail / "poids.json").write_text(
                json.dumps({k: np.round(p, 5).tolist() for k, p in P.items()}))
    jr(f"entraînement fini : meilleure précision de validation {100 * meilleure:.2f} %")


# ---- Phase 3 : mesure ------------------------------------------------------------------------


def jouer_mesure(P, paquet, donneur, equipe_reseau):
    d = Donne(donneur, paquet=paquet)
    while d.phase is Phase.ENCHERES:
        p = d.joueur
        choix = bots.choisir_enchere(d.mains[p], d.tour_encheres, d.retournee)
        d.passer(p) if choix is None else d.prendre(p, choix)
    if d.phase is not Phase.JEU:
        return None
    while d.phase is Phase.JEU:
        p = d.joueur
        legaux = coups_legaux(d.mains[p], d.pli, d.atout, p)
        if equipe(p) == equipe_reseau and len(legaux) > 1:
            x = np.array(caracteristiques(d.mains[p], d.pli, d.plis, d.atout, p, d.preneur, d.retournee,
                                          d.points_cartes, d.plis_gagnes), np.float32)
            z = avant(P, x[None, :])[4][0]
            c = max(legaux, key=lambda k: z[k])
        else:
            c = bots.choisir_carte(d.mains[p], d.pli, d.atout, p, d.jouees, d.preneur)
        d.jouer(p, c)
    return d.resultat().points


def mesurer(args):
    chemin, graine, n = args
    with np.load(chemin) as z:
        P = {k: z[k] for k in ("W1", "b1", "W2", "b2", "W3", "b3")}
    rng = random.Random(graine)
    nous = eux = 0
    for i in range(n):
        paquet = list(range(32))
        rng.shuffle(paquet)
        for e in (0, 1):
            pts = jouer_mesure(P, paquet, i % 4, e)
            if pts:
                nous += pts[e]
                eux += pts[1 - e]
    return nous, eux


def phase_mesure(a, travail, jr):
    poids = travail / "poids.npz"
    if not poids.exists():
        jr("mesure : pas de poids, lancer d'abord l'entraînement")
        return
    jr(f"mesure : {a.donnes_mesure} donnes par processus, {a.processus} processus")
    with Pool(a.processus) as pool:
        res = pool.map(mesurer, [(str(poids), 1000 + i, a.donnes_mesure) for i in range(a.processus)])
    nous = sum(r[0] for r in res)
    eux = sum(r[1] for r in res)
    part = 100 * nous / (nous + eux)
    ligne = (f"{time.strftime('%Y-%m-%d %H:%M')} : le réseau marque {part:.2f} % des points contre la "
             f"stratégie simple ({2 * a.donnes_mesure * a.processus} parties). "
             f"{'OBJECTIF ATTEINT' if part >= 55 else 'objectif (55 %) non atteint'}")
    jr("mesure : " + ligne)
    with open(travail / "resultat.txt", "a", encoding="utf-8") as f:
        f.write(ligne + "\n")


# ---- Programme --------------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--heures", type=float, default=8.0, help="budget total de cette exécution")
    ap.add_argument("--processus", type=int, default=6)
    ap.add_argument("--charge", type=float, default=0.85,
                    help="part du temps passée à calculer (1 : sans pause ; plus bas : CPU plus frais)")
    ap.add_argument("--phase", choices=("tout", "donnees", "entrainement", "mesure"), default="tout")
    ap.add_argument("--tirages", type=int, default=100, help="tirages du PIMC qui joue les données")
    ap.add_argument("--parties-par-fichier", type=int, default=100)
    ap.add_argument("--max-echantillons", type=int, default=3_000_000)
    ap.add_argument("--donnes-mesure", type=int, default=2500, help="donnes par processus pour la mesure")
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--dossier", default=str(ICI / "travail"))
    ap.add_argument("--essai", action="store_true", help="mini-run de quelques minutes pour tout vérifier")
    a = ap.parse_args()
    if a.essai:
        a.heures, a.parties_par_fichier, a.donnes_mesure = 0.05, 8, 40
        a.dossier = str(ICI / "travail" / "essai")
    travail = Path(a.dossier)
    travail.mkdir(parents=True, exist_ok=True)
    total = a.heures * 3600
    a.budget_donnees, a.budget_entrainement = 0.35 * total, 0.50 * total

    def jr(texte):
        ligne = f"{time.strftime('%H:%M:%S')} {texte}"
        print(ligne, flush=True)
        with open(travail / "journal.log", "a", encoding="utf-8") as f:
            f.write(ligne + "\n")

    jr(f"départ : {a.heures} h, {a.processus} processus, charge {a.charge}, phase {a.phase}")
    if a.phase in ("tout", "donnees"):
        phase_donnees(a, travail, jr)
    if a.phase in ("tout", "entrainement"):
        phase_entrainement(a, travail, jr)
    if a.phase in ("tout", "mesure"):
        phase_mesure(a, travail, jr)
    jr("terminé")


if __name__ == "__main__":
    main()
