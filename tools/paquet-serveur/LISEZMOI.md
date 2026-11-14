# Serveur BELOTE LAN C64 — version @VERSION@

*Français · [English](README.md)*

Le serveur de la belote en réseau pour C64 Ultimate : il applique les règles, joue les bots et
relie jusqu'à quatre C64 autour d'une table. Il est écrit en Python et n'utilise que la
bibliothèque standard : **rien d'autre à installer**.

Sources, client C64 et spécification complète : https://github.com/Stephan83c/belote-lan-c64

## 1. Ce qu'il faut

- **Python 3.10 ou plus récent** (testé avec 3.13) : `python3 --version`.
- Linux, macOS ou Windows. Pour jouer depuis plusieurs maisons : une machine joignable depuis
  Internet (un VPS par exemple) et le **port TCP 6464** ouvert.

## 2. Installer et lancer

```sh
cd ~
tar xzf belote-serveur-v@VERSION@.tar.gz      # crée ~/belote-serveur
cd ~/belote-serveur
python3 -m belote --port 6464
```

Le serveur affiche `serveur de belote sur 0.0.0.0:6464`. Il s'arrête avec Ctrl+C. Dans ce
terminal, la commande `RAZ` (puis Entrée) efface la partie en cours.

Sous Windows : extraire le `.zip`, ouvrir un terminal dans le dossier `belote-serveur`, puis
`py -m belote --port 6464`, et autoriser Python dans le pare-feu quand Windows le demande.

Options :

| Option | Par défaut | Rôle |
|---|---|---|
| `--port` | 6464 | Port TCP écouté. |
| `--host` | 0.0.0.0 | Adresse écoutée (toutes les interfaces). |
| `--delai-bot` | 1.0 | Secondes avant chaque action d'un bot. |
| `--delai-manche` | 10 | Secondes de pause en fin de manche avant la suivante. |

## 3. Vérifier

Depuis la même machine (ou une autre, avec l'adresse du serveur) :

```sh
printf 'JOIN BOT2\n' | nc -w 3 localhost 6464
```

La réponse doit être `ERR NOM RESERVE` : le serveur répond, sans qu'une place soit prise (BOT2 est
un nom réservé aux bots).

Sur le C64, lancer `belote_lan.prg` (release GitHub) et taper l'adresse du serveur dans le champ
SERVEUR de l'écran de connexion, par exemple `192.168.1.10:6464`.

## 4. Service (Linux, démarrage automatique)

Pour que le serveur démarre avec la machine et redémarre s'il plante, sans terminal ouvert, avec
un service systemd *utilisateur* (pas besoin d'être root pour le faire tourner) :

```sh
mkdir -p ~/.config/systemd/user
cp ~/belote-serveur/belote.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now belote
sudo loginctl enable-linger $USER     # une fois : démarre au boot, même sans session ouverte
```

Le fichier suppose le paquet dans `~/belote-serveur` et Python en `/usr/bin/python3` : l'adapter
sinon. Ensuite :

| Action | Commande |
|---|---|
| État | `systemctl --user status belote` |
| Journal en direct | `journalctl --user -u belote -f` |
| Redémarrer | `systemctl --user restart belote` |
| Arrêter | `systemctl --user stop belote` |

Sous systemd, il n'y a pas de console : le chef de table efface la partie avec **F4** sur son C64.

## 5. Pare-feu

- Fedora (firewalld) : `sudo firewall-cmd --permanent --add-port=6464/tcp && sudo firewall-cmd --reload`
- Debian, Ubuntu (ufw) : `sudo ufw allow 6464/tcp`
- Si l'hébergeur a aussi un pare-feu dans son interface web, y ouvrir le port TCP 6464.

Depuis chez vous, `nc -vz <adresse> 6464` doit répondre *succeeded* (ou *open*).

## 6. Mettre à jour

Extraire la nouvelle version par-dessus l'ancienne, puis redémarrer (la partie en cours est
effacée) :

```sh
cd ~
tar xzf belote-serveur-vX.Y.tar.gz
systemctl --user restart belote       # ou relancer python3 -m belote
```

## 7. Tests (facultatif)

```sh
cd ~/belote-serveur
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt     # pytest
.venv/bin/pytest -q
```

## 8. À savoir

- Il n'y a pas de mot de passe : quiconque connaît l'adresse et le port peut rejoindre la table.
  Un joueur est reconnu à son nom, et le protocole n'est pas chiffré. Une connexion qui ne
  rejoint pas la table en une minute est fermée, et le tchat est limité à 3 messages par joueur
  sur 10 secondes.
- Une seule table de 4 places ; les places libres sont tenues par des bots.
- Le protocole est du texte, une ligne par message : on peut jouer ou déboguer avec `nc` (voir
  `protocol.fr.md`).
- Licence GPL v3 (fichier `LICENSE`).
