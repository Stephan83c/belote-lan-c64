# Projet : BELOTE LAN C64 (jeu de belote en réseau pour C64)

La spécification complète du jeu est dans SPEC.fr.md : elle fait foi (règles, protocole, écran).

Documentation en double : français (`*.fr.md`, `docs/serveur-service.md`) pour Stéphan et les
francophones, anglais sous les noms principaux (README.md, SPEC.md, protocol.md,
`docs/server-service.md`) pour GitHub. Toute modification de l'une se reporte dans l'autre.

## Matériel
- C64 Ultimate sur le LAN : 192.168.1.27 (API REST active, Command Interface activée)
- Serveur public (adresse par défaut du C64, SERVEUR_IP dans config.mk), port 6464, sur un
  VPS que Stéphan met à jour lui-même (git pull, make test PYTHON=python3, systemctl --user
  restart belote ; voir docs/serveur-service.md)
- Serveur de test sur ce PC : 192.168.1.55:6464 (`make server`, puis
  `make deploy SERVEUR_IP=192.168.1.55` ; le PRG est refait de lui-même quand SERVEUR_IP, LANGUE
  ou VERSION changent, voir build/options) ; redéployer ensuite le PRG normal (`make deploy`)

## Outils
- Client C64 : cc65 (cl65), cible c64 ; les .s (lecteur SID) sont assemblés par ca65 via cl65
- Serveur : Python 3.13, asyncio, venv dans server/.venv
- Émulateur pour tests rapides : VICE (x64sc)

## Commandes
- `config.mk` : SERVEUR_IP, SERVEUR_PORT, ULTIMATE (surchargeables : `make deploy ULTIMATE=...`)
- `make` : compile c64/ vers build/belote_lan.prg ; `make LANGUE=0..3` choisit la langue au
  démarrage (FR, EN, DE, ES ; F1 la change sur le C64) ; `make clean` efface build/
- `VERSION` (Makefile) : numéro affiché sur l'écran de connexion, celui de la release GitHub
- `make deploy` : pytest, tape F7 sur le C64 (le client quitte la table et ferme son
  socket), puis envoie et lance le PRG sur l'Ultimate
  (curl -X POST --data-binary @build/belote_lan.prg http://192.168.1.27/v1/runners:run_prg)
- `make server` : lance le serveur Python
- `make pc` : client PC (pc/belote_lan.py, terminal 80x24, bibliothèque standard, Python 3.8+) sur
  le serveur de config.mk ; `--auto` (caché) joue seul, pour les essais. Sa VERSION doit égaler celle
  du Makefile (test). belote-lan.exe : .github/workflows/client-windows.yml (PyInstaller sur
  windows-latest), joint automatiquement à chaque release publiée, ou lancé à la main (artefact)
- `make paquet-serveur` : pytest puis build/belote-serveur-vX.Y.tar.gz et .zip, à joindre à la
  release (serveur sans dépendance, service, notes FR/EN de tools/paquet-serveur/)
- `make vice` : le vrai client dans VICE (écran de connexion seulement : VICE n'émule pas
  la Command Interface)
- `make vice-demo SCENARIO=1..8` : client avec réseau simulé (c64/vice/faux_uci.c) ;
  `make demo` compile sans lancer VICE
- `python3 tools/musique.py` : régénère la musique et les bruitages (c64/son_donnees.s, versionné ;
  lecteur SID dans c64/son.s, branché sur l'IRQ du KERNAL, page zéro $FB-$FE)
- `python3 tools/textes.py` : régénère les textes du client en 4 langues (c64/textes.c et .h,
  versionnés ; refuse un texte trop large ou un caractère hors des 64 de l'ECM)
- `python3 tools/titre.py [apercu.png]` : régénère l'écran titre (c64/titre_img.c, versionné, compressé :
  décodé par c64/titre_dec.s ; demande Pillow et la ROM caractères de VICE)

## Mémoire du client (banque VIC 3)
- Programme sous $C000 (__HIMEM__ dans le Makefile), pile C de 512 octets (__STACKSIZE__, mesurée à
  58 octets au plus dans VICE en v2.0). L'image titre et son décompresseur sont dans le segment ONCE :
  un constructeur (c64/titre_dec.s) la décompresse au chargement, avant zerobss et main, puis la place
  sert aux variables. Deux marges dans build/belote_lan.map : fin du BSS sous $BE00 (environ 4,7 Ko) et
  fin du segment ONCE sous $C000 (environ 1,7 Ko : la vraie limite pour le code) ; au-delà, ld65 refuse.
  Le constructeur règle bordure, fond et banque VIC ; titre() est appelé avant ecran_init().
- $C000 écran (ECM), $C3F8 pointeurs de sprites, $C400-$C47F sprites de la carte qui glisse (et du pli ramassé),
  $C800 jeu de caractères en RAM, $E000 bitmap de l'écran titre (RAM sous le KERNAL, libre après)
- ECM : 64 caractères seulement. Redessinés : @ £ ↑ ← (♠ ♥ ♣ ♦), # (tapis), " $ % & (coins des
  cartes), < (trait fin des séparations) ; ils s'affichent « ? » si on les écrit en texte.
- Couleurs (v1.7) : bordure brune, bandeaux noirs L0 et L24 ($D023), traits jaunes L11 et L20.
- Joystick en port 2 (driver statique de cc65, joy_read(JOY_2)) ; jouables() dans proto.c recopie
  les règles du serveur (moteur.coups_legaux) : à garder en accord si les règles changent.
  Le client PC en a une copie Python (pc/belote_lan.py), comparée au serveur par les tests.

## Vérifier
- Client dans VICE sans fenêtre : `x64sc -console -warp +sound -autostartprgmode 1
  -limitcycles 25000000 -exitscreenshot f.png -autostart build/demoN.prg -keybuf ' \x0djean\x0d'`
  (une capture par lancement ; pour une animation, plusieurs lancements à -limitcycles croissants)
- Sur le C64 : `make deploy`, écran lu par l'API REST (voir plus bas)
- Pile C : VICE avec `-raminitstartvalue 85 -raminitvalueinvert 0 -raminitpatterninvert 0
  -raminitrandomchance 0 -remotemonitor`, puis `m be00 bfff` par nc sur le port 6510 : la plus basse
  adresse différente de $55 donne la profondeur (sans couper le bruit aléatoire, on croit la pile pleine)
- Client PC : captures en lançant pc/belote_lan.py dans un pseudo-terminal 80x24 rendu par pyte
  et Pillow (venv à part, pas dans le dépôt) ; docs/pc.png (FR) et docs/pc-en.png (EN)

## Règles
- Réseau côté C64 via l'Ultimate Command Interface ($DF1C-$DF1F), cible réseau.
- Protocole texte ASCII, une ligne par message terminée par LF (64 octets max), documenté dans SPEC.fr.md section 7 et protocol.fr.md (traductions SPEC.md, protocol.md) : il doit rester débogable avec nc.
- Toujours tester le serveur avec pytest avant de déployer.

## Pièges de cc65 (constatés)
- `(b - a) * k / n` avec b < a (int) et k unsigned char donne un résultat faux : la carte qui glisse
  montait en zigzag. Calculer sans différence négative (voir etape() dans c64/vue.c).
- Les calculs 16 bits (multiplication, division) sont lents : les positions de 8 sprites prenaient
  plus d'une image ; sprite_carte() prend à lui seul plus d'une image. Calculer la position avant
  d'attendre l'image (deplacer() dans c64/vue.c), dessiner le sprite pendant qu'il est caché.
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
