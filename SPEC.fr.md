# BELOTE LAN C64 — belote en réseau sur C64 (C / cc65) + tchat

*[English](SPEC.md) · Français*

**Spécification consolidée — version 4**

Client Commodore 64 Ultimate  •  serveur de table Python  •  4 places

*Mise à jour de la version consolidée du 27 octobre 2026. v3 : matériel réseau, protocole, écran, comptage. v4 : règles officielles de la belote classique, tapis supprimé.*

Version 4 — 7 novembre 2026 ; dernière mise à jour : 14 novembre 2026 (v1.7, voir section 13)

Statut : spécification fonctionnelle et protocolaire

Matériel réseau C64 : C64 Ultimate (Ultimate Command Interface, TCP)

## Sommaire

0. Changements des versions 3 et 4

1. Vue d’ensemble

2. Déroulement

3. Touches

4. Joueurs, places et bots

5. Règles de belote

6. Architecture et serveur

7. Protocole

8. Interface, couleurs et sons

9. Tchat

10. Conventions du code

11. Décisions d’arbitrage

12. Reste à faire / questions ouvertes

13. Historique des décisions

*Marques : (v3) = modifié en version 3 ; (v4) = modifié en version 4.*

## 0. Changements des versions 3 et 4

### Version 4 *(v4)*

| Sujet | Changement v4 | Origine |
|---|---|---|
| Règles | Application des règles usuelles de la belote classique : sens du jeu, obligations à l’atout, interdiction de sous-couper, capot, contrat belote comprise. Pas d’annonces (tierce, carré…) : seule la belote-rebelote est annoncée, automatiquement. | Décision |
| Sens du jeu | Jeu et donne dans le sens inverse des aiguilles d’une montre. P1 devient EST et P3 devient OUEST ; les équipes ne changent pas. | Règle |
| À l’atout | Monter est obligatoire même si le partenaire est maître. | Règle |
| Annonces | Aucune annonce de combinaison (tierce, cinquante, cent, carrés). Seule la belote-rebelote existe, annoncée automatiquement par le serveur. | Décision |
| Capot | 252 points pour l’équipe qui fait les 8 plis. | Règle |
| Écran | Tapis central supprimé : chaque carte jouée s’affiche sous le nom de son joueur. Journal agrandi à 6 lignes. | Décision |
| Protocole | Ajout de CAPOT. | Complété |
| Réglages | Adresse serveur saisie sur le C64 ; bots à 1 s ; couleur de nom par place dans le tchat ; F1 : score cible et délai d’inactivité. | Décision |
| Fin de partie | La première équipe qui atteint la cible (1000 par défaut) gagne ; contrôle en fin de manche. Réserve non attribuée perdue. | Décision |

### Version 3 *(v3)*

| Sujet | Changement v3 | Origine |
|---|---|---|
| Matériel réseau | C64 Ultimate retenu. Connexion TCP directe du C64 vers le serveur via l’Ultimate Command Interface. RS232, SwiftLink et modem WiFi abandonnés. | Décision |
| Transport / trames | Protocole texte conservé : une ligne par message, terminée par LF (10), ASCII majuscules, 64 octets maximum. Port 6400. | Complété |
| Écran | Le C64 a 25 lignes : la grille passe de L0–L25 à L0–L24 (suppression de l’ancienne ligne vide L11). | Correction |
| Barre de touches | Libellés raccourcis : chaque barre tient en 39 caractères au plus. | Correction |
| Touche règles | F8 (code 140). La touche HELP n’existe pas sur C64 (elle est propre au C128). | Correction |
| Vue relative | Chaque joueur se voit en SUD. Le client reçoit sa place (BIENVENUE) et fait tourner l’affichage. NOUS/EUX sont relatifs au joueur. | Correction |
| Donne | Donne classique en deux temps : 5 cartes chacun + carte retournée, puis 3 cartes (2 + la retournée pour le preneur). L’ancienne formule « 5 puis 3 à chaque place + retournée » dépassait 32 cartes. | Correction |
| COUP | COUP C envoie le code de carte (0–31) et non plus la position dans la main ; MAIN est renvoyée après chaque changement. | Correction |
| Messages | Ajout de BIENVENUE, SIEGE, DONNEUR, RETOURNE, ENCHERES, TOUR P (diffusé), PREND, PASSE P, REDONNE, BELOTE, REBELOTE, NBCARTES, TAPIS, MANCHE, LITIGE, GAGNANT, INFO, PARAM. | Complété |
| Comptage | Dedans : 162 à la défense, la belote reste à l’équipe qui l’a annoncée. Litige 81–81 : points du preneur en réserve. Points bruts, sans arrondi. | Arbitrage |

## 1. Vue d’ensemble

Le projet est un jeu de belote à quatre places, en réseau, avec un client Commodore 64 écrit en C et compilé avec cc65, et un serveur faisant autorité sous Linux en Python asyncio. Quatre humains au maximum peuvent occuper la table ; les places vacantes ou abandonnées sont jouées par des bots côté serveur. Le tchat est public et intégré à l’écran de jeu. Le client interroge clavier et réseau en alternance, y compris pendant la saisie du tchat.

| Élément | Spécification consolidée |
|---|---|
| Jeu | Belote française à 4 joueurs, deux équipes opposées. |
| Client | Commodore 64, C compilé avec cc65 : affichage, clavier non bloquant et échange réseau en alternance. |
| Client PC *(v1.8)* | Terminal de Windows, macOS ou Linux (pc/belote_lan.py, Python 3.8 ou plus, bibliothèque standard ; belote-lan.exe pour Windows) : même protocole, même table que les C64. |
| Serveur | Serveur Python 3 asyncio sous Linux ; autorité unique sur l’état, les cartes, les règles, le score et les bots. |
| Places / équipes | P0 + P2 contre P1 + P3 ; partenaires face à face. |
| Partie | Plusieurs manches ; score cible par défaut 1000, configurable par le chef de table. |
| Réseau matériel C64 *(v3)* | C64 Ultimate : sockets TCP ouverts par le programme C64 via l’Ultimate Command Interface (registres $DF1C–$DF1F). L’option « Command Interface » doit être activée dans le menu de l’Ultimate. |
| Adresse serveur *(v4)* | Saisie sur le C64 au démarrage (nom d’hôte ou IP, port 6464 par défaut), avec une valeur par défaut fixée à la compilation. Développement : serveur sur le PC du réseau local ; production : VPS Linux. |

## 2. Déroulement

### 2.1 Connexion et attente *(v4)*

Au démarrage, le client affiche l’écran de connexion, qui ne montre que le NOM, centré *(v1.8)*. Le serveur est un réglage un peu caché : F3 remplace le nom par deux champs, IP (hôte ou IP, 29 caractères au plus) et PORT (chiffres, 6464 si vide), pré-remplis avec l’adresse par défaut (SERVEUR_IP et SERVEUR_PORT dans config.mk) ; DEL efface, haut, bas ou RETURN sur l’IP passent d’un champ à l’autre, RETURN sur le port ou F3 revient au nom. Le C64 Ultimate résout lui-même le nom d’hôte. En cas d’échec, le message « CONNEXION IMPOSSIBLE » s’affiche et le nom reste proposé (F3 pour corriger le serveur).

```
L0  BELOTE LAN C64                          V2.0
L5                NOM : JEAN_
L7  (messages : CONNEXION..., CONNEXION IMPOSSIBLE...)
L11            [A♠] [D♥]
L12       [V♣]           [R♥]
L16  4 PLACES : LES BOTS COMPLETENT LA TABLE
L20 ────────────────────────────────────────
L22   FRANCAIS  ENGLISH  DEUTSCH  ESPANOL
L24 RETURN VALIDER  F1 LANGUE  F3 SERVEUR

Après F3 :
L3   IP      :203.0.113.42
L5   PORT    :6464_
```

L’écran reprend la présentation des autres : bandeaux noirs en haut et en bas, trait fin jaune, feutre, cartes de la table, touches sur la barre du bas en gris clair, choix en cours en jaune. Les cartes sont celles de l’écran titre (valet de trèfle, as de pique, puis la belote), distribuées une à une depuis le haut avec la carte qui glisse et son claquement, la première fois seulement ; leurs figures suivent la langue.

**Langue** : F1 passe à la langue suivante (français, anglais, allemand, espagnol) ; chaque nom est écrit dans sa langue, celle en cours en jaune, et les textes de l’écran changent aussitôt. Le choix vaut pour toute la session ; la langue au démarrage se règle à la compilation (`make LANGUE=0..3`). Tout est en majuscules sans accents : le mode couleur étendue n’a que 64 caractères (UE pour Ü, N pour Ñ). Les figures suivent la langue : V D R, J Q K (anglais, espagnol), B D K (allemand). Le protocole ne change pas : ses mots-clés restent en français et le client traduit à l’affichage les messages ERR et INFO qu’il reconnaît (un texte inconnu s’affiche tel quel). Les textes sont dans tools/textes.py, qui génère c64/textes.c et vérifie leurs largeurs. Au joystick (port 2) *(v1.7)* : droite et gauche changent de langue (suivante, précédente), haut et bas passent d’un champ à l’autre dans le réglage du serveur, le bouton vaut RETURN.

Ensuite, le client demande un nom de 6 caractères maximum (A–Z, 0–9) puis rejoint la table. Le serveur attribue une place et la confirme par BIENVENUE. Le premier humain connecté devient chef de table et premier donneur. Les bots occupent les places libres mais ne jouent pas tant que le chef n’a pas lancé la partie avec F2.

### 2.2 Cycle d’une manche *(v4)*

- Première distribution : 5 cartes à chaque place (20 cartes), puis la 21e carte est retournée face visible pour l’ouverture des enchères.

- Deux tours d’enchères selon les règles de belote classique décrites en section 5.

- Seconde distribution : le preneur reçoit la carte retournée et 2 cartes, les trois autres places reçoivent 3 cartes. Chacun a alors 8 cartes (32 au total).

- Huit plis : chaque joueur joue une carte ; le gagnant du pli entame le pli suivant.

- Comptage des points, mise à jour du score cumulé, puis vérification de la fin de partie uniquement en fin de manche.

- Si la partie continue, la manche suivante démarre seule après une pause de 10 secondes (le temps de lire le résultat), avec un compte à rebours sur la ligne d’état ; n’importe quel joueur peut l’écourter avec F5. Le donneur tourne, y compris après une égalité ou une donne annulée.

### 2.3 Fin de partie

Le score cible est 1000 par défaut et peut être modifié par le chef dans les paramètres serveur. Le score affiché est cumulé d’une manche à l’autre. **La première équipe qui atteint ou dépasse la cible gagne la partie** *(v4)*. Le contrôle se fait à la fin de chaque manche, après le comptage complet (jamais au milieu d’une manche, car les points ne sont connus qu’à la fin : dedans, capot, réserve). Si les deux équipes atteignent la cible dans la même manche, la plus haute l’emporte ; en cas d’égalité parfaite, une manche supplémentaire est jouée et le donneur tourne. Des points encore en réserve (litige) à la fin de la partie sont perdus.

```
L0  BELOTE LAN C64         PARTIE TERMINEE
L2
L3
L4  NOUS : 1040
L5  EUX  :  870
L6
L7  VICTOIRE DE NOUS !
L8
L9
L10
L11 F5 = NOUVELLE PARTIE   (CHEF SEULEMENT)
L12 F7 = QUITTER
```

## 3. Touches

La table d’attente réserve F1 aux paramètres serveur. Les règles du jeu se consultent avec F8. F2 lance la partie, F3 ouvre le tchat, F5 passe tout de suite à la manche suivante en fin de manche, sans attendre la fin de la pause (score cumulé conservé, tout joueur) et F7 quitte. Sur l’écran de fin de partie, F5 démarre une nouvelle partie et remet les scores à zéro. Pendant les enchères, 1 à 4 choisissent une option ; pendant le jeu, 1 à 8 jouent les cartes numérotées de la main ; RETURN valide le nom à la connexion. Depuis la v1.7, le joystick en port 2 (ou les flèches et RETURN / ESPACE) permet de tout faire sans clavier : voir les deux dernières lignes du tableau.

| Touche | Code C64 | Action / disponibilité |
|---|---|---|
| F1 | 133 | Écran de connexion : langue suivante. Table d’attente : paramètres de la table, chef seulement : score cible et délai d’inactivité (section 3.1). |
| F2 | 137 | Lancer la partie en attente ; chef seulement. |
| F3 | 134 | Ouvrir le tchat public, saisir puis envoyer un message. À l’écran de connexion : réglage du serveur, IP et PORT (2.1). |
| F4 | 138 | Chef, partie lancée : effacer la partie en cours, après confirmation (O, ou Y, J, S selon la langue). |
| F5 | 135 | Fin de manche : manche suivante sans attendre la fin de la pause, score cumulé conservé (tout joueur). Écran de fin de partie : nouvelle partie, scores remis à zéro (chef seulement). |
| F6 | 139 | Aucune action. |
| F7 | 136 | Quitter la table. |
| F8 *(v3)* | 140 | Afficher / masquer les règles (écran local, la réception réseau continue). HELP n’existe pas sur C64. |
| 1 à 4 | Touches ordinaires | Choix d’enchère, uniquement à son tour d’enchère. |
| 1 à 8 | Touches ordinaires | Jouer la carte portant ce numéro, uniquement à son tour de jeu et si la règle le permet (la carte est sortie du rang). |
| RETURN | 13 | Valider le nom / rejoindre ; envoyer le message de tchat. En jeu *(v1.7)*, comme ESPACE : jouer la carte choisie, valider l’enchère choisie, en fin de manche passer à la suivante. |
| CRSR ← → *(v1.7)* | 157, 29 | En jeu : choisir la carte jouable voisine, ou l’enchère voisine. |
| Joystick, port 2 *(v1.7)* | — | Gauche / droite : comme CRSR ← → (à la connexion : langue). Bouton : comme RETURN (écran titre : lancer). Haut / bas, à la connexion : changer de champ. |

