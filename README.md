# BELOTE LAN C64

Belote en réseau local pour **Commodore 64 Ultimate**. Jusqu'à quatre joueurs humains, chacun sur
son C64. Les places libres sont tenues par des bots. Un serveur Python sur le PC arbitre la partie.

![Écran titre](docs/titre.png)

| Table de jeu | Enchères, second tour |
|---|---|
| ![Table](docs/table.png) | ![Enchères](docs/encheres.png) |

## Ce qu'il y a dedans

- **Client C64** (`c64/`, C avec cc65) : l'écran est en mode couleur étendue (ECM), avec des cartes
  rouges et noires sur un tapis de feutre vert. Le réseau passe par la
  *Ultimate Command Interface* ($DF1C-$DF1F). Un écran titre en bitmap multicolore est généré par
  `tools/titre.py`.
- **Serveur** (`server/`, Python 3.13 asyncio) : il applique les règles de la belote classique, gère
  les bots, la reconnexion, l'inactivité et le tchat.
- **Protocole** : texte ASCII, une ligne par message terminée par LF (64 octets au maximum), sur le
  port TCP 6464. On peut jouer ou déboguer avec `nc` (voir [protocol.md](protocol.md)).
- **Spécification complète** (règles, protocole, écran) : [SPEC.md](SPEC.md).

## Démarrer

Il faut un C64 Ultimate (ou un Ultimate 64 / Ultimate-II+) avec l'API REST et la Command Interface
activées, cc65, Python 3.13 et, en option, VICE.

```sh
make server                          # serveur sur le port 6464 (crée le venv au besoin)
make deploy ULTIMATE=192.168.1.27    # tests, compilation, envoi et lancement sur le C64
```

Sur le C64 : une touche passe l'écran titre. Saisissez ensuite l'adresse du serveur
(`IP:6464`, pré-remplie par `SERVEUR_DEFAUT` à la compilation) et un nom de 5 caractères.
Le premier arrivé devient le chef.

Le port 6464 doit être ouvert sur le PC, par exemple
`sudo ufw allow from 192.168.1.0/24 to any port 6464 proto tcp`.

## Touches

| Touche | Action |
|---|---|
| 1-4 | Enchères : prendre (à la couleur retournée au 1er tour, à une autre au 2e) ou passer |
| 1-8 | Jouer la carte affichée sous ce numéro |
| F1 | Chef, en attente : réglages (points pour gagner, délai d'inactivité) |
| F2 | Chef : lancer la partie |
| F3 | Tchat (30 caractères) |
| F4 | Chef : effacer la partie en cours (confirmation par O) |
| F5 | Chef : manche suivante, ou nouvelle partie |
| F7 | Quitter la table (un bot prend la place) |
| F8 | Règles du jeu |

## Développement

```sh
make                         # build/belote_lan.prg
make test                    # tests du serveur (pytest)
make vice                    # écran de connexion dans VICE (VICE n'émule pas la Command Interface)
make vice-demo SCENARIO=1..5 # client avec un réseau simulé, pour voir les écrans de jeu
python3 tools/titre.py       # régénère l'écran titre (Pillow)
```

Dans le terminal du serveur, `RAZ` efface la partie en cours. Les particularités de l'Ultimate
constatées sur le matériel (sockets libérés, Command Interface bloquée) sont notées dans
[CLAUDE.md](CLAUDE.md).

## Auteurs

Stéphan ([@Stephan83c](https://github.com/Stephan83c)), avec Claude (Anthropic) comme co-auteur :
conception et code écrits ensemble avec Claude Code.

## Licence

Logiciel libre sous licence MIT : voir [LICENSE](LICENSE). Vous pouvez l'utiliser, le modifier et le
redistribuer librement, en gardant la mention de copyright.
