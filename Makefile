VENV := server/.venv

# Client C64 (cc65). Adresse pré-remplie dans le champ SERVEUR (SPEC 2.1).
SERVEUR_DEFAUT ?= 192.168.1.55:6464
ULTIMATE ?= 192.168.1.27
PRG := build/belote_lan.prg
SOURCES := $(sort $(wildcard c64/*.c) c64/titre_img.c)
ENTETES := $(wildcard c64/*.h)
# Le programme s'arrête sous $C000 : écran et caractères vivent en $C000-$CFFF.
CFLAGS := -t c64 -O -Or -DSERVEUR_DEFAUT='"$(SERVEUR_DEFAUT)"' -Wl -D,__HIMEM__=0xC000

.PHONY: all deploy vice demo vice-demo test server clean

all: $(PRG)

$(PRG): $(SOURCES) $(ENTETES) Makefile
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
	cl65 -t c64 -O -Or -Ic64 -DSCENARIO=$(SCENARIO) -Wl -D,__HIMEM__=0xC000 \
	  -o $(DEMO) $(filter-out c64/uci.c,$(SOURCES)) c64/vice/faux_uci.c
	@rm -f c64/*.o c64/vice/*.o

vice-demo: demo
	x64sc -autostart $(DEMO) -keybuf ' \x0djean\x0d'

test: $(VENV)/bin/pytest
	cd server && .venv/bin/pytest -q

server: $(VENV)/bin/pytest
	cd server && .venv/bin/python -m belote

clean:
	rm -rf build

$(VENV)/bin/pytest:
	python3.13 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r server/requirements-dev.txt
