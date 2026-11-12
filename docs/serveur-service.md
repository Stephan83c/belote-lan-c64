# Faire tourner le serveur en service (Linux, systemd)

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
printf 'JOIN TEST\n' | nc -q1 localhost 6464   # le serveur répond BIENVENUE TEST ...
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

## 6. Bon à savoir

- **Pas de console** : en service, le serveur ne lit pas le clavier, donc la commande `RAZ` du
  terminal n'existe pas. Le chef efface la partie depuis son C64 avec **F4** puis **O**.
- **Pare-feu** : le port doit rester ouvert aux C64 du réseau local, par exemple
  `sudo ufw allow from 192.168.1.0/24 to any port 6464 proto tcp`. N'ouvrez pas ce port sur
  Internet : le serveur n'a aucune authentification.
- **Modifier le service** : éditez `~/.config/systemd/user/belote.service`, puis
  `systemctl --user daemon-reload` et `systemctl --user restart belote`.
- **Désinstaller** :
  ```sh
  systemctl --user disable --now belote
  rm ~/.config/systemd/user/belote.service
  systemctl --user daemon-reload
  ```
