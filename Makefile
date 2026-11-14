VENV := server/.venv
# Python du serveur (bibliothèque standard seulement) : python3 suffit, ex. sur Fedora.
PYTHON ?= python3.13

# Adresses (serveur appelé par le C64, Ultimate pour make deploy) : voir config.mk.
include config.mk

# Client C64 (cc65). Adresse pré-remplie dans le champ SERVEUR (SPEC 2.1).
SERVEUR_DEFAUT := $(SERVEUR_IP):$(SERVEUR_PORT)
# Version affichée sur l'écran de connexion (celle de la release GitHub).
VERSION := 1.5
# Langue au démarrage (F1 la change sur l'écran de connexion) : 0 FR, 1 EN, 2 DE, 3 ES.
LANGUE ?= 0
PRG := build/belote_lan.prg
# Les fichiers générés (versionnés) sont nommés pour être refaits s'ils manquent.
SOURCES := $(sort $(wildcard c64/*.c c64/*.s) c64/titre_img.c c64/son_donnees.s c64/textes.c)
ENTETES := $(sort $(wildcard c64/*.h) c64/textes.h)
# Le programme s'arrête sous $C000 : écran, sprites et caractères vivent en $C000-$CFFF,
# l'image titre en $E000 (voir CLAUDE.md, mémoire du client).
CFLAGS := -t c64 -O -Or -DSERVEUR_DEFAUT='"$(SERVEUR_DEFAUT)"' -DVERSION='"$(VERSION)"' -DLANGUE_DEFAUT=$(LANGUE) -Wl -D,__HIMEM__=0xC000

.PHONY: all deploy vice demo vice-demo test server clean

all: $(PRG)

# Réglages compilés dans le PRG : s'ils changent (make LANGUE=1, SERVEUR_IP=...), build/options
# change et le PRG est refait, sans avoir à l'effacer.
OPTIONS := $(SERVEUR_DEFAUT) $(VERSION) $(LANGUE)
$(shell mkdir -p build; echo '$(OPTIONS)' | cmp -s - build/options || echo '$(OPTIONS)' > build/options)

$(PRG): $(SOURCES) $(ENTETES) Makefile config.mk build/options
	@mkdir -p build
	cl65 $(CFLAGS) -m build/belote_lan.map -o $@ $(SOURCES)
	@rm -f c64/*.o

# Avant d'envoyer, on tape F7 sur le C64 : si le client tourne, il quitte la table
# et ferme son socket. Un reset avec un socket ouvert le laisse ouvert dans
# l'Ultimate, et quelques-uns suffisent à bloquer la Command Interface.
deploy: $(PRG) test
	-@curl -s -m 3 -o /dev/null -X PUT "http://$(ULTIMATE)/v1/machine:writemem?address=0277&data=88" && \
	  curl -s -m 3 -o /dev/null -X PUT "http://$(ULTIMATE)/v1/machine:writemem?address=00C6&data=01" && sleep 1
	curl -sS -X POST --data-binary @$(PRG) http://$(ULTIMATE)/v1/runners:run_prg

# Musique et bruitages ; le .s généré est versionné.
c64/son_donnees.s: tools/musique.py
	python3 tools/musique.py

# Textes du client en quatre langues ; le .c généré est versionné.
c64/textes.c c64/textes.h: tools/textes.py
	python3 tools/textes.py

# Image de l'écran titre (Pillow) ; le .c généré est versionné.
c64/titre_img.c: tools/titre.py
	python3 tools/titre.py

vice: $(PRG)
	x64sc -autostart $(PRG)

# Client avec réseau simulé (c64/vice/faux_uci.c), pour voir les écrans de jeu dans VICE.
SCENARIO ?= 2
DEMO := build/demo$(SCENARIO).prg

demo: $(SOURCES) $(ENTETES) c64/vice/faux_uci.c Makefile
	@mkdir -p build
	cl65 -t c64 -O -Or -Ic64 -DSCENARIO=$(SCENARIO) -DLANGUE_DEFAUT=$(LANGUE) -Wl -D,__HIMEM__=0xC000 \
	  -o $(DEMO) $(filter-out c64/uci.c,$(SOURCES)) c64/vice/faux_uci.c
	@rm -f c64/*.o c64/vice/*.o

vice-demo: demo
	x64sc -autostart $(DEMO) -keybuf ' \x0djean\x0d'

test: $(VENV)/bin/pytest
	cd server && .venv/bin/pytest -q

server: $(VENV)/bin/pytest
	cd server && .venv/bin/python -m belote --port $(SERVEUR_PORT)

clean:
	rm -rf build

$(VENV)/bin/pytest:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -q -r server/requirements-dev.txt
