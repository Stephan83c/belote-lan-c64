# Le client C64 (make, make deploy) viendra s'ajouter ici.
VENV := server/.venv

.PHONY: test server

test: $(VENV)/bin/pytest
	cd server && .venv/bin/pytest -q

server: $(VENV)/bin/pytest
	cd server && .venv/bin/python -m belote

$(VENV)/bin/pytest:
	python3.13 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r server/requirements-dev.txt