### 3.1 Paramètres F1 *(v4)*

F1 ouvre un petit écran de réglage, réservé au chef pendant l’attente. Deux paramètres, chacun modifiable avec les touches + et −, validés par RETURN, abandon par F1 :

| Paramètre | Défaut | Plage |
|---|---|---|
| Score cible | 1000 | 500 à 5000, par pas de 100 |
| Délai d’inactivité avant remplacement par un bot | 3 min | 1 à 10 min, par pas de 1 |

La réception réseau continue pendant cet écran ; les nouvelles valeurs sont diffusées à tous par PARAM.

### 3.2 Barre de touches (L24) *(v3)*

La barre affichée dépend de l’état et du rôle. Chaque barre fait 39 caractères au plus. Depuis la v1.7, elle est écrite sur un bandeau noir, les touches (F1 à F8, 1-8, 1-4) en jaune et le reste en gris clair.

| Situation | Barre affichée (≤ 39 car.) |
|---|---|
| Chef, en attente | F1 PARAM F2 GO F3 TCHAT F7 QUIT F8 AIDE |
| Autre joueur, en attente | F3 TCHAT F7 QUIT F8 AIDE |
| Enchères, à son tour | 1-4 CHOIX F3 TCHAT F7 QUIT F8 AIDE |
| Jeu, à son tour | 1-8 CARTE F3 TCHAT F7 QUIT F8 AIDE |
| Pas son tour | F3 TCHAT F7 QUIT F8 AIDE |
| Chef, partie lancée | F4 RAZ s'ajoute ; F3 TCHAT devient F3 MSG quand la ligne dépasserait 39 caractères (ex. 1-8 CARTE F3 MSG F4 RAZ F7 QUIT F8 AIDE) |
| Chef, fin de manche | F3 MSG F4 RAZ F5 SUITE F7 QUIT F8 AIDE |
| Autre joueur, fin de manche | F3 TCHAT F5 SUITE F7 QUIT F8 AIDE |
| Chef, fin de partie | F5 NOUVELLE PARTIE F7 QUIT |
| Autre joueur, fin de partie | F7 QUIT |
| Chef, après F4 | EFFACER LA PARTIE ? O OUI, AUTRE NON |
| Saisie du tchat | RETURN ENVOYER  DEL EFFACER  F3 ANNULER |

## 4. Joueurs, places et bots

### 4.1 Sièges et équipes

| Place | Position absolue | Équipe | Ordre de jeu |
|---|---|---|---|
| P0 | SUD | Équipe 0 (P0 + P2) | 1 |
| P1 | EST *(v4)* | Équipe 1 (P1 + P3) | 2 |
| P2 | NORD | Équipe 0 (P0 + P2) | 3 |
| P3 | OUEST *(v4)* | Équipe 1 (P1 + P3) | 4 |

L’ordre de parcours des places est P0 → P1 → P2 → P3 → P0, soit SUD → EST → NORD → OUEST : le jeu tourne dans le sens inverse des aiguilles d’une montre, comme dans la belote classique ; le joueur suivant est toujours à droite. P0 et P2 sont partenaires, de même que P1 et P3. Le serveur place le premier humain en P0 ; les autres sièges libres sont des bots.

**Affichage relatif** *(v3)* — Les positions ci-dessus sont celles du serveur. Chaque client s’affiche lui-même en SUD : la position à l’écran d’une place P vue par le joueur M est r = (P − M + 4) mod 4, avec 0 = SUD, 1 = EST, 2 = NORD, 3 = OUEST. NOUS désigne l’équipe du joueur, EUX l’autre.

### 4.2 Chef de table

- Le premier humain connecté est chef et premier donneur. Il dispose des paramètres F1 et du lancement F2.

- Si le chef quitte ou est remplacé par inactivité, sa place devient un bot et le premier humain restant selon l’ordre P0→P3 devient chef. Si aucun humain ne reste, il n’y a pas de chef et la table attend.

- Après le lancement, le départ de l’ancien chef n’interrompt pas la partie. Le nouveau chef peut lancer une nouvelle partie (F5) en fin de partie ; il ne relance pas la partie en cours.

- La limite est de quatre connexions humaines. Une cinquième connexion (et les suivantes) est refusée par ERR TABLE PLEINE, puis fermée par le serveur ; le C64 affiche « TABLE PLEINE (4 JOUEURS) : PLUS TARD » sur l’écran de connexion. Les bots ne comptent pas comme connexions humaines.
- Limites du serveur *(serveur v2.0)*, toutes tables confondues (prévues pour le multi-salon) : 64 connexions ouvertes au plus, et 8 au plus depuis une même adresse IP (quatre C64 derrière une même box passent). Au-delà, la connexion reçoit ERR TABLE PLEINE dès son ouverture, puis est fermée : les clients déjà publiés le traduisent (« réessayez plus tard »). Options `--max-connexions` et `--max-par-ip`.

### 4.3 Pseudos, remplacement et présence

- Nom affiché : 6 caractères maximum, lettres A–Z et chiffres ; pseudo unique parmi les joueurs. En cas de doublon, le dernier caractère est remplacé par un suffixe numérique (ex. JEAN → JEA2), de 1 à 9 ; sinon la connexion est refusée. Le nom final est renvoyé dans BIENVENUE.

- Noms réservés : BOT et BOT suivi de chiffres (noms des bots : BOT1 à BOT5, BOT12, BOT13… en v2.1). Le C64 les refuse avant de se connecter ; le serveur répond ERR NOM RESERVE sans fermer la connexion, et un suffixe de doublon ne produit jamais un tel nom. Le C64 affiche « NOM RESERVE AUX BOTS : CHOISIR UN AUTRE » et replace le curseur sur le champ NOM.

- Inactivité (3 minutes par défaut, réglable par le chef avec F1) : la place est prise en charge par un bot. Il n’y a pas de spectateurs ; un utilisateur inactif libéré doit se reconnecter. Avant le lancement *(serveur v2.0)*, un humain qui n’envoie rien pendant 10 minutes (`--delai-attente`, en secondes) rend sa place de la même façon, avec les mêmes messages : une table d’attente ne peut plus être gardée par des connexions muettes. Chaque table le vérifie pour elle-même.

- À la reconnexion, l’utilisateur retrouve sa place et la main encore tenue par le bot si cette place est toujours disponible. Si elle est occupée par un autre humain, une place bot libre est attribuée ; s’il n’y en a aucune, la reconnexion est refusée.

- Connexion fantôme : un C64 redémarré (reset, nouveau programme) n’envoie pas LEAVE et son ancienne connexion TCP peut rester ouverte. Un JOIN portant le nom d’un humain encore assis, depuis la même adresse IP, reprend sa place : l’ancienne connexion est fermée, le client reçoit BIENVENUE et l’état complet, les autres joueurs un INFO NOM RECONNECTE. Depuis une autre adresse, la règle des doublons s’applique.

- Déconnexion explicite ou perte de connexion pendant le tour : le bot joue immédiatement, sans attendre les 3 minutes. Il conserve la main en cours ; une reprise ultérieure récupère l’état actualisé (voir 7.4).

### 4.4 Stratégie des bots

Les bots sont calculés par le serveur et n’agissent qu’après le lancement. Ils jouent toujours un coup légal (section 5.3) *(v2.0)* :

- **Enchères** : la main est estimée pour chaque atout possible, retournée comprise (valet 20, 9 14, as 11, 10 10, roi 4, dame 3, 8 et 7 2 ; as hors atout 10, 10 hors atout gardé par son as 5, belote 10). Le bot prend si elle vaut au moins 32 : au premier tour à la couleur de la retournée, au second à la meilleure des trois autres ; sinon il passe.
- **Preneur** : à l’entame, il fait tomber les atouts adverses avec son atout maître tant qu’il en reste dehors, ou avec son plus petit atout s’il en a au moins trois.
- **Entame** : sinon, la plus forte carte restante d’une couleur hors atout (l’as, ou le 10 une fois l’as tombé) : il se souvient des cartes déjà jouées dans la donne.
- **Adversaire maître** : la plus petite carte qui gagne, sinon la plus faible.
- **Partenaire maître** : s’il joue en dernier, ou si la carte du partenaire ne peut plus être battue dans sa couleur, il le charge (son 10 ou son as hors atout) ; sinon il joue sa carte la plus faible.

- **Cartes (PIMC)** *(v2.1)* : quand `--pimc N` est actif (2 par défaut), le bot choisit sa carte en simulant la fin de la donne : pour chaque carte jouable, 100 répartitions plausibles des cartes cachées (couleurs manquantes déduites des plis, retournée chez le preneur), terminées par la stratégie simple ci-dessus ; il garde la carte au meilleur écart de points moyen. Le calcul tourne dans N processus (la boucle du serveur reste libre) ; au-delà de 3 s ou en cas d'erreur, la stratégie simple joue. `--pimc 0` la rétablit seule. Mesuré (`tools/pimc.py`) : environ 56 % des points contre la stratégie simple. Les enchères PIMC n'apportent que 0,8 point de part (seuil 5) : non retenues.

