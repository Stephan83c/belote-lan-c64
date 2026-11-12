VENV := server/.venv

# Client C64 (cc65). Adresse pré-remplie dans le champ SERVEUR (SPEC 2.1).
SERVEUR_DEFAUT ?= 192.168.1.55:6464
ULTIMATE ?= 192.168.1.27
PRG := build/belote_lan.prg
SOURCES := $(wildcard c64/*.c)
ENTETES := $(wildcard c64/*.h)
# Le programme s'arrête sous $C000 : écran et caractères vivent en $C000-$CFFF.
CFLAGS := -t c64 -O -Or -DSERVEUR_DEFAUT='"$(SERVEUR_DEFAUT)"' -Wl -D,__HIMEM__=0xC000

.PHONY: all deploy vice test server clean

all: $(PRG)

$(PRG): $(SOURCES) $(ENTETES) Makefile
	@mkdir -p build
	cl65 $(CFLAGS) -m build/belote_lan.map -o $@ $(SOURCES)
	@rm -f c64/*.o

deploy: $(PRG) test
	curl -sS -X POST --data-binary @$(PRG) http://$(ULTIMATE)/v1/runners:run_prg

vice: $(PRG)
	x64sc -autostart $(PRG)

test: $(VENV)/bin/pytest
	cd server && .venv/bin/pytest -q

server: $(VENV)/bin/pytest
	cd server && .venv/bin/python -m belote

clean:
	rm -rf build

$(VENV)/bin/pytest:
	python3.13 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r server/requirements-dev.txt
