# Faire tourner le serveur en service (Linux, systemd)

*[English](server-service.md) · Français*

Avec `make server`, le serveur s'arrête quand on ferme le terminal. En **service**, il démarre tout
seul avec le PC, redémarre s'il plante et tourne sans fenêtre ouverte. Cette fiche utilise un
**service utilisateur** systemd : pas besoin d'être root pour le faire tourner, et il s'exécute avec
votre compte.

## 1. Préparer

Le dépôt est cloné, par exemple dans `~/c64-online`, et le venv du serveur existe :

```sh
cd ~/c64-online
make test        # crée server/.venv au besoin et vérifie que le serveur fonctionne
```

Arrêtez un éventuel `make server` lancé à la main (Ctrl+C) : deux serveurs ne peuvent pas écouter le
même port.

## 2. Installer le service

Le fichier `tools/belote.service` est prêt. S'il le faut, **adaptez-le** avant de le copier :

- le **chemin** `%h/c64-online/server` si le dépôt est ailleurs (`%h` = votre dossier personnel) ;
- le **port** `--port 6464` s'il diffère de `SERVEUR_PORT` dans `config.mk`.

Puis :

```sh
mkdir -p ~/.config/systemd/user
cp tools/belote.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now belote
```

`enable` le lance à chaque ouverture de session, `--now` le démarre tout de suite.

## 3. Démarrer avec le PC, sans ouvrir de session

Un service utilisateur ne tourne normalement que pendant que vous êtes connecté. Pour qu'il démarre
dès l'allumage du PC et continue après la déconnexion :

```sh
sudo loginctl enable-linger $USER
```

(À faire une seule fois. Pour annuler : `sudo loginctl disable-linger $USER`.)

## 4. Vérifier

```sh
systemctl --user status belote          # doit indiquer « active (running) »
journalctl --user -u belote -f          # journal en direct (connexions, erreurs) ; Ctrl+C pour sortir
ss -ltn | grep 6464                    # le port est bien en écoute
```

Sur le C64, connectez-vous comme d'habitude à `SERVEUR_IP:SERVEUR_PORT`.

## 5. Au quotidien

| Action | Commande |
|---|---|
| Arrêter | `systemctl --user stop belote` |
| Démarrer | `systemctl --user start belote` |
| Redémarrer (après une mise à jour du code) | `systemctl --user restart belote` |
| Ne plus lancer au démarrage | `systemctl --user disable belote` |
| Voir les 50 dernières lignes du journal | `journalctl --user -u belote -n 50` |

Après un `git pull` qui modifie le serveur : `make test`, puis `systemctl --user restart belote`.
Un redémarrage efface la partie en cours.

## 6. Sur un VPS Fedora (serveur sur Internet)

Pour jouer depuis plusieurs maisons, le serveur peut tourner sur un VPS. Les C64 l'appellent alors à
son adresse publique (`SERVEUR_IP` dans `config.mk`). Sur le VPS, il n'y a besoin ni de cc65 ni de
VICE.

```sh
sudo dnf install -y git make python3
git clone https://github.com/Stephan83c/belote-lan-c64.git ~/c64-online
cd ~/c64-online
make test PYTHON=python3          # crée le venv avec le Python de Fedora et lance les tests
```

Installez ensuite le service comme aux étapes 2 à 4. L'étape 3 (`enable-linger`) est
**indispensable** sur un VPS : personne n'y garde de session ouverte.

**Pare-feu** : Fedora utilise firewalld, pas ufw :

```sh
sudo firewall-cmd --permanent --add-port=6464/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports      # doit afficher 6464/tcp
```

Si l'hébergeur a aussi un pare-feu dans son interface web (OVH : *Network Firewall*), ouvrez-y le
port TCP 6464 également.

**Vérifier depuis chez vous** : `nc -vz 51.38.50.79 6464` doit répondre *succeeded* (ou *open*).

**Exposé sur Internet**, le serveur accepte n'importe qui :

- il n'y a pas de mot de passe, et quiconque connaît l'adresse et le port peut rejoindre la table ;
- un joueur est reconnu à son nom : choisir le nom d'un absent permet de reprendre sa place ;
- le protocole n'est pas chiffré (c'est du texte simple, comme sur le réseau local).

C'est sans enjeu pour une partie de belote entre amis. Pour limiter les visiteurs, vous pouvez
utiliser un autre port que 6464 (dans `config.mk` et dans le service), ou n'ouvrir le pare-feu
qu'aux adresses de vos joueurs :

```sh
sudo firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=<ip publique d un joueur> port port=6464 protocol=tcp accept'
```

(dans ce cas, n'utilisez pas `--add-port` ci-dessus).

## 7. Bon à savoir

- **« Failed to connect to user scope bus … XDG_RUNTIME_DIR not defined »** : la session (souvent
  ouverte par `su` ou `sudo -u`) n'a pas de gestionnaire systemd utilisateur. Activez le linger
  (étape 3), puis indiquez-le à la session et recommencez :
  ```sh
  sudo loginctl enable-linger $USER
  export XDG_RUNTIME_DIR=/run/user/$(id -u)
  systemctl --user daemon-reload
  ```
  Le `export` est à refaire dans chaque nouvelle session où l'erreur revient. Le service, lui, n'en
  a pas besoin.

- **Pas de console** : en service, le serveur ne lit pas le clavier, donc la commande `RAZ` du
  terminal n'existe pas. Le chef efface la partie depuis son C64 avec **F4** puis **O** (Y, J ou S dans les autres langues).
- **Pare-feu (réseau local, Debian/Ubuntu)** : le port doit être ouvert aux C64, par exemple
  `sudo ufw allow from 192.168.1.0/24 to any port 6464 proto tcp`. Pour Fedora et un serveur sur
  Internet, voir la partie 6.
- **Modifier le service** : éditez `~/.config/systemd/user/belote.service`, puis
  `systemctl --user daemon-reload` et `systemctl --user restart belote`.
- **Désinstaller** :
  ```sh
  systemctl --user disable --now belote
  rm ~/.config/systemd/user/belote.service
  systemctl --user daemon-reload
  ```
