# BELOTE LAN C64 server — version @VERSION@

*English · [Français](LISEZMOI.md)*

The server for networked belote on the C64 Ultimate: it applies the rules, plays the bots and
links up to four C64s around a table. It is written in Python and uses only the standard
library: **nothing else to install**.

Sources, C64 client and full specification: https://github.com/Stephan83c/belote-lan-c64

## 1. Requirements

- **Python 3.10 or later** (tested with 3.13): `python3 --version`.
- Linux, macOS or Windows. To play from several homes: a machine reachable from the Internet (a
  VPS for example) with **TCP port 6464** open.

## 2. Install and run

```sh
cd ~
tar xzf belote-serveur-v@VERSION@.tar.gz      # creates ~/belote-serveur
cd ~/belote-serveur
python3 -m belote --port 6464
```

The server prints `serveur de belote sur 0.0.0.0:6464`. Ctrl+C stops it. In that terminal, the
`RAZ` command (then Enter) wipes the game in progress.

On Windows: extract the `.zip`, open a terminal in the `belote-serveur` folder, then
`py -m belote --port 6464`, and allow Python through the firewall when Windows asks.

Options:

| Option | Default | Role |
|---|---|---|
| `--port` | 6464 | TCP port to listen on. |
| `--host` | 0.0.0.0 | Address to listen on (all interfaces). |
| `--delai-bot` | 1.0 | Seconds before each bot action. |
| `--delai-manche` | 10 | Seconds of pause at the end of a round before the next one. |

## 3. Check

From the same machine (or another one, with the server's address):

```sh
printf 'JOIN BOT2\n' | nc -w 3 localhost 6464
```

The answer should be `ERR NOM RESERVE`: the server answers, without a seat being taken (BOT2 is a
name reserved for the bots).

On the C64, run `belote_lan.prg` (GitHub release) and type the server's address in the SERVER
field of the connection screen, for example `192.168.1.10:6464`.

## 4. Service (Linux, automatic start)

To have the server start with the machine and restart if it crashes, without an open terminal,
use a systemd *user* service (no root needed to run it):

```sh
mkdir -p ~/.config/systemd/user
cp ~/belote-serveur/belote.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now belote
sudo loginctl enable-linger $USER     # once: starts at boot, even with nobody logged in
```

The file assumes the package in `~/belote-serveur` and Python at `/usr/bin/python3`: adapt it
otherwise. Then:

| Action | Command |
|---|---|
| Status | `systemctl --user status belote` |
| Live log | `journalctl --user -u belote -f` |
| Restart | `systemctl --user restart belote` |
| Stop | `systemctl --user stop belote` |

Under systemd there is no console: the table's host wipes the game with **F4** on their C64.

## 5. Firewall

- Fedora (firewalld): `sudo firewall-cmd --permanent --add-port=6464/tcp && sudo firewall-cmd --reload`
- Debian, Ubuntu (ufw): `sudo ufw allow 6464/tcp`
- If the hosting provider also has a firewall in its web interface, open TCP port 6464 there.

From home, `nc -vz <address> 6464` should answer *succeeded* (or *open*).

## 6. Update

Extract the new version over the old one, then restart (the game in progress is wiped):

```sh
cd ~
tar xzf belote-serveur-vX.Y.tar.gz
systemctl --user restart belote       # or start python3 -m belote again
```

## 7. Tests (optional)

```sh
cd ~/belote-serveur
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt     # pytest
.venv/bin/pytest -q
```

## 8. Good to know

- There is no password: anyone who knows the address and port can join the table. A player is
  recognised by name, and the protocol is not encrypted. A connection that does not join the
  table within a minute is closed, and the chat is limited to 3 messages per player over 10
  seconds.
- A single 4-seat table; free seats are held by bots.
- The protocol is plain text, one line per message: you can play or debug with `nc` (see
  `protocol.md`).
- GPL v3 licence (`LICENSE` file).
