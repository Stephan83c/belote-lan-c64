BELOTE LAN C64 - version @VERSION@
==================================

English first, français plus bas.

------------------------------------------------------------------
ENGLISH
------------------------------------------------------------------

Networked belote (French card game) for the C64 Ultimate: up to four
players around a table, empty seats played by bots.

STEP 1 - ENABLE THE COMMAND INTERFACE (IMPORTANT!)
  Without this, the game cannot reach the network and shows
  "COMMAND INTERFACE MISSING OR DISABLED".
  On your Ultimate: press C= + RESTORE to open the menu, go to
      Memory & ROMs  ->  Command Interface  ->  Enabled
  then choose "Save to Flash", otherwise the setting is lost when
  you switch off. (The wording may vary slightly with your firmware.)

STEP 2 - RUN THE GAME
  - Copy belote_lan.prg to the USB stick or SD card of your Ultimate,
    then run it from its file menu;
  - or, from a PC on the same network (REST API enabled):
      curl -X POST --data-binary @belote_lan.prg http://<ultimate-ip>/v1/runners:run_prg

STEP 3 - PLAY
  Press a key on the title screen. F1 changes the language. Type your
  name, press RETURN, pick a room (joystick in port 2, arrows or a
  digit), RETURN to sit down. The public server is pre-filled; F3 on
  the connection screen changes it.

Needs: a C64 Ultimate, Ultimate 64 or Ultimate-II+, on a network with
Internet access. It does NOT work in VICE (no Command Interface).
No C64 Ultimate? Use the PC client (belote-lan.exe or belote_lan.py).

Home page, sources, specification: https://github.com/Stephan83c/belote-lan-c64
itch.io: https://stephan83c.itch.io/belote-lan-c64

------------------------------------------------------------------
FRANÇAIS
------------------------------------------------------------------

Belote en réseau pour le C64 Ultimate : jusqu'à quatre joueurs autour
d'une table, les places vides sont tenues par des bots.

ÉTAPE 1 - ACTIVER LA COMMAND INTERFACE (IMPORTANT !)
  Sans cela, le jeu n'atteint pas le réseau et affiche
  « COMMAND INTERFACE ABSENTE OU INACTIVE ».
  Sur votre Ultimate : C= + RESTORE pour ouvrir le menu, puis
      Memory & ROMs  ->  Command Interface  ->  Enabled
  puis « Save to Flash », sinon le réglage est perdu à l'extinction.
  (L'intitulé peut varier selon la version du firmware.)

ÉTAPE 2 - LANCER LE JEU
  - Copiez belote_lan.prg sur la clé USB ou la carte SD de l'Ultimate,
    puis lancez-le depuis son menu de fichiers ;
  - ou, depuis un PC du même réseau (API REST activée) :
      curl -X POST --data-binary @belote_lan.prg http://<ip-ultimate>/v1/runners:run_prg

ÉTAPE 3 - JOUER
  Une touche sur l'écran titre. F1 change la langue. Tapez votre nom,
  RETURN, choisissez un salon (joystick en port 2, flèches ou un
  chiffre), RETURN pour s'asseoir. Le serveur public est pré-rempli ;
  F3 sur l'écran de connexion le change.

Il faut : un C64 Ultimate, Ultimate 64 ou Ultimate-II+, sur un réseau
avec accès à Internet. Ne fonctionne PAS dans VICE (pas de Command
Interface). Pas de C64 Ultimate ? Client PC (belote-lan.exe ou
belote_lan.py).

Page du projet, sources, spécification :
https://github.com/Stephan83c/belote-lan-c64