- **Styles** *(v2.1)* : chaque bot a un style, tiré au sort à chaque nouvelle partie, à chaque RAZ (demande de Stéphan) et quand il remplace un humain, jamais deux fois le même nom à une table. Le style règle le seuil de prise et l'objectif du PIMC : attaquant (BOT1, seuil 26, vise les grosses manches), défenseur (BOT2, seuil 34, vise à gagner la manche), modéré (BOT3, seuil 32, écart de points), adaptatif (BOT4 : attaque s'il est mené de 150 points ou si l'adversaire approche de la cible, se défend s'il mène de 150 points), feinteur (BOT5, comme le modéré, mais joue parfois une carte presque aussi bonne que la meilleure et autre que celle qu'on attendrait, jamais quand son partenaire tient le pli). Variantes : BOTx pour la première, BOTx2 et BOTx3 pour les autres ; elles décalent les seuils de -2, 0 et +2 (15 noms en tout). Mesuré avec `tools/styles.py` : les styles sont à égalité en tables tirées au hasard (49 à 51 % de victoires). `--sans-styles` rétablit des bots tous nommés BOT, qui jouent comme le modéré.

Ces choix sont mesurés avec `tools/duel_bots.py` (chaque donne jouée deux fois, équipes échangées) : 53,9 % des points contre les bots de la v1.8 sur 200 000 donnes. Plus prudents aux enchères, quatre bots passent tous dans 18 % des donnes (redistribuées). Chaque action d’un bot (enchère ou carte) est jouée après un délai fixe de **1 seconde** *(v4)*, pour que les joueurs puissent suivre.

### 4.5 Salons *(v2.0)*

Le serveur a plusieurs tables indépendantes, les salons, numérotés de 1 à 9 (9 par défaut, `--salons N` au lancement). Chaque salon a ses sièges, son chef, sa partie, ses bots, son tchat et sa propre vérification d’inactivité ; les limites de connexions (4.3) valent pour le serveur entier.

- Avant JOIN, une connexion peut demander la liste : `SALONS` reçoit `SALONS N`, puis une ligne `SALON I H ETAT` par salon (humains assis, état de sa table). Elle a alors 5 minutes pour choisir, au lieu des 60 secondes d’une connexion sans JOIN.
- `JOIN NOM I` rejoint le salon I ; `JOIN NOM` sans numéro rejoint le salon 1, ce que font les clients d’avant la v2.0, qui continuent donc de marcher. Le nom n’est unique que dans son salon.
- Salon choisi plein : `ERR TABLE PLEINE`, et la connexion reste ouverte pour en choisir un autre ; numéro invalide : `ERR SALON`. Un JOIN sans numéro sur un salon 1 plein est refusé puis fermé, comme avant.
- Le C64 et le client PC demandent la liste après la connexion et l’affichent (numéro, joueurs sur 4, ATTENTE ou EN JEU) ; on choisit aux flèches, au joystick ou avec un chiffre, RETURN entre, F7 (Échap sur PC) revient au nom. Un serveur sans salons répond ERR à SALONS : le client envoie alors JOIN sans numéro.
- Console du serveur : `RAZ` efface la partie de chaque salon, `RAZ N` celle du salon N.

## 5. Règles de belote

### 5.1 Paquet, codes et ordre

Jeu de 32 cartes : 7, 8, 9, 10, Valet, Dame, Roi, As dans les quatre couleurs. Carte C = COULEUR × 8 + RANG ; couleur 0=♠, 1=♥, 2=♣, 3=♦ ; rang 0=7, 1=8, 2=9, 3=10, 4=V, 5=D, 6=R, 7=A. Les cartes sont codées de 0 à 31.

| Contexte | Ordre de force (faible → fort) | Points |
|---|---|---|
| Sans atout | 7, 8, 9, V, D, R, 10, A | 7/8/9 = 0 ; V=2 ; D=3 ; R=4 ; 10=10 ; A=11 |
| À l’atout | 7, 8, D, R, 10, A, 9, V | 7/8=0 ; D=3 ; R=4 ; 10=10 ; A=11 ; 9=14 ; V=20 |

Le tri des couleurs dans la main est pique, cœur, trèfle, carreau (0, 1, 2, 3). Les valeurs d’atout remplacent les valeurs non-atout du Valet et du 9.

### 5.2 Donne et enchères *(v4)*

- Le premier donneur est le premier humain connecté. À chaque manche suivante, le donneur avance d’une place (vers sa droite) ; cela vaut aussi après égalité et après une donne annulée.

- Le serveur mélange le paquet à chaque donne (la coupe par le joueur de gauche n’a pas d’effet en ligne).

- Première distribution, en commençant par le joueur à droite du donneur : 3 cartes puis 2 cartes à chaque place (5 cartes). La 21e carte est retournée et propose l’atout.

- Premier tour : chacun, à partir du joueur à droite du donneur, peut prendre la couleur de la carte retournée ou passer. Si personne ne prend, second tour : chacun peut choisir une des trois autres couleurs ou passer.

- Dès qu’un joueur prend, les enchères s’arrêtent : l’atout et l’équipe preneuse sont fixés. Le preneur reçoit la carte retournée et 2 cartes ; les autres reçoivent 3 cartes.

- Si tous passent pendant les deux tours, la donne est annulée (REDONNE) et redistribuée par le donneur suivant.

### 5.3 Jeu et légalité des coups *(v4)*

Le joueur à droite du donneur entame le premier pli. Le gagnant d’un pli entame le suivant ; il y a huit plis. Un pli est gagné par l’atout le plus fort ou, sans atout, par la carte la plus forte de la couleur demandée.

| Situation | Obligation |
|---|---|
| Couleur demandée (non atout), le joueur en a | Fournir la couleur demandée (n’importe quelle carte de cette couleur). |
| Atout demandé | Fournir de l’atout et monter (jouer un atout plus fort que le plus fort déjà posé) si possible, même si le partenaire est maître. Sans atout plus fort : atout inférieur. Sans atout : défausse libre. |
| Couleur demandée absente, partenaire maître | Libre : défausse ou atout. |
| Couleur demandée absente, adversaire maître | Couper (jouer atout) obligatoire si possible. Si un adversaire a déjà coupé, surcouper si possible. |
| Impossible de surcouper *(v2.1)* | Jouer quand même un atout inférieur (sous-couper, « pisser »), comme dans la règle classique. Jusqu’à la v2.0, la sous-coupe était interdite (défausser une autre couleur) : le serveur accepte encore cette défausse pour ne pas bloquer les clients v2.0, mais les clients et les bots jouent l’atout. |
| Aucune carte de la couleur ni d’atout | Défausse libre. |

Le serveur vérifie le tour, la carte en main et ces obligations ; en cas de refus, il renvoie ERR COUP REFUSE et attend une nouvelle action du même joueur. Le client peut griser les cartes interdites, mais le serveur fait foi.

### 5.4 Belote-rebelote *(v4)*

Le joueur qui possède le Roi et la Dame d’atout marque 20 points. Le serveur annonce automatiquement « belote » à la pose de la première de ces cartes, puis « rebelote » à la pose de la seconde ; le joueur n’a rien à faire. Ces 20 points restent toujours à l’équipe qui les annonce, même si elle est dedans.

**Pas d’autres annonces** : les tierces, cinquantes, cents et carrés ne sont pas joués.

### 5.5 Points et contrats *(v4)*

Total des points des cartes : 152, plus 10 points de dernier pli (dix de der) : 162 points par manche, plus 20 points de belote-rebelote éventuelle.

| Cas | Règle retenue |
|---|---|
| Contrat rempli | Le preneur fait strictement plus de points que la défense, cartes + dix de der + belote comprises (82 sur 162 sans belote). Chaque équipe marque ses points. |
| Dedans | Le preneur fait moins que la défense : la défense marque 162 (+ sa propre belote éventuelle). Le preneur marque 0, plus sa belote-rebelote s’il l’a annoncée. |
| Litige (égalité) | La défense marque ses points. Les points du preneur sont mis en réserve et vont à l’équipe qui remporte la manche suivante (preneur qui réussit, ou défense si le preneur est dedans). Une donne annulée ne solde pas la réserve. |
| Capot | L’équipe qui remporte les 8 plis marque 252 points (au lieu de 162) + sa belote ; l’autre marque seulement sa belote éventuelle. Si c’est la défense qui fait capot, le preneur est dedans. |
| Arrondi | Aucun : les points sont ajoutés bruts au score cumulé. |

Le score de la manche (MANCHE) et le score cumulé (SCORE) sont transmis après le huitième pli.

## 6. Architecture et serveur

### 6.1 Stack technique

- **Serveur** — Python 3 asyncio sous Linux : asyncio.start_server sur le port 6464, une coroutine par client, état de partie centralisé, protocole texte ligne par ligne (StreamReader.readline()).

- **Client** — C pour C64 compilé avec cc65 (cl65 -t c64) ; écran 40×25 en mode couleur étendue (ECM) écrit directement en mémoire ($C000, caractères en $C800) ; boucle principale non bloquante alternant clavier (GETIN du KERNAL, cbm_k_getin) et réseau, afin de continuer à recevoir pendant la saisie. Deux sprites pour la carte qui glisse et le pli ramassé (8.1) ; écran titre en bitmap multicolore ; musique et bruitages sur le SID (8.3).

- **Client PC** *(v1.8)* — Un seul fichier Python (pc/belote_lan.py) : un fil lit le réseau, un autre le clavier (msvcrt sous Windows, termios ailleurs), la boucle principale tient l’état de la partie à partir des messages (classe Partie, sans affichage, testée contre le vrai serveur) et redessine une grille 80×24 en séquences ANSI (16 couleurs). Mêmes règles que le C64 : vue relative, cartes jouables (coups_legaux recopié du serveur), PASSE proposé d’abord aux enchères, dernière carte jouée seule, pause de fin de manche. belote-lan.exe est fabriqué par PyInstaller dans GitHub Actions (.github/workflows/client-windows.yml) et joint à chaque release publiée.

- **Réseau C64** *(v3)* — Ultimate Command Interface du C64 Ultimate, cible réseau : ouverture d’une connexion TCP, puis lectures non bloquantes à chaque passage de boucle. Le client accumule les octets jusqu’au LF, puis traite la ligne.

- **Encodage** *(v3)* — Le réseau transporte de l’ASCII. En mode majuscules/graphiques, les lettres A–Z ont les mêmes codes en ASCII et en PETSCII. cc65 convertirait les littéraux pour la cible c64 : c64/ascii.h lui impose l’identité pour $40–$5F, si bien que littéraux, clavier et réseau parlent le même code, sans conversion à l’émission ni à la réception.

### 6.2 Répartition des responsabilités

| Serveur Linux (Python 3 asyncio) | Client C64 (C / cc65) |
|---|---|
| asyncio.start_server ; coroutine par client ; état de partie centralisé et protocole texte ligne par ligne. | Affiche la table et sa propre main uniquement, en vue relative (lui-même en SUD). |
| Distribue, gère les enchères, valide les coups et compte les points. | Reçoit et interprète les messages ; transmet choix de touches et tchat. |
| Joue les bots et agit immédiatement lors d’une déconnexion pendant le tour. | Ne reçoit jamais les cartes cachées des autres places. |
| Gère les connexions, le chef, les états, les temporisations et la diffusion sélective. | Boucle non bloquante : interroge clavier et réseau en alternance ; la réception continue pendant la saisie du tchat. |

Le serveur est l’autorité unique ; les mains adverses ne sont jamais envoyées aux clients. Un client reçoit sa main privée, le nombre de cartes restant aux autres, les cartes jouées et les événements de table publics.

### 6.3 États de la table

| État | Signification |
|---|---|
| ATTENTE | Table ouverte ; humains rejoignent/quittent ; bots immobiles ; seul le chef peut lancer. |
| LANCEE | Lancement accepté ; la première manche démarre. |
| EN COURS | Enchères ou jeu d’une manche en cours. |
| FIN MANCHE | Résultat publié ; la manche suivante démarre seule après 10 secondes (SUITE), ou plus tôt sur F5 de n’importe quel joueur. Sans humain à la table, elle attend le prochain arrivé. |
| FIN PARTIE *(v3)* | La cible est atteinte en fin de manche ; gagnant affiché. F5 (chef) démarre une nouvelle partie, scores remis à zéro. |

### 6.4 Données conceptuelles historiques

```
PT(P) = 0 bot / 1 humain, P=0..3
PN$(P) = nom affiché
MAIN(P,K) = carte, K=1..8 ; -1 si jouée
NMAIN(P) = nombre de cartes restantes
DONNEUR = place du donneur ; CHEF = place chef, -1 si aucun
ATOUT, PRENEUR, ENTAMEUR, PLI(P), RETOURNEE
BELOTE(P)
POINTS(E), SCORE(E), RESERVE ; E=0 : P0+P2, E=1 : P1+P3
```

## 7. Protocole *(v3)*

### 7.1 Transport et cadrage

| Point | Règle |
|---|---|
| Transport | TCP, port 6464. Une connexion par client. Une connexion sans place à la table 60 s après son ouverture (pas de JOIN accepté) est fermée par le serveur. |
| Trame | Une ligne par message, terminée par LF (code 10). Un CR éventuel avant le LF est ignoré. |
| Champs | Mot-clé en majuscules, puis paramètres séparés par une espace. Pour TCHAT, INFO et ERR, le texte est le reste de la ligne. |
| Encodage | ASCII 32–95 (majuscules, chiffres, ponctuation). Le serveur met en majuscules et remplace tout autre caractère par « ? ». |
| Longueur | 64 octets maximum, LF compris. Le serveur ignore une ligne plus longue (ERR TROP LONG). |
| Valeurs | Places 0–3 (absolues), cartes 0–31, couleurs 0–3, équipes 0–1, nombres en décimal. |
| Erreurs | Une action refusée reçoit ERR TEXTE ; l’état du serveur ne change pas. |

### 7.2 Serveur → client

| Message | Audience | Sens / données |
|---|---|---|
| BIENVENUE NOM P *(v3)* | Client | Connexion acceptée : nom final (éventuellement modifié) et place P. |
| SIEGE P T NOM *(v3)* | Tous | Occupant de la place P : T = H (humain) ou B (bot). Remplace TABLE P0 P1 P2 P3. Envoyé pour les 4 places à la connexion et à chaque changement. Le NOM d’un bot est celui de son style (BOT1, BOT12… *(v2.1)*) ; un serveur v2.0 envoie BOT. |
| CHEF P | Tous | Place du chef, 0..3 ; -1 si aucun. |
| ETAT X | Tous | ATTENTE, LANCEE, EN COURS, FIN MANCHE ou FIN PARTIE. |
| PARAM CIBLE N *(v3)* | Tous | Score cible actuel. |
| PARAM INACTIF M *(v4)* | Tous | Délai d’inactivité actuel, en minutes. |
| DONNEUR P *(v3)* | Tous | Donneur de la manche. |
| MAIN C1 .. Cn | Client | Sa main complète (n ≤ 8), triée. Renvoyée après chaque distribution et chaque coup accepté. |
| NBCARTES N0 N1 N2 N3 *(v3)* | Tous | Nombre de cartes de chaque place (après distribution et à la reconnexion). |
| RETOURNE C *(v3)* | Tous | Carte retournée pour les enchères. |
| ENCHERES T *(v3)* | Tous | Début du tour d’enchères T (1 ou 2). |
| TOUR P *(v3)* | Tous | C’est à la place P d’agir (enchère ou carte selon la phase). Diffusé à tous. |
| PREND P C *(v3)* | Tous | La place P prend ; l’atout est la couleur C. |
| PASSE P *(v3)* | Tous | La place P passe. |
| REDONNE *(v3)* | Tous | Tout le monde a passé : donne annulée. |
| JOUE P C | Tous | La place P a joué la carte C. |
| BELOTE P / REBELOTE P *(v3)* | Tous | Annonce automatique à la pose du Roi ou de la Dame d’atout. |
| PLI P | Tous | La place P gagne le pli. |
| PLICOURS C0 C1 C2 C3 *(v4)* | Client | Cartes du pli en cours par place (-1 = pas encore jouée) ; à la reconnexion. Remplace TAPIS. |
| CAPOT E *(v4)* | Tous | L’équipe E a remporté les 8 plis. |
| MANCHE E0 E1 *(v3)* | Tous | Points de la manche de l’équipe 0 (P0+P2) et de l’équipe 1 (P1+P3). |
| LITIGE N *(v3)* | Tous | N points mis en réserve (litige). |
| RESERVE N *(v2.1)* | Tous | Réserve en attente (0 : plus de réserve), après un litige, quand elle est remportée, à la nouvelle partie, et à l’arrivée d’un joueur (après SCORE). Le client l’affiche dans l’en-tête (RES 81 à la place de BELOTE). Les clients v2.0 l’ignorent. |
| SCORE E0 E1 | Tous | Score cumulé par équipe absolue ; le client affiche NOUS/EUX selon sa place. |
| GAGNANT E *(v3)* | Tous | Équipe gagnante de la partie. |
| SUITE S | Tous | Après ETAT FIN MANCHE (et à la reconnexion pendant la pause) : la manche suivante démarre dans S secondes. Un client qui ne connaît pas ce message l’ignore. |
| TCHAT NOM TXT | Tous | Message public, nom et contenu. |
| INFO TXT *(v3)* | Client ou tous | Information affichée dans le journal (pseudo modifié, joueur remplacé par un bot, etc.). Textes fixes, que le client reconnaît pour les traduire : NOM CHANGE EN NOM, NOM RECONNECTE, NOM REMPLACE PAR UN BOT, NOM INACTIF REMPLACE PAR UN BOT, INACTIF : PLACE RENDUE AU BOT, PARTIE EFFACEE, RESERVE N POUR EQUIPE E. |
| ERR TEXTE | Client | ERR CHEF SEUL, ERR TABLE PLEINE, ERR PAS TON TOUR, ERR COUP REFUSE, ERR DEJA LANCEE, ERR PAS LANCEE, ERR NOM, ERR NOM RESERVE, ERR PARAM, ERR INCONNU, ERR TROP LONG (détail dans protocol.fr.md). Le client les affiche traduits dans le journal (« REFUS : … »). |

### 7.3 Client → serveur

| Message | Déclencheur | Sens / contrôle serveur |
|---|---|---|
| SALONS *(v2.0)* | Après la connexion | Liste des salons : SALONS N, puis SALON I H ETAT par salon (4.5). |
| JOIN NOM [I] | RETURN après saisie du nom (et choix du salon) | Rejoindre ; nom de 6 caractères maximum, unicité appliquée côté serveur ; I : salon (1 sans numéro). |
| LANCER | F2 | Chef seulement, en ATTENTE ; sinon ERR CHEF SEUL ou ERR DEJA LANCEE. |
| PARAM CIBLE N *(v3)* | F1 puis réglage | Chef seulement, en ATTENTE ; N de 500 à 5000. |
| PARAM INACTIF M *(v4)* | F1 puis réglage | Chef seulement, en ATTENTE ; M de 1 à 10 minutes. |
| ENCH C | Touches 1–4 en enchères | Prendre à la couleur C. Au tour 1, C doit être la couleur retournée ; au tour 2, une autre couleur. |
| PASSE | Touche d’enchère PASSE | Passer. |
| COUP C *(v3)* | Touche 1–8 | Jouer la carte de code C (le client traduit le numéro affiché en code). Valide seulement à son tour. Au dernier pli, le client l’envoie seul (8.1). |
| TCHAT TXT | F3, saisie, RETURN | Message public, tronqué à 30 caractères par le client et le serveur ; au plus 3 messages par 10 s, les suivants sont ignorés. |
| REJOUER | F5 | Tout joueur en FIN MANCHE : manche suivante sans attendre la fin de la pause. Chef seulement en FIN PARTIE : nouvelle partie. |
| RAZ | F4 puis O (Y, J, S selon la langue) | Chef seulement, partie lancée : efface la partie (scores, réserve, places réservées) et revient en ATTENTE ; les clients reçoivent INFO PARTIE EFFACEE, SCORE 0 0, ETAT ATTENTE. Sinon ERR CHEF SEUL ou ERR PAS LANCEE. |
| LEAVE | F7 | Quitter ; la place est transférée à un bot. |

### 7.4 Séquences

**Connexion et lancement**

```
C64 -> srv : JOIN JEAN
srv -> C64 : BIENVENUE JEAN 0
srv -> tous: SIEGE 0 H JEAN / SIEGE 1 B BOT12 / SIEGE 2 B BOT4 / SIEGE 3 B BOT3
srv -> tous: CHEF 0 / ETAT ATTENTE / PARAM CIBLE 1000 / PARAM INACTIF 3
chef-> srv : LANCER
srv -> tous: ETAT LANCEE / SCORE 0 0
```

**Une manche**

```
srv -> tous: ETAT EN COURS / DONNEUR 0
srv -> chacun: MAIN c1..c5          (privé)
srv -> tous: NBCARTES 5 5 5 5 / RETOURNE 12 / ENCHERES 1
srv -> tous: TOUR 1 / PASSE 1 / TOUR 2 / PREND 2 1
srv -> chacun: MAIN c1..c8          (privé)
srv -> tous: NBCARTES 8 8 8 8 / TOUR 1
P1  -> srv : COUP 14
srv -> tous: JOUE 1 14 / TOUR 2 ...
            (srv -> P1 : MAIN ...)
srv -> tous: PLI 3 / TOUR 3 ...   (x 8 plis)
srv -> tous: MANCHE 72 110 / SCORE 72 110 / ETAT FIN MANCHE / SUITE 10
            (10 s plus tard, ou plus tôt : P2 -> srv : REJOUER)
srv -> tous: ETAT EN COURS / DONNEUR 1 ...
```

**Reconnexion** — après BIENVENUE, le serveur envoie l’état complet : SIEGE ×4, CHEF, ETAT, PARAM, SCORE, DONNEUR, GAGNANT en FIN PARTIE, puis selon la phase RETOURNE ou PREND, MAIN, NBCARTES, PLICOURS et TOUR.

## 8. Interface, couleurs et sons

### 8.1 Grille écran de référence *(v4)*

Grille de 40 colonnes (0–39) et 25 lignes (L0–L24). Le tapis central est supprimé : la carte jouée par chaque joueur s’affiche sous son nom. Un bot porte le nom de son style (BOT1, BOT12… *(v2.1)*, voir 4.4), envoyé par le serveur, sur la table comme dans le journal : le même nom sur tous les écrans. Avec un serveur v2.0, qui appelle tous les bots BOT, le client les nomme BOT1 à BOT4 d’après leur place réelle (P0 à P3). Les noms, points et cartes sont des exemples (le joueur est en P0). La table est symétrique *(v1.8)* : cartes de l’OUEST et de l’EST à quatre colonnes du bord (4 à 7, 32 à 35), noms alignés sur le bord extérieur de leur carte, noms du NORD et du SUD centrés sur la leur.

```
    0         1         2         3
    0123456789012345678901234567890123456789
L0  BELOTE   ATOUT: ♥    NOUS 0000 EUX 0000
L2                    BOT3
L3                    [D ]
L4                    [♥ ]
L5      BOT4                        BOT2
L6      [R ]                        [10]
L7      [♣ ]                        [♦ ]
L8  
L9  
L10                   JEAN
L11 ────────────────────────────────────────
L12 BOT3 : PASSE
L13 BOT2 : PREND A D♥
L14 BOT2 : BELOTE
L15 LEA  : BIEN JOUE !
L16 BOT2 : REBELOTE
L17 BOT2 : REMPORTE LE PLI
L18 VOUS : _
L19 A VOUS DE JOUER : 1-8 OU JOYSTICK
L20 [V ] [9 ] [D ] ──────────────────────
L21 [♠ ] [♠ ] [♠ ] [10] [7 ] [R ]
L22                [♦ ] [♦ ] [♥ ]
L23  1    2    3    4    5    6
L24 1-8 CARTE F3 TCHAT F7 QUIT F8 AIDE
```

**Zone de jeu (L2–L10)** : nom de chaque joueur à sa position relative (NORD = partenaire, EST = à droite, OUEST = à gauche, SUD = soi). Sous chaque nom, la carte qu’il a jouée dans le pli en cours, ou rien ; un pli terminé est ramassé vers son gagnant (8.1). Le tour se lit à la carte qui arrive et à la ligne d’état (plus d’astérisque devant le nom). Les mains adverses ne sont pas dessinées. Les humains sont désignés par leur nom (suivi de « (CHEF) » en attente), les bots par le nom de leur style (BOT1, BOT12… *(v2.1)*), identique pour tous les joueurs. Au centre (L5–L7) : pendant les enchères, la carte retournée sous « RETOURNEE » ; après la prise, la carte prise sous « PRISE », jusqu’à la première carte jouée.

**Journal (L12–L17)** : six lignes pour les enchères, belote-rebelote, plis, tchat et INFO ; un événement de joueur tient en 33 caractères après « NOM  : », un message du serveur prend toute la ligne (40) ; les nouveaux événements remplacent les plus anciens. **L18** sert à la saisie du tchat. De L12 à L19, entre les deux traits jaunes, le fond est un vert uni, sans les points du feutre *(v2.0)*.

**L19** est la ligne d’état. En attente : « CHEF : <NOM>   CIBLE : 1000 POINTS ». Au jeu, à son tour : « A VOUS DE JOUER : 1-8 ». En fin de manche : « MANCHE POUR NOUS - SUITE DANS 10 S » ou « MANCHE POUR EUX - … », selon l’équipe qui a marqué le plus de points, dans la couleur claire de cette équipe (bleu clair ou rouge clair), décompté chaque seconde (avec un serveur sans SUITE, plus ancien : « MANCHE TERMINEE : F5 POUR LA SUIVANTE » pour le chef, « … : ON ATTEND LE CHEF » pour les autres). Pendant les enchères, premier tour : « [1 PRENDRE <couleur retournée>] [2 PASSE] ». Second tour : les 3 autres couleurs puis PASSE (ex. « [1 ♠] [2 ♣] [3 ♦] [4 PASSE] »). Au tour d’un autre joueur : « ENCHERES : AU TOUR DE <NOM>... ». À droite de la ligne, le tour d’enchères en cours (« 1ER TOUR » ou « 2E TOUR », jusqu’à la colonne 38 comme les choix partent de la colonne 1 *(v2.0)*), car le journal ne montre pas toujours les passes du premier tour. Le joueur concerné utilise les touches 1 à 4.

**Main (L20–L23)** *(v1.7)* : jusqu’à 8 cartes numérotées de 1 à 8, dans l’ordre du serveur (pique, cœur, trèfle, carreau). À son tour de jeu, les cartes que la règle permet de jouer sortent du rang (lignes L20–L21, par-dessus le trait) ; le client applique pour cela les règles du serveur (section 5.3), qui reste juge. La carte choisie au joystick ou aux flèches a son numéro en noir sur fond blanc ; les autres numéros jouables sont jaunes, les autres gris clair, et gris foncé hors de son tour. L0, sur le bandeau noir : BELOTE en jaune, l’atout dans sa couleur (? pendant les enchères), puis NOUS et EUX dans la couleur de chaque équipe et le score cumulé sur 4 chiffres.

**Enchères au joystick** *(v1.7)* : en L19, les choix sont des étiquettes (« 1 PRENDRE ♥ », « 2 PASSE » ; au second tour les trois couleurs et « 4 PASSE ») ; celle choisie est sur fond blanc. Le choix repart sur PASSE à chaque tour d’enchères, pour qu’un appui involontaire ne fasse jamais prendre.

**Fin de manche** *(v1.7)* : une grande carte blanche aux coins arrondis, posée au centre du tapis (cases 10 à 29, lignes 3 à 9) : LA MANCHE, les points de chaque équipe (bleu ou rouge foncé), CONTRAT REMPLI, DEDANS !, CAPOT !, LITIGE : RES. N (réserve en attente) ou +N DE RESERVE (réserve remportée, v2.1) dans la couleur de l’équipe concernée, puis AU TOTAL et les scores. Elle reste pendant le compte à rebours ; le bouton du joystick (ou RETURN) fait comme F5.

**Carte qui glisse** : chaque carte jouée (JOUE) glisse jusqu’à sa place sur le tapis en 14 images (environ un quart de seconde), dessinée par deux sprites : le corps blanc aux coins arrondis (sprite 1, élargi) et, devant, le rang et le symbole dans la couleur de la carte (sprite 0) ; données en $C400. Sa propre carte part de son emplacement dans la main (retenu à la réception de JOUE, avant la MAIN qui suit) ; celle du partenaire du haut de l’écran, celles des adversaires du bord droit (EST) ou gauche (OUEST). Pendant ce quart de seconde, le client ne lit pas le réseau : les messages attendent dans l’Ultimate. La table et la main sont redessinées sur place, sans être effacées d’abord : rien ne clignote.

**Pli ramassé** : à la réception de PLI, le pli complet reste visible une demi-seconde, puis les cartes rejoignent le centre du tapis une par une (10 images chacune *(v2.0)*), dans l’ordre des places qui suivent le gagnant, la sienne en dernier, sur le dessus du paquet. Le paquet part ensuite en accélérant vers le gagnant : jusqu’à son nom pour soi (16 images), hors de l’écran par le haut pour le partenaire, par la droite (EST) ou la gauche (OUEST) pour les adversaires (28 images). Une seule carte bouge à la fois, avec les deux sprites de la carte qui glisse ; les cartes déjà réunies sont en texte au centre. Le bruitage du pli (un glissement) part avec le paquet. Le client ne lit pas le réseau pendant ces 2 s environ ; les bots attendent au moins 1 s avant de jouer.

**Dernier pli** : la dernière carte est jouée automatiquement une demi-seconde après le TOUR du joueur (un seul COUP par carte).

### 8.2 Couleurs C64

| Zone / élément | Valeur retenue | Rendu |
|---|---|---|
| Plateau | Vert C64 = 5 | Fond vert ; les cases vides portent un motif de feutre (points vert clair = 13, le caractère # redessiné), sauf le journal et le tchat (L12–L19), en vert uni *(v2.0)*. |
| Bordure *(v1.7)* | Brun C64 = 9 | Le cadre de la table (le vert, puis le noir et le gris foncé ont été essayés). |
| Bandeaux *(v1.7)* | Fond noir (ECM, $D023 = 0) | L0 (titre, atout, scores) et L24 (touches en jaune). Sur le noir, ♥ ♦ en rouge clair, ♠ ♣ en blanc. |
| Séparations *(v1.7)* | Jaune C64 = 7 | Trait fin continu (le caractère < redessiné, 2 pixels) en L11 et L20, au lieu des tirets. |
| Cartes | Fond blanc (ECM, $D022 = 1), coins arrondis | Rang et symbole dans la couleur de la carte. Les coins sont quatre caractères redessinés (" $ % &) : un arc de 2 pixels en vert du plateau. |
| Cœurs et carreaux | Rouge C64 = 2 | Rang et symbole rouges sur la carte blanche. |
| Piques et trèfles | Noir C64 = 0 | Rang et symbole noirs sur la carte blanche. |
| RAM couleur | Adresse $D800 | Attributs couleur des cellules écran. |

Codes de couleur par couleur de carte : FC(0)=0, FC(1)=2, FC(2)=0, FC(3)=2.

### 8.3 Sons

Le client joue la musique et les bruitages sur le SID, uniquement à partir des messages déjà reçus : le serveur et le protocole n’en savent rien.

| Moment | Déclencheur | Son |
|---|---|---|
| Écran titre | affichage de l’image, jusqu’à la touche | Valse musette originale à 3 voix, en boucle : mélodie d’accordéon (impulsion qui respire, léger vibrato rapide qui imite le battement des anches musette), basse grave, accords arpégés. |
| Carte posée | JOUE (tout joueur) | Claquement court (bruit). |
| Pli ramassé | PLI | Toc grave et feutré (triangle) pour chaque carte réunie au centre, puis glissement de cartes quand le paquet part vers le gagnant (8.1). |
| Tchat | TCHAT (tout message de joueur) | Deux notes claires. |
| Partie gagnée | GAGNANT, équipe du joueur | Fanfare montante. |
| Partie perdue | GAGNANT, équipe adverse | Descente qui finit en mineur. |

Le lecteur (c64/son.s) tourne dans l’interruption du KERNAL, 60 fois par seconde, donc aussi pendant les commandes réseau. Les airs utilisent les voix 1 à 3 et les bruitages la voix 3 : un bruitage demandé pendant qu’un autre joue attend la fin de celui-ci. Notes, durées et enveloppes sont écrites dans tools/musique.py, qui génère c64/son_donnees.s.

## 9. Tchat

- Public uniquement : aucun tchat privé. Ouverture par F3, envoi par RETURN.

- Nom affiché limité à 6 caractères (5 jusqu’à la v1.5, dont le client tronque un nom plus long). Texte limité à 30 caractères : le client limite la saisie et le serveur tronque par sécurité.

- Anti-inondation : au plus 3 messages par joueur sur 10 secondes ; le serveur ignore les suivants, sans réponse.

- Le message est diffusé à tous via TCHAT NOM TXT et affiché dans le journal L12–L17 ; saisie en L18.

- La saisie du tchat n’interrompt pas la réception réseau : la boucle principale vérifie le clavier de façon non bloquante (GETIN du KERNAL) et traite les données réseau en alternance.

- Couleur du nom, sur la table et dans le journal : une couleur fixe par place, la même sur tous les écrans, en deux nuances par équipe : P0 bleu clair (14) et P2 bleu (6) pour l’équipe P0+P2 ; P1 rouge clair (10) et P3 rouge (2) pour l’équipe P1+P3. Le rouge clair, écarté en v1.3 car proche du vert en luminosité, est repris à la demande de Stéphan pour des équipes bleue et rouge. Le texte du message reste blanc ; INFO et messages du serveur en gris clair (15).

- Chaque bot a un nom unique à la table (BOT1, BOT12… *(v2.1)*) : dans le tchat, « BOT2 » désigne le même bot pour tout le monde.

## 10. Conventions du code

Le client C/cc65 (c64/) et le serveur Python (server/) sont écrits et en service. Les extraits BASIC ci-dessous viennent de la conception d’origine : leurs conventions (codes des cartes, places, couleurs) sont toujours celles du code.

### 10.1 Codage des cartes et places

```
REM Carte C = COULEUR*8 + RANG, C=0..31
REM COULEUR : 0=Pique, 1=Coeur, 2=Trefle, 3=Carreau
REM RANG : 0=7, 1=8, 2=9, 3=10, 4=V, 5=D, 6=R, 7=A
REM Places : P0=SUD, P1=EST, P2=NORD, P3=OUEST (absolues)
REM Sens : P0 -> P1 -> P2 -> P3 (sens inverse des aiguilles)
REM Ecran : position relative r = (P - MOI + 4) MOD 4
REM Equipes : E0 = P0+P2 ; E1 = P1+P3
```

### 10.2 Conventions graphiques

```
REM Couleur plateau : 5 (vert) ; bordure : 9 (brun) ; bandeaux noirs ; traits jaunes
REM Cartes : fond blanc, rang et symbole rouge=2 ou noir=0
REM Mode couleur etendue (ECM) ; RAM couleur : $D800
REM FC(0)=0 pique ; FC(1)=2 coeur ; FC(2)=0 trefle ; FC(3)=2 carreau
```

### 10.3 Logique serveur

```
DISTRIBUER : melanger ; 3 puis 2 cartes par place ; RETOURNEE = 21e
ENCHERES   : tour 1 sur couleur retournee ; tour 2 autre couleur
COMPLETER  : preneur = retournee + 2 ; autres = 3
ENTAMEUR   = (DONNEUR + 1) MOD 4
BELOTE     : auto a la pose du R ou de la D d atout si le joueur a les deux
PLI        : 4 coups valides ; gagnant = ENTAMEUR du pli suivant
FIN MANCHE : compter (contrat/dedans/litige/capot) ; SCORE ; DONNEUR+1
BOT        : toujours un coup legal (section 5.3)
```

### 10.4 Organisation du projet *(v3)*

```
Belote_C64/
  c64/         client C (cc65), compilé par le Makefile de la racine (cl65 -t c64)
  c64/vice/    réseau simulé pour VICE (make vice-demo SCENARIO=1..7)
  pc/          client PC dans un terminal (make pc), belote_lan.py
  .github/     construction de belote-lan.exe (GitHub Actions)
  server/      serveur Python asyncio + tests pytest
  protocol.md  extrait de la section 7 (protocol.fr.md en français)
  tools/       générateurs : textes (4 langues), musique, écran titre ; belote.service
  docs/        captures d’écran (FR et EN), fiche du service systemd
  config.mk    adresses : serveur par défaut, C64 Ultimate
  CLAUDE.md    instructions de build/deploy
  SPEC.md, README.md, protocol.md : traductions anglaises (*.fr.md : français)
```

Déploiement de développement : make deploy envoie build/belote_lan.prg au C64 Ultimate par son API REST (POST /v1/runners:run_prg). Le serveur se teste sans C64 avec nc ou telnet sur le port 6464.

## 11. Décisions d’arbitrage

Ces décisions priment sur les formulations contradictoires ou plus anciennes.

| Sujet | Décision consolidée | État |
|---|---|---|
| Touches | F1 paramètres (chef) ; F2 lancer (chef) ; F3 tchat ; F4 effacer la partie (chef) ; F5 suite (tout joueur) / nouvelle partie (chef) ; F7 quitter ; F8 règles ; 1–4 enchères ; 1–8 cartes ; RETURN valider ; joystick en port 2, flèches et ESPACE *(v1.7)*. | Retenu ; F8 *(v3)* ; joystick (client v1.7) |
| Places / partenaires | P0=SUD, P1=EST, P2=NORD, P3=OUEST ; ordre P0→P1→P2→P3, sens inverse des aiguilles d’une montre ; équipes P0+P2 contre P1+P3 ; affichage relatif, chacun en SUD. | Retenu ; sens *(v4)* |
| Donne et enchères | Belote classique : 3 + 2 cartes + retournée, deux tours d’enchères, puis 3 cartes (preneur : retournée + 2). Tous passent : redistribution, donneur suivant. | Retenu ; donne *(v3)* |
| Jeu *(v4)* | Fournir ; à l’atout monter toujours ; couper si adversaire maître, surcouper si possible ; sous-coupe interdite sauf s’il ne reste que de l’atout ; libre si partenaire maître. | Retenu *(v4)* ; sous-coupe obligatoire depuis la v2.1 (étape 54) |
| Annonces *(v4)* | Uniquement belote-rebelote (+20), annoncée automatiquement par le serveur. Pas de tierce, cinquante, cent ni carré. | Retenu *(v4)* |
| Points | 162 par manche (152 + dix de der), belote-rebelote +20 ; cible 1000 par défaut, paramétrable ; la première équipe à atteindre la cible gagne (contrôle en fin de manche) ; les deux la même manche : la plus haute ; égalité parfaite = nouvelle manche ; réserve non attribuée perdue. | Retenu ; fin *(v4)* |
| Contrat | Preneur : strictement plus que la défense, belote comprise. Dedans : 162 à la défense, la belote reste à l’équipe qui l’a annoncée. Litige : points du preneur en réserve. Capot : 252. Points bruts. | Retenu *(v3)* ; capot *(v4)* |
| Présence | Pas de spectateurs. Inactivité 3 min par défaut (F1 : 1 à 10 min) : bot. Retour possible sur sa place si libre. Déconnexion pendant son tour : le bot joue immédiatement. | Retenu |
| Tchat | Public ; nom 6 caractères ; message 30 caractères ; boucle non bloquante ; couleur de nom par place, deux nuances par équipe (bleu clair et bleu, rouge clair et rouge) ; bots BOT1 à BOT4. | Retenu ; couleurs et noms des bots (client v1.3) |
| Graphisme | Plateau vert 5 avec motif de feutre, bordure brune 9, bandeaux noirs et traits jaunes *(v1.7)* ; cartes blanches aux coins arrondis, rang et symbole rouge 2 / noir 0 ; RAM couleur $D800 ; carte jouée qui glisse (deux sprites). | Retenu ; cartes blanches (client v1.3) ; coins et glissement (client v1.5) |
| Sons | Musique sur l’écran titre ; bruitages carte posée, pli, tchat ; jingles victoire et défaite. Côté client seulement (section 8.3). | Retenu |
| Langues | Français, anglais, allemand, espagnol, choisis par F1 sur l’écran de connexion ; majuscules sans accents ; protocole inchangé, ERR et INFO traduits par le client (section 2.1). | Retenu (client v1.5) |
| Écran | Grille 40 × 25 (L0–L24), sans tapis central : carte jouée sous le nom de chaque joueur ; mains adverses non affichées ; journal 6 lignes ; barre de touches ≤ 39 caractères en L24 ; * devant le joueur au tour (retiré à l’étape 30). | Retenu ; sans tapis *(v4)* |
| Serveur | Python asyncio sur Linux (VPS en production), port 6464 ; adresse saisie sur le C64 ; distribue, valide, compte, joue les bots (délai 1 s) ; 4 humains max. | Retenu ; adresse *(v4)* |
| Paramètres F1 *(v4)* | Score cible (500–5000, défaut 1000) et délai d’inactivité (1–10 min, défaut 3). | Retenu *(v4)* |
| Matériel réseau *(v3)* | C64 Ultimate, Ultimate Command Interface, TCP direct. | Retenu *(v3)* |
| Protocole *(v3)* | Texte ASCII, une ligne par message terminée par LF, 64 octets max ; messages de la section 7. | Retenu *(v3)* |

## 12. Reste à faire / questions ouvertes

- **Bots** — Renforcés en v2.0 (4.4) : enchères à la valeur de la main, atouts tirés par le preneur, partenaire chargé. Pistes suivantes : compter les atouts tombés pour savoir quand couper, le 10 de der, jouer selon la place du preneur ; à mesurer avec tools/duel_bots.py.

- **Écran de fin de partie (C64)** — Scores, victoire, F5 et F7 sont centrés (v2.0 retouchée). Reste à finir : aligner F5/F7 en un bloc, centrer la barre du bas, raccourcir « F5 = NOUVELLE PARTIE (CHEF SEULEMENT) » en français.

- **Type de client dans les logs** — Le serveur ne sait pas si une connexion vient d’un C64 ou du client PC : les deux envoient la même séquence (SALONS, JOIN). Proposition : une ligne `CLIENT C64 2.0` ou `CLIENT PC 2.0` avant SALONS, loguée par le serveur, absence tolérée (anciens clients = « inconnu »). Déployer le serveur avant les clients (un serveur v2.0 répond ERR NOM, que les clients doivent ignorer). Touche salons.py, proto.c, pc/belote_lan.py, protocol, SPEC, tests.

- **Sons d’arrivée et de départ** — Un petit bruitage quand un joueur entre dans la partie et un autre quand il en sort (tools/musique.py, c64/son.s ; côté PC, au minimum la cloche du terminal). Le client sait déjà qui est assis (messages de table) : il reste à repérer l’arrivée ou le départ d’un humain, sans sonner pour un bot qui prend la place.

- **Son de changement de tour d’enchères** — Un son discret quand les deux tours d’enchères sont passés (tout le monde a passé) et que la donne repart vers une autre enchère, c’est-à-dire une nouvelle donne. À brancher sur le message du serveur qui annonce ce changement (tools/musique.py, c64/son.s ; cloche du terminal côté PC).

- **Joystick partout** — Le joystick ne sert pas encore : à la validation de l’écran de connexion (avec le choix de langue), à la sélection du salon, et pour lancer une nouvelle partie côté chef (F5). Prévoir le feu pour valider, haut/bas pour choisir le salon et la langue, et une façon de lancer la nouvelle partie sans clavier. Une analyse d’ensemble est à faire d’abord : recenser chaque écran et chaque touche (F1, F2, F5, F7…) pour rendre le jeu aussi complet que possible au joystick seul. Le joystick s’ajoute au clavier : toutes les fonctions existantes (pseudo, tchat, touches F) restent telles quelles. Le but est qu’un joueur qui ne tchate pas puisse, son nom saisi, tout faire au joystick sans retourner au clavier.

- **Joystick de l'écran de connexion (bogue)** — Corrigé en v2.1 (étape 57) : `touche_connexion` sort dès qu'une action du joystick est reconnue.

- **Noms des bots et styles** — Fait en v2.1 (4.4, étape 56).

- **Portage Oscar64** — Essayé (étape 52) puis abandonné : le compilateur actuel génère du code faux à tous les niveaux d'optimisation. À reprendre seulement si ces erreurs sont corrigées.

- **Plusieurs tables** — Fait en v2.0 : 9 salons (4.5). Au-delà de 9, il faudrait deux colonnes ou des pages sur le C64, qui manque de mémoire.

- **Accessibilité** — Il faut un C64 Ultimate (ou Ultimate 64 / Ultimate-II+) : VICE n’émule pas la Command Interface. Une version passant par le réseau émulé de VICE (RR-Net) permettrait d’essayer sans matériel.

## 13. Historique des décisions

| Étape | Décision / évolution | Traitement |
|---|---|---|
| 1 | Concept initial : belote réseau, serveur maître de la partie ; messages JOIN, COUP, ENCH, PASSE, TCHAT, REJOUER, LEAVE. | Conservé et détaillé. |
| 2 | Premier humain : rôle de chef, lancement F2 et passation du chef. | Conservé ; F1 réaffectée aux paramètres. |
| 3 | Enchère simplifiée et comptage provisoires. | Remplacés par les enchères classiques et 162 points. |
| 4 | Règles classiques : retournée puis autre couleur ; belote/rebelote ; obligations à l’atout. | Intégré. |
| 5 | Écran texte 40 colonnes, adversaires cachés, tapis, * de tour. | Conservé ; ramené à 25 lignes en v3. |
| 6 | 4 humains maximum, bots, pseudos, reconnexion, inactivité. | Consolidé. |
| 7 | Score cible 1000, contrôle en fin de manche, donneur qui tourne après égalité. | Conservé. |
| 8 | Arbitrages : touches, sièges/équipes, couleurs C64, tchat, VPS Linux. | Appliqués. |
| 9 | Zone d’enchères et écran de fin de partie. | Conservé. |
| 10 | Stack : Python asyncio + client cc65. | Retenu. |
| 11 *(v3)* | C64 Ultimate choisi ; protocole complété (transport, trames, nouveaux messages, COUP par code) ; écran 25 lignes ; F8 ; vue relative ; donne corrigée ; règles dedans / litige / points bruts. | Version 3 (7 novembre 2026). |
| 12 *(v4)* | Règles officielles de la belote classique : sens du jeu, obligations, capot, belote comprise dans le contrat ; seule la belote est annoncée (automatiquement) ; la première équipe à 1000 gagne ; adresse saisie sur le C64, bots à 1 s, couleurs du tchat, paramètres F1. Tapis central supprimé. | Version 4 (7 novembre 2026). |
| 13 | Sons sur le SID : musique de l’écran titre, bruitages (carte, pli, tchat), jingles de fin de partie. Aucun changement de protocole. | Client v1.2 (13 novembre 2026). |
| 14 | Bots nommés BOT1 à BOT4 par place réelle (et non plus par position relative, qui différait d’un écran à l’autre) ; couleurs des noms par équipe : cyan et bleu, orange et rouge. | Client v1.3. |
| 15 | Cartes blanches, rang et symbole dans la couleur de la carte (rouge ou noir), au lieu de cartes rouges ou noires à texte blanc. | Client v1.3. |
| 16 | Noms BOT et BOT + chiffres refusés aux joueurs (ERR NOM RESERVE) ; messages de refus en clair sur l’écran de connexion (table pleine, nom réservé ou refusé). | Serveur et client v1.4. |
| 17 | Client en quatre langues (français, anglais, allemand, espagnol), choisie par F1 sur l’écran de connexion ; figures de la langue ; ERR et INFO traduits par le client ; sur l’écran titre, une touche SPACE dessinée remplace « ESPACE POUR JOUER ». Aucun changement de protocole ni de serveur (voir 2.1). Documentation traduite en anglais (SPEC.md, README.md, protocol.md, docs/server-service.md), le français gardé en *.fr.md. Release GitHub v1.5 (notes en anglais et en français), description du dépôt en anglais. | Client v1.5 (14 novembre 2026). Serveur public mis à jour. |
| 18 | Bots, après une partie complète sur le serveur public (Stéphan contre Claude, 1115 à 687) et l’analyse de son journal : les 10 sacrifiés par les bots étaient des coups forcés, pas des erreurs. Mémoire des cartes jouées ; entame de la plus forte carte restante d’une couleur (10 maître après la chute de l’as), +1 % de points sur 40 000 donnes simulées contre l’ancienne stratégie. Couper ou gagner avec une carte maîtresse plutôt qu’avec la plus petite carte gagnante a été essayé et écarté (−6,8 %). | Serveur v1.5, correction après la release (14 novembre 2026) : notes de la release complétées, tag inchangé, serveur public mis à jour. |
| 19 | Cartes aux coins arrondis (arc de 2 pixels, préféré à 3 après essai sur le C64) ; les caractères " $ % & deviennent les coins et s’affichent « ? » dans le tchat ; tools/textes.py les refuse dans les traductions ; captures de la documentation refaites (FR et EN). | Client v1.5, mise à jour (14 novembre 2026) : PRG de la release remplacé, tag inchangé. |
| 20 | Carte qui glisse (deux sprites) de la main ou du bord de l’écran jusqu’au tapis ; table et main redessinées sur place, sans clignotement ; sa carte part de l’emplacement choisi ; dernière carte jouée automatiquement. Mis au point par essais sur le C64 : la première version clignotait (la table et la main étaient effacées puis redessinées, deux fois par carte) ; la carte montait en zigzag (cc65 calculait mal une différence négative multipliée par l’étape) ; elle partait de sous le tapis (la MAIN arrive avec le JOUE et retirait déjà la carte : son emplacement est retenu dès le JOUE). Démo 6 conforme au serveur (MAIN après JOUE). Aucun changement de protocole ni de serveur. | Client v1.5, mise à jour (14 novembre 2026) : PRG de la release remplacé, tag inchangé. |
| 21 | Relecture complète du serveur : un joueur qui se reconnecte en FIN PARTIE reçoit maintenant GAGNANT (son écran de fin affichait le score sans le vainqueur). Test ajouté, qui échoue sans la correction. | Serveur v1.5, correction (14 novembre 2026). Serveur public mis à jour. |
| 22 | Protections du serveur public : une connexion sans place à la table au bout de 60 s est fermée ; tchat limité à 3 messages par joueur sur 10 s (les suivants sont ignorés, sans nouveau message d’erreur pour ne pas changer le client). Tests sur la table et sur vraie socket. | Serveur v1.5, correction (14 novembre 2026). Serveur public mis à jour et vérifié : une connexion sans place y est fermée au bout de 60 s. |
| 23 | Relecture complète du client : pendant les enchères, la ligne d’état affichait « AU TOUR DE BOT » au lieu de BOT1 à BOT4 ; une seule fonction (nom_place) nomme désormais les places sur la table, dans le journal et sur la ligne d’état. Captures refaites. Un GIF animé de la carte qui glisse (une capture VICE par image d’écran, 19 656 cycles d’écart en PAL, images déchirées écartées) a été ajouté au README puis retiré, jugé trop gros. | Client v1.5, mise à jour (14 novembre 2026) : PRG de la release remplacé (41 902 octets), tag inchangé ; notes de la release complétées avec cette correction et celles du serveur (étapes 21 et 22). |
| 24 | Écran titre : coins des cartes légèrement arrondis (3 pixels par coin, bord noir qui suit la courbe) ; dans l’éventail, le coin laisse voir la carte de derrière au lieu d’un pixel vert qui la trouait. Image regénérée par tools/titre.py, capture docs/titre.png refaite (celle de GitHub vérifiée identique ; une ancienne image affichée vient du cache du navigateur). | Client v1.5, mise à jour (14 novembre 2026) : PRG de la release remplacé, tag inchangé, notes de la release complétées. |
| 25 | Une seule table pour l’instant ; un serveur à plusieurs tables pourrait devenir un projet si le jeu trouve son public. Section « Et après ? » dans les README et les notes de la release ; onglet Discussions activé et annonce bilingue publiée (https://github.com/Stephan83c/belote-lan-c64/discussions/1), épinglée. | 14 novembre 2026. |
| 26 | Pli ramassé animé : les cartes rejoignent le centre une par une, celle du gagnant en dernier sur le dessus, puis le paquet part vers le gagnant (jusqu’à son nom pour soi, comme Stéphan l’a proposé, plutôt que jusqu’au bas de l’écran) ; bruitage du pli au départ du paquet (il partait avant, à la réception de PLI, pendant que la dernière carte glissait encore, et pouvait même effacer son claquement). Une première version réunissait les quatre cartes d’un coup avec huit sprites ; une carte à la fois, avec les deux sprites existants, ressemble davantage au geste de ramasser et garde le code plus simple. Vérifié dans VICE (démo 6, gagnants SUD, EST, NORD, OUEST). Aucun changement de protocole ni de serveur. | Client v1.6 (14 novembre 2026). |
| 27 | Fin de manche sans F5 du chef : la manche suivante démarre seule après 10 secondes, le temps de lire le résultat, avec un compte à rebours sur la ligne d’état (« SUITE DANS 9 S (F5) ») ; F5 l’écourte et est ouvert à tous les joueurs ; une nouvelle partie reste l’affaire du chef. Le chef n’est plus évincé pour inactivité en fin de manche (il bloquait la table s’il s’absentait). Nouveau message SUITE S, ignoré par les anciens clients (ils affichent « ON ATTEND LE CHEF », la manche repart quand même) ; option --delai-manche du serveur. 7 tests ajoutés ; démo 7 (compte à rebours vérifié dans VICE). Idée proposée par Claude, retenue par Stéphan. | Client et serveur v1.6 (14 novembre 2026) ; serveur public mis à jour (étape 32). |
| 28 | Même présentation partout. Écran de connexion : curseur d’abord sur NOM quand le serveur est rempli ; en-tête comme les autres écrans (version à droite), tirets, l’éventail de l’écran titre en cartes de la table distribuées une à une (carte qui glisse et claquement), une ligne d’information, les langues et une barre de touches en bas comme en jeu ; figures redessinées au changement de langue. Écran titre : touche SPACE plus discrète (cadre fin de 48×17 pixels au lieu de 64×27, lettres de 12 lignes au lieu de 16, centré entre l’éventail et la ligne d’auteur), capture docs/titre.png refaite. Pile C de cc65 ramenée de 2 à 1,5 Ko (__STACKSIZE__ dans le Makefile) : le programme dépassait $C000 de 216 octets. Vérifié dans VICE (FR, EN, DE). | Client v1.6 (14 novembre 2026). |
| 29 | Musique moins « bip bip » : chaque note restait figée (même largeur d’impulsion, même hauteur). Le lecteur SID fait maintenant varier la largeur d’impulsion voix par voix (aller-retour entre $300 et $800, le son s’épaissit) et ajoute un vibrato rapide (7,5 Hz, une douzaine de cents) qui imite le battement des anches d’un accordéon musette ; mélodie un peu plus tenue, accords moins étroits. Après écoute (« trop d’effet ») : effets réduits de moitié ; basse une octave plus bas, en carré au lieu du triangle (qui porte mal dans le grave) et un peu tenue : deux fois plus d’énergie sur sa fondamentale. Mêmes notes, sauf la basse transposée. Réglages par voix dans tools/musique.py (deux octets de plus par voix). Vérifié sur un enregistrement VICE : bandes latérales à ±7,5 Hz autour du do aigu (39 et 36 contre 5 et 1 avant). | Client v1.6 (14 novembre 2026). |
| 30 | Retouches : plus d’astérisque devant le nom du joueur au tour (la carte qui arrive et la ligne d’état suffisent) ; toc grave et feutré pour chaque carte réunie au centre quand le pli est ramassé (nouveau bruitage RAMASSE ; un premier essai jouait par erreur le ding du tchat : bruitage inséré au mauvais rang dans tools/musique.py, dont l’ordre doit suivre les numéros FX_ de c64/son.h) ; pendant le compte à rebours, « MANCHE POUR NOUS » en jaune ou « MANCHE POUR EUX » en gris, « (F5) » retiré de la ligne puisque la barre l’affiche. Textes NOUS et EUX réutilisés (mémoire). Vérifié dans VICE (démos 6 et 7). | Client v1.6 (14 novembre 2026). |
| 31 | Équipes en couleurs : noms de l’équipe P0+P2 en bleu clair et bleu, de l’équipe P1+P3 en rouge clair et rouge (au lieu de cyan et bleu, orange et rouge), toujours fixes par place et identiques sur tous les écrans ; la ligne de fin de manche prend la couleur claire de l’équipe gagnante. Noms de 6 caractères au lieu de 5 (serveur et client ; journal : nom sur 6 colonnes, message sur 32) ; un client v1.5 tronque ces noms à 5. Mémoire : l’image titre est compressée (cases de feutre identiques : un bit par case au lieu de 10 octets), décodée en assembleur (c64/titre_dec.s) pour s’afficher aussi vite qu’avant ; le PRG passe de 44 382 à 38 892 octets (environ 5,5 Ko de marge sous $C000). Image vérifiée identique au pixel près dans VICE. 1 test serveur ajouté. | Client et serveur v1.6 (14 novembre 2026). |
| 32 | Relecture du code avant la v1.6 : noms de l’EST et de l’OUEST remis aux colonnes 27 et 1 (décalés d’une case avec le retrait de l’étoile, un nom de 13 caractères à l’EST débordait sur la ligne suivante et celui de l’OUEST était rogné par l’effacement du centre) ; SUITE ignoré si son nombre n’est pas valable ; glisser() réutilise deplacer() ; commentaires mis à jour. Captures FR et EN refaites (couleurs d’équipe). Release GitHub v1.6. | Client et serveur v1.6 (14 novembre 2026). Serveur public mis à jour par Stéphan, vérifié sans prendre de place : JOIN BOT123 répond ERR NOM RESERVE (un serveur v1.5 répondrait ERR NOM, nom trop long). Compte à rebours de fin de manche confirmé par Stéphan sur le C64 avec le serveur public. Notes de la release v1.6 et annonce épinglée des Discussions mises à jour (v1.6, serveur public déjà à jour). |
| 33 | Paquet du serveur dans la release : `make paquet-serveur` produit belote-serveur-vX.Y.tar.gz et .zip (dossier belote-serveur : serveur, tests, service systemd prêt pour ~/belote-serveur, protocole, licence, notes de mise en place en français et en anglais). Le serveur n’utilise que la bibliothèque standard : `python3 -m belote`, sans venv. Vérifié en partant de l’archive : lancement, `JOIN BOT2` → ERR NOM RESERVE, 477 tests. | Release v1.6 complétée (14 novembre 2026) : archives ajoutées, notes de la release et annonce des Discussions mises à jour. |
| 34 | v1.7, idées venues d’un client expérimental « édition café » écrit à part : joystick en port 2 partout (titre, connexion avec langue et champs, choix de la carte et de l’enchère, manche suivante) ; à son tour, les cartes jouables sortent du rang (règles du serveur recopiées dans le client) et le numéro de la carte choisie est sur fond blanc ; enchères en étiquettes, la choisie en blanc, PASSE par défaut ; fin de manche sur une grande carte blanche aux coins arrondis au centre du tapis ; bandeaux noirs en haut et en bas (touches en jaune), traits fins jaunes au lieu des tirets, bordure brune ; joystick dessiné à côté de SPACE sur l’écran titre. Captures refaites. Sections 2.1, 3 et 8 de cette spécification mises à jour. Serveur inchangé. | Client v1.7 (14 novembre 2026) : release GitHub v1.7 (PRG, paquet du serveur, notes FR/EN), annonce épinglée des Discussions mise à jour ; pas de mise à jour du VPS. |
| 35 | Client PC pour jouer sans C64 (un ami de Stéphan n’en a pas) : pc/belote_lan.py, terminal 80×24, Windows, macOS et Linux, quatre langues avec accents (le terminal n’a pas les limites de l’ECM), nom, serveur et langue retenus dans ~/.belote-lan.json. Écran : tapis vert, cartes blanches 5×3, cartes jouables qui sortent du rang (les autres grisées), enchères en étiquettes, fin de manche et de partie sur une carte blanche, journal à droite, bandeaux noirs aux touches jaunes. Touches : flèches et Entrée, 1-8, T tchat, D dernier pli, A règles, L et R (chef, en attente), E effacer, Q quitter ; F1-F8 du C64 acceptées. Reconnexion à sa place par Entrée après une coupure. Choix écartés : curses (absent de Windows sans paquet en plus), client dans le navigateur (passerelle WebSocket à ajouter au serveur, plus tard si le client PC plaît). Tests (9) : règles identiques au serveur sur 20 000 situations, ordre du pli retrouvé à la reconnexion, parties complètes contre le vrai serveur (aucun refus, 162 points comptés par manche), version identique au Makefile ; ils sont sautés dans le paquet du serveur. VERSION passe à 1.8 (Makefile et client PC). | Client PC v1.8 (14 novembre 2026), validé par Stéphan. belote-lan.exe construit par GitHub Actions (8,5 Mo) : le premier essai plantait sur --help, la sortie redirigée de Windows étant en cp1252 (symbole ♠) ; sortie passée en UTF-8 avant tout affichage. Essayé avec succès par Stéphan. Release GitHub v1.8 (PRG, belote_lan.py, paquet du serveur, notes FR/EN ; belote-lan.exe joint par GitHub Actions), annonce épinglée des Discussions mise à jour. Serveur et client C64 inchangés : pas de mise à jour du VPS. |
| 36 | Essai écarté : bordure en veines de bois. Le VIC ne met qu’une couleur dans la bordure ; une interruption raster la changeait au début de certaines lignes (bandes horizontales brunes, orange et noires, écrites dans le retour de ligne, bit 8 de la comparaison préservé dans $D011). Neuf veines : peu évocateur. Trente : joli motif, mais 30 % du processeur (entrée et sortie d’interruption par le KERNAL, attente de la ligne), le jeu rame. Dix-sept : environ 15 %. Stéphan a préféré revenir à la bordure brune unie. Enseignements notés : arrivée dans le gestionnaire environ 85 cycles après le déclenchement, quatre lignes au moins entre deux changements. | Rien de publié ; client C64 v1.8 remis sur le C64. |
| 37 | Table symétrique, signalée par Stéphan (BOT2 décalé à l’EST, BOT4 bien placé à l’OUEST) : carte de l’EST de la colonne 28 à 32 (à quatre colonnes du bord comme l’OUEST), nom de l’OUEST commençant au bord gauche de sa carte, nom de l’EST finissant au bord droit de la sienne (un nom avec « (CHEF) » reste dans sa case), NORD et SUD centrés sur leur carte, tableau de fin de manche centré (cases 10 à 29 au lieu de 7 à 26). Lecteur SID : le retour vers l’ancien vecteur d’interruption passe par un jmp direct dont l’adresse est posée à l’installation, au lieu de jmp (ancien) ; ld65 avait signalé ce vecteur à cheval sur deux pages ($xxFF), où le 6502 lit une mauvaise adresse (plantage dès la musique), un piège qui dépendait de la taille du programme. Vérifié dans VICE (attente, partie, fin de manche) et sur le C64. | Client C64 v1.8 corrigé (15 novembre 2026), numéro de version inchangé : personne n’avait encore essayé le PRG v1.8. belote_lan.prg remplacé dans la release v1.8, notes mises à jour, tag inchangé. Serveur et client PC inchangés. |
| 38 | Retouches du client C64 demandées par Stéphan. Journal et tchat (lignes 12 à 19, entre les traits jaunes) sur un vert uni, sans les points du feutre (ecran_uni(), écran de jeu seulement). Ramassage du pli deux fois plus lent (10 images par carte, départ du paquet en 16 ou 28 images). « 1ER TOUR » et « 2E TOUR » finissent à la colonne 38, comme les choix d’enchère commencent à la 1. Écran de connexion : seul le NOM est affiché, centré ; F3 ouvre le réglage du serveur, un peu caché, en deux champs IP (29 caractères) et PORT (chiffres, 6464 si vide) ; barre « RETURN VALIDER  F1 LANGUE  F3 SERVEUR » ; langues centrées. Mémoire : le programme débordait de 28 octets (marge réelle de 48 octets, et non 5,5 Ko comme noté) ; sprintf de cc65 (1,3 Ko avec vsnprintf) remplacé par fmt() dans ecran.c (%s %c %u %d, largeur, 0 et -), écrans identiques au pixel près dans VICE ; environ 430 octets de marge. Partie sur le serveur public le même jour, Stéphan et Claude contre GRAF (client Windows) et un bot : 1051 à 609 ; client de GRAF figé pendant son tour puis relancé, sans doute l’Édition rapide de la console Windows (un clic dans la fenêtre bloque l’affichage) : correction possible, jugée inutile pour l’instant. | Client C64 v1.8 (15 novembre 2026), numéro de version inchangé : belote_lan.prg remplacé dans la release v1.8, notes mises à jour, tag inchangé. Serveur et client PC inchangés. |
| 39 | Failles du serveur trouvées le 15 novembre (après des scans de connexions sur le serveur public), corrigées en pensant au multi-salon. Connexions sans limite : 3000 connexions depuis une seule IP étaient toutes acceptées ; le serveur entier (toutes tables confondues) en accepte maintenant 64 au plus, et 8 au plus par IP (quatre C64 derrière une même box passent), classe Limites dans __main__.py, options --max-connexions et --max-par-ip. Au-delà, ERR TABLE PLEINE dès l’ouverture puis fermeture : un code à part (SERVEUR PLEIN) aurait affiché « nom refusé » sur le client PC déjà publié. Rejoué : 8 acceptées, 2992 refusées. Table squattée : quatre JOIN muets gardaient la table sans limite (personne n’était jugé inactif avant le lancement) ; en ATTENTE, chaque table rend maintenant la place d’un humain muet depuis 10 minutes (--delai-attente), avec les messages de l’inactivité en jeu, que les clients traduisent déjà. Clients inchangés. 3 tests ajoutés. | Serveur v2.0 (15 novembre 2026), commité, pas encore publié. |
| 40 | Multi-salon, sur la branche multi-salon : 9 salons numérotés (--salons 1 à 9), chacun une Table complète, aiguillés par la classe Salons (server/belote/salons.py). Protocole compatible : SALONS donne la liste (SALONS N, puis SALON I H ETAT), JOIN NOM I choisit le salon, JOIN NOM sans numéro va au salon 1 (anciens clients) ; salon choisi plein : ERR TABLE PLEINE sans fermeture ; ERR SALON pour un numéro invalide ; RAZ N à la console. C64 : après le nom, liste des salons (numéro, joueurs sur 4, ATTENTE ou EN JEU) au joystick, aux flèches ou au chiffre, F7 pour revenir ; avec un serveur sans salons (ERR à SALONS), JOIN sans numéro ; touche_connexion() commune au nom et aux salons, qui surveille aussi la connexion. Mémoire : pile C mesurée dans VICE (RAM remplie de $55, bruit aléatoire de VICE coupé) à 58 octets au plus dans tous les scénarios, réduite de 1,5 Ko à 512 octets ; il reste 44 octets. Essai de Stéphan : coupé après 60 s sur la liste (délai sans JOIN) ; une connexion qui a demandé SALONS a maintenant 5 minutes pour choisir (DELAI_LISTE), et les messages sous le nom sont centrés. Client PC : même écran des salons (Échap pour revenir). Scénario de démo 8 (liste des salons). 17 tests ajoutés. | Branche multi-salon (15 novembre 2026), essai sur le C64 avec un serveur local. |
| 41 | Bots renforcés, sur la branche bots. Outil tools/duel_bots.py : les bots actuels contre ceux d’une version git (main par défaut), chaque donne jouée deux fois, équipes échangées, pour ôter la chance des cartes (4 000 donnes à la seconde). Enchères : choisir_enchere reçoit la carte retournée (plus seulement sa couleur) et estime la main pour chaque atout (valet 20, 9 14, as 11..., as hors atout 10, belote 10) ; prise à partir de 35 (essayé de 20 à 50 : 50 perdait, 35 le meilleur), +1,8 % de points. Jeu : charger le partenaire en dernier (+1,3 %), puis en troisième quand sa carte est imbattable dans sa couleur, même au risque d’une coupe (+0,8 %) ; le preneur tire son atout maître, ou son plus petit avec trois atouts (+0,2 % sur 200 000 donnes ; l’atout maître seul ne gagnait rien). Résultat : 53,9 % des points contre les bots de la v1.8 (+13 points par donne, 200 000 donnes). Entre quatre bots, 18 % de donnes redistribuées (les anciens prenaient presque toujours). choisir_carte reçoit aussi le preneur. Tests des bots refaits (8). | Branche bots (15 novembre 2026), serveur seulement. |
| 42 | Mémoire du C64 : il restait 45 octets. L’image titre (4,4 Ko) ne servait qu’au démarrage mais occupait la mémoire en permanence : elle passe, avec son décompresseur, dans le segment ONCE de cc65 ; un constructeur assembleur (.constructor dans c64/titre_dec.s) éteint l’écran, règle la banque VIC, la bordure brune et le fond vert, et décompresse l’image au chargement, avant que crt0 remette les variables à zéro ; ensuite cette place sert aux variables. titre() est appelé avant ecran_init() (qui écrase la matrice de couleurs), et ecran_init() rallume l’écran. Écran titre, table et liste des salons identiques au pixel près dans VICE. Marges : 1,7 Ko pour le code (fin du segment ONCE sous $C000), 4,7 Ko pour les variables. Essayé aussi : -Cl (variables locales statiques, réinitialisées à chaque appel), seulement +211 octets, non retenu. tools/titre.py génère l’image dans ONCE. | Branche bots (15 novembre 2026). |
| 43 | Version 2.0, à diffuser : regroupe les entrées 39 à 42 (failles du serveur, 9 salons, bots renforcés, mémoire du C64). Client PC : l’Édition rapide de la console Windows est coupée pour la fenêtre du jeu (un clic y figeait l’affichage, comme pour GRAF). Démos compilées avec le numéro de version (le bandeau affichait « V? »). Captures refaites dans VICE, en français et en anglais : table (tchat sur vert uni), enchères, et la liste des salons, ajoutée aux README avec la façon de choisir son salon. | Client C64, client PC et serveur v2.0 (15 novembre 2026). Release GitHub v2.0 ; serveur public mis à jour par Stéphan, vérifié sans prendre de place : SALONS répond SALONS 9 et la liste, JOIN ZZ 0 répond ERR SALON. |
| 44 | Rangements après la v2.0 : captures du client PC refaites (« v2.0 » dans le bandeau) par un nouvel outil, tools/capture_pc.py, qui fait jouer le client en mémoire contre une table du serveur et dessine sa grille de caractères en PNG, sans terminal ni pyte ; branches de travail (failles-serveur, multi-salon, bots), fusionnées dans main, supprimées. SPEC relue : en-tête V2.0 de l’écran de connexion, ramassage à 10 images par carte (16 et 28 pour le paquet), vert uni du journal et du tchat, « 1ER TOUR » en colonne 38, F3 à l’écran de connexion. | Dépôt seulement (15 novembre 2026). |
| 45 | Diffusion : page itch.io publiée par Stéphan (https://stephan83c.itch.io/belote-lan-c64), fichiers de la release v2.0, captures, GIF animé de 16 s capturé dans VICE (scénario 6 en anglais, une image par lancement), déclaration d’IA (« AI Assisted ») et paragraphe sur la façon dont le jeu a été fait (spécification, tests sur le vrai C64, 500 tests, bots réglés sur 200 000 donnes). Lien ajouté aux README et à l’annonce des Discussions. CSDb écarté (plutôt la démoscène). Page relue après publication : plateformes Windows (exe) et Linux (py) seulement, macOS décoché faute d’essai, comme le demandent les règles d’itch.io. Premier billet du devlog publié (« BELOTE LAN C64 2.0 is out: networked belote on the real C64 », type Release, avec le GIF) ; l’éditeur d’itch.io n’étant pas du Markdown, les astérisques du modèle ont été retirées. | Dépôt et annonce (15 novembre 2026). |
| 46 | Écran de fin de partie : scores, victoire, F5 et F7 centrés (c64/vue.c, centrer()), scores espacés d’une ligne. PRG de la release v2.0 remplacé (même tag, pas de nouvelle version). | Retouche de présentation. |
| 47 | Aide aux débutants (la communauté rétro francophone ne connaît pas la belote et ne donne pas de retour) : la belote en 5 minutes, docs/regles.fr.md et docs/rules.md (but, manche, atout, enchères avec un repère, obligations, points, contrat, pli commenté, touches), liés depuis les README. Pistes notées, non faites : raison du grisage d'une carte, conseil d'enchère, table d'entraînement seul contre 3 bots. | Documentation seulement ; client et serveur inchangés. |
| 48 | Règles : phrase ajoutée à la page des règles (docs/regles.fr.md, docs/rules.md) : les points sont exacts (162 et 252), la table arrondit souvent à 160 et 250. Points bruts conservés (choix de Stéphan), rien changé au code. | Documentation. |
| 49 | Bots : seuil de prise abaissé de 35 à 32 (server/belote/bots.py), après balayage avec duel_bots (25 à 45 ; autres valeurs : as, 10 gardé, belote, sans effet net). Contre le seuil 35 : +0,4 point de part sur 6 graines de 20 000 donnes (50,42 % en moyenne), moins de donnes redonnées (environ 4 250 sur 40 000 au lieu de 7 200). Prototype PIMC pour le jeu de la carte (tools/pimc.py, non intégré) : 56 % contre les bots actuels, 100 tirages par coup. | Réglage ; mise à jour du serveur à faire sur le VPS. |
| 50 | Bots PIMC pour le jeu de la carte (server/belote/pimc.py, option `--pimc N`, 2 processus par défaut ; repli sur la stratégie simple après 3 s) : environ 56 % des points contre la stratégie simple. Enchères PIMC essayées (seuil 5 : +0,8 point de part), non retenues. La donne garde ses plis terminés (Donne.plis). | Ajout ; mise à jour du serveur à faire sur le VPS (2 cœurs de calcul). |
| 51 | R&D des bots, hors serveur et hors clients (21 novembre 2026) : `tools/styles.py`, cinq styles de bots (attaquant, défenseur, modéré, adaptatif au score, feinteur) en trois variantes (décalage des seuils de prise -2, 0, +2), nommés BOT1 à BOT5 pour la variante 1, BOT12, BOT13, BOT22… pour les autres. Le jeu de la carte reste le PIMC ; un style change le seuil de prise et l'objectif des simulations. Mesures par parties entières à 1000, camps échangés : les styles sont à égalité (48 à 54 % de victoires, ±2,5 à 3,5 points) ; le défenseur à 38 perdait (42,8 %), à 34 il est à égalité (49,7 %) ; tables aléatoires avec ou sans doublon de style : 49 à 51 %, aucun duo à éviter ; le feinteur (joue une carte autre que la règle parmi les cartes à moins de 3 points de la meilleure) coûte environ 2 points de victoire (47,9 % sur 1 200 parties). PIMC conditionné par les enchères (`tools/pimc_cond.py`) : 50,45 % contre le PIMC actuel sur 12 000 parties, non retenu. Intégration au serveur en attente : elle change la signification de BOT1 à BOT4 (aujourd'hui la place à la table) dans le C64 et le client PC. Chemins : le dépôt s'appelle désormais Belote_C64 (docs, service systemd), `make paquet-client`. | R&D ; serveur et clients inchangés, rien à déployer. Poussé sur GitHub. |
| 52 | Essai de portage du client C64 en Oscar64 (21 novembre 2026), hors dépôt (`build/oscar64-essai/`) : client complet (titre, son ca65 à `$B000`, réseau) compilé, écrans identiques à cc65 dans VICE, lancé sur le C64 Ultimate ; programme de `$0801` à `$9E52` au lieu de `$B96C`. Pièges : BASIC visible sous `$A000` (`POKE(1, $36)`), BSS du lecteur à remettre à zéro, lecture du joystick (bits en entrée sur `$DC02`), `CLOCKS_PER_SEC` à 50. Abandonné : Oscar64 génère un mauvais code à chaque niveau d'optimisation (`-O2` : tests des drapeaux de redessin décalés, d'où joystick gauche/droite et F4 sans effet à l'écran ; `-O1` et `-Os` : second score faux au tableau de manche ; `-O0` : choisir() ne déplace plus la sélection ; `-O3` ne se lie pas). Le C64 est revenu au client cc65 (`make deploy`, 516 tests du serveur passés ; l'environnement Python du serveur a dû être recréé après le renommage du dossier). Trouvé au passage : à l'écran de connexion, le joystick ne peut pas fonctionner (la boucle de `touche_connexion` écrase la touche du joystick par un nouvel appel à `cbm_k_getin`), bogue présent depuis la v1.7 ; ajouté à la section 12. | Aucun changement du dépôt (client et serveur inchangés). |
| 53 | Adresse du serveur public par son nom de domaine, boombass.net, au lieu de l'IP (25 novembre 2026) : `SERVEUR_IP` de config.mk (champ SERVEUR prérempli du C64) et `SERVEUR_DEFAUT` du client PC. L'Ultimate résout le nom lui-même (vérifié sur le C64 Ultimate : connexion et partie lancée). Tests du serveur fiabilisés : deux tests d'inactivité échouaient au hasard (horloge fixe à 1000 s alors que `time.monotonic()` part du démarrage du PC, et arrondi flottant au seuil exact). | Clients seulement (serveur inchangé) ; à publier avec la v2.1. |
| 54 | Sous-coupe (25 novembre 2026) : quand un adversaire a coupé et qu'on ne peut pas surcouper, on joue quand même un atout plus faible (« pisser »), comme le disent Wikipédia, Pagat et regles-du-jeu.net ; la v4 l'interdisait à tort (défausser une autre couleur). Remarqué par Stéphan en partie : son 7 d'atout restait en bas. Serveur (`coups_legaux`), C64 (`jouables`) et client PC corrigés ; la copie du C64 a été comparée au serveur sur 50 000 cas tirés au hasard (dont 424 sous-coupes), sans écart. Transition : le serveur accepte encore la défausse de l'ancienne règle (`coups_toleres`), sinon un client v2.0 resterait bloqué dans ce cas. Règles en 5 minutes (FR/EN) mises à jour. | Serveur et clients ; à publier avec la v2.1 (mise à jour du VPS). Retirer la tolérance quand les clients v2.0 auront disparu. |
| 55 | Réserve visible (25 novembre 2026, demande de Stéphan) : tant qu'une réserve attend, l'en-tête affiche RES 81 à la place de BELOTE (C64) ou « Réserve 81 » après les scores (PC) ; le tableau de fin de manche affiche LITIGE : RES. 81, puis +81 DE RESERVE quand elle est remportée. Nouveau message `RESERVE N` (réserve en attente), aussi envoyé à qui arrive ; un client v2.1 sur un serveur v2.0 la déduit de LITIGE et INFO RESERVE. Scénarios VICE 9 (litige) et 10 (réserve remportée). | Serveur et clients ; à publier avec la v2.1. |
| 56 | Bots à style dans le serveur (25 novembre 2026) : `server/belote/styles.py` (repris de `tools/styles.py`), 15 noms (BOT1 à BOT5, BOT12, BOT13…), tirés à chaque nouvelle partie, à chaque RAZ et quand un bot remplace un humain, jamais deux fois le même nom à une table ; seuil de prise du style (`choisir_enchere(..., seuil)`), objectif du PIMC et feinte (`pimc.choisir(..., objectif, tolerance)`). Option `--sans-styles`. Clients C64 et PC : affichent le nom envoyé par le serveur ; avec un serveur v2.0 (tous « BOT »), BOT1 à BOT4 par place comme avant. Un client v2.0 sur un serveur v2.1 garde ses noms par place. | Serveur et clients ; à publier avec la v2.1. |
| 57 | Joystick de l'écran de connexion et des salons (25 novembre 2026) : le bogue présent depuis la v1.7 est corrigé, `touche_connexion` (c64/main.c) renvoie la touche dès qu'une action du joystick est reconnue au lieu de rappeler `cbm_k_getin()`, qui l'écrasait. Droite et gauche changent la langue, haut et bas passent d'un champ ou d'un salon à l'autre, le bouton valide. Vérifié sur le C64 Ultimate. Les bots reçoivent aussi de nouveaux styles à chaque RAZ (demande de Stéphan). | Client C64 et serveur ; à publier avec la v2.1. |
