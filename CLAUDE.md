# Projet : jeu online C64

La spécification complète du jeu est dans SPEC.md : elle fait foi (règles, protocole, écran).

## Matériel
- C64 Ultimate sur le LAN : 192.168.1.27 (API REST active, Command Interface activée)
- Serveur Python sur ce PC : 192.168.1.55, port TCP 6464

## Outils
- Client C64 : cc65 (cl65), cible c64. Assembleur annexe : 64tass
- Serveur : Python 3.13, asyncio, venv dans server/.venv
- Émulateur pour tests rapides : VICE (x64sc)

## Commandes
- `make` : compile c64/ vers build/belote_lan.prg
- `make deploy` : envoie et lance le PRG sur l'Ultimate
  (curl -X POST --data-binary @build/belote_lan.prg http://192.168.1.27/v1/runners:run_prg)
- `make server` : lance le serveur Python

## Règles
- Réseau côté C64 via l'Ultimate Command Interface ($DF1C-$DF1F), cible réseau.
- Protocole texte ASCII, une ligne par message terminée par LF (64 octets max), documenté dans SPEC.md section 7 et protocol.md : il doit rester débogable avec nc.
- Toujours tester le serveur avec pytest avant de déployer.
