# Protocole du serveur de belote

La référence est `SPEC.md` section 7 : texte ASCII, une ligne par message terminée par LF,
64 octets maximum, port TCP 6464. Ce fichier résume comment jouer à la main et consigne ce
que la spec laisse ouvert.

## Jouer avec nc

    make server            # dans un terminal
    nc localhost 6464      # dans un autre

    JOIN JEAN              rejoindre (place P0, chef)
    PARAM CIBLE 500        optionnel, chef, avant le lancement
    LANCER                 démarrer
    ENCH 1 / PASSE         à son TOUR, pendant les enchères (couleur 1 = coeur)
    COUP 14                à son TOUR, pendant le jeu (carte 14 = roi de coeur)
    REJOUER                chef : à ETAT FIN MANCHE ou FIN PARTIE
    RAZ                    chef : efface la partie en cours (comme RAZ en console)
    TCHAT BONJOUR          à tout moment après JOIN
    LEAVE                  quitter

Carte = couleur × 8 + rang.

    Couleur \ rang   7   8   9  10   V   D   R   A
    0 pique          0   1   2   3   4   5   6   7
    1 coeur          8   9  10  11  12  13  14  15
    2 trefle        16  17  18  19  20  21  22  23
    3 carreau       24  25  26  27  28  29  30  31

## Console du serveur

Dans le terminal de `make server` (le chef peut aussi envoyer `RAZ`, voir plus bas) :

    RAZ                    efface la partie en cours et revient en ATTENTE

Scores, réserve et places réservées sont effacés ; les humains connectés et les paramètres
restent. Les clients reçoivent `INFO PARTIE EFFACEE`, `SCORE 0 0`, `ETAT ATTENTE`.

## Précisions par rapport à la spec

Erreurs ajoutées au format `ERR TEXTE` :

| Message | Cas |
|---|---|
| `ERR INCONNU` | Mot-clé inconnu. |
| `ERR PARAM` | PARAM mal formé ou hors plage. |
| `ERR PAS LANCEE` | REJOUER ou RAZ en ATTENTE. |

Autres cas :

- Toute commande avant JOIN, ou un second JOIN, reçoit `ERR NOM`.
- Enchère mal placée à son tour (mauvaise couleur, ou ENCH pendant le jeu) et COUP pendant les
  enchères reçoivent `ERR COUP REFUSE`.
- Après REDONNE, le serveur enchaîne `ETAT EN COURS` et `DONNEUR P`, comme pour toute donne.
- `MANCHE` inclut la réserve remportée, pour que `SCORE` reste la somme des `MANCHE` ; un
  `INFO RESERVE N POUR EQUIPE E` le signale.
- Ordre en fin de manche : `PLI`, `CAPOT`, `LITIGE`, `INFO RESERVE`, `MANCHE`, `SCORE`, puis
  `GAGNANT` et `ETAT`. Chaque message n'est présent que si le cas s'applique.
- À la reconnexion pendant les enchères, `ENCHERES T` suit `RETOURNE`, pour que le client sache
  quel tour afficher.
- La main vide en fin de manche s'écrit `MAIN` sans paramètre.
- Après `PREND`, si le premier à jouer est un bot, il attend trois fois son délai habituel
  (3 s par défaut) : le temps de voir la carte prise.
- PETSCII : tout ce que le serveur envoie (majuscules, chiffres, espace, `-`) a le même code en
  ASCII et en PETSCII majuscules/graphiques. En réception, les majuscules PETSCII du mode
  minuscules ($C1-$DA) valent A-Z, sauf si l'octet suivant est $80-$BF (caractère UTF-8 envoyé
  par nc, qui reste `?`). Le terminateur reste LF : un client C64 ne doit pas finir ses lignes
  par le seul CR du PETSCII.

## Décisions d'interprétation des règles

- **Partenaire maître (5.3)** : tout est permis, y compris un atout inférieur à celui du
  partenaire qui a coupé.
- **Litige avec belote du preneur (5.4, 5.5)** : la belote est marquée tout de suite, seuls ses
  points de cartes vont en réserve. Une manche sans équipe gagnante (nouveau litige) cumule la
  réserve.
- **Inactivité (4.3)** : seul l'humain dont la table attend une action est jugé inactif (joueur
  à son tour, chef en FIN MANCHE ou FIN PARTIE). Jamais en ATTENTE. Toute ligne reçue compte
  comme activité.
- **Reconnexion (4.3)** : le serveur reconnaît un joueur à son nom, sans authentification. Un
  nouveau venu évite les places réservées tant qu'il en reste une autre.
- **Connexion fantôme (4.3)** : un JOIN au nom d'un humain encore assis, venant de la même
  adresse IP, remplace sa connexion (C64 redémarré sans LEAVE). Les autres reçoivent
  `INFO NOM RECONNECTE`. Contrepartie : deux joueurs derrière la même IP (NAT) qui choisissent
  le même nom ne sont plus départagés par un suffixe, le second prend la place du premier.
- **Table vide (4.2)** : sans humain, les bots s'arrêtent et la partie reste en suspens ; le
  prochain arrivant la reprend et devient chef.
- **Doublons de nom (4.3)** : suffixes essayés de 2 à 9, puis 1, pour respecter l'exemple
  JEAN → JEA2. Le nom BOT est réservé.
