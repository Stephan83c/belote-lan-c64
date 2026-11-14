# Projet : BELOTE LAN C64 (jeu de belote en réseau pour C64)

La spécification complète du jeu est dans SPEC.fr.md : elle fait foi (règles, protocole, écran).

Documentation en double : français (`*.fr.md`, `docs/serveur-service.md`) pour Stéphan et les
francophones, anglais sous les noms principaux (README.md, SPEC.md, protocol.md,
`docs/server-service.md`) pour GitHub. Toute modification de l'une se reporte dans l'autre.

## Matériel
- C64 Ultimate sur le LAN : 192.168.1.27 (API REST active, Command Interface activée)
- Serveur Python sur ce PC : 192.168.1.55, port TCP 6464

## Outils
- Client C64 : cc65 (cl65), cible c64. Assembleur annexe : 64tass
- Serveur : Python 3.13, asyncio, venv dans server/.venv
- Émulateur pour tests rapides : VICE (x64sc)

## Commandes
- `config.mk` : SERVEUR_IP, SERVEUR_PORT, ULTIMATE (surchargeables : `make deploy ULTIMATE=...`)
- `make` : compile c64/ vers build/belote_lan.prg
- `make deploy` : pytest, tape F7 sur le C64 (le client quitte la table et ferme son
  socket), puis envoie et lance le PRG sur l'Ultimate
  (curl -X POST --data-binary @build/belote_lan.prg http://192.168.1.27/v1/runners:run_prg)
- `make server` : lance le serveur Python
- `make vice` : le vrai client dans VICE (écran de connexion seulement : VICE n'émule pas
  la Command Interface)
- `make vice-demo SCENARIO=1..6` : client avec réseau simulé (c64/vice/faux_uci.c) ;
  `make demo` compile sans lancer VICE
- `python3 tools/musique.py` : régénère la musique et les bruitages (c64/son_donnees.s, versionné ;
  lecteur SID dans c64/son.s, branché sur l'IRQ du KERNAL, page zéro $FB-$FE)
- `python3 tools/textes.py` : régénère les textes du client en 4 langues (c64/textes.c et .h,
  versionnés ; refuse un texte trop large ou un caractère hors des 64 de l'ECM)
- `python3 tools/titre.py [apercu.png]` : régénère l'écran titre (c64/titre_img.c, versionné ;
  demande Pillow et la ROM caractères de VICE)

## Règles
- Réseau côté C64 via l'Ultimate Command Interface ($DF1C-$DF1F), cible réseau.
- Protocole texte ASCII, une ligne par message terminée par LF (64 octets max), documenté dans SPEC.fr.md section 7 et protocol.fr.md (traductions SPEC.md, protocol.md) : il doit rester débogable avec nc.
- Toujours tester le serveur avec pytest avant de déployer.

## Pièges de cc65 (constatés)
- `(b - a) * k / n` avec b < a (int) et k unsigned char donne un résultat faux : la carte qui glisse
  montait en zigzag. Calculer sans différence négative (voir etape() dans c64/vue.c).
- Le serveur envoie MAIN juste après JOUE et les deux sont traités avant le dessin : tout ce qui
  dépend de l'ancienne main (emplacement de la carte jouée) doit être relevé à la réception de JOUE.

## Pièges de l'Ultimate (constatés)
- Lecture réseau sans données : longueur -1 et statut « 02,NO DATA: 11 » (EAGAIN). Après
  fermeture par le serveur : « CONNECTION CLOSED BY HOST » puis « NO DATA: 9 » (EBADF),
  l'Ultimate ayant libéré le socket. Ne plus jamais écrire ni fermer ce numéro ensuite : il
  peut être réutilisé par l'Ultimate, et y toucher bloque la Command Interface (état $15).
- Une fois bloquée ($DF1C reste à $15), ni reset, ni PUT /v1/machine:reboot, ni abort par
  writemem ne la relancent : il faut couper l'alimentation de l'Ultimate.
- Un reset du C64 laisse ouverts ses sockets dans l'Ultimate : quitter avec F7 avant (make
  deploy le fait). Le serveur reprend la place d'un JOIN même nom + même IP (SPEC 4.3).
- L'API REST lit l'écran : GET /v1/machine:readmem?address=C000&length=1000 (écran en $C000,
  codes écran ECM) ; on tape au clavier en écrivant le tampon $0277 et son compteur $C6.
