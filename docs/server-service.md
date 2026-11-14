# Running the server as a service (Linux, systemd)

*English · [Français](serveur-service.md)*

With `make server`, the server stops when you close the terminal. As a **service**, it starts with
the PC, restarts if it crashes and runs without an open window. This guide uses a systemd **user
service**: no root needed to run it, and it runs under your account.

## 1. Prepare

The repository is cloned, for example in `~/c64-online`, and the server's venv exists:

```sh
cd ~/c64-online
make test        # creates server/.venv if needed and checks that the server works
```

The Makefile uses `python3.13` by default. If the machine only has `python3` (Debian, Ubuntu,
Fedora…), run `make test PYTHON=python3` the first time: the venv is then created with it.

Stop any `make server` started by hand (Ctrl+C): two servers cannot listen on the same port.

## 2. Install the service

The file `tools/belote.service` is ready. If needed, **adapt it** before copying it:

- the **path** `%h/c64-online/server` if the repository is elsewhere (`%h` = your home directory);
- the **port** `--port 6464` if it differs from `SERVEUR_PORT` in `config.mk`.

Then:

```sh
mkdir -p ~/.config/systemd/user
cp tools/belote.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now belote
```

`enable` starts it at each login, `--now` starts it right away.

## 3. Start with the PC, without logging in

A user service normally runs only while you are logged in. To have it start when the PC boots and
keep running after you log out:

```sh
sudo loginctl enable-linger $USER
```

(Only once. To undo: `sudo loginctl disable-linger $USER`.)

## 4. Check

```sh
systemctl --user status belote          # should say "active (running)"
journalctl --user -u belote -f          # live log (connections, errors); Ctrl+C to leave
ss -ltn | grep 6464                    # the port is listening
printf 'JOIN BOT2\n' | nc -w 3 localhost 6464   # should answer ERR NOM RESERVE
```

The last line really talks to the server without taking a seat at the table: BOT2 is a name
reserved for the bots, so the server refuses it.

On the C64, connect as usual to `SERVEUR_IP:SERVEUR_PORT`.

## 5. Day to day

| Action | Command |
|---|---|
| Stop | `systemctl --user stop belote` |
| Start | `systemctl --user start belote` |
| Restart (after a code update) | `systemctl --user restart belote` |
| Do not start at boot any more | `systemctl --user disable belote` |
| Show the last 50 log lines | `journalctl --user -u belote -n 50` |

After a `git pull` that changes the server: `make test`, then `systemctl --user restart belote`.
A restart wipes the game in progress.

## 6. On a Fedora VPS (server on the Internet)

To play from several homes, the server can run on a VPS. The C64s then call it at its public
address (`SERVEUR_IP` in `config.mk`). The VPS needs neither cc65 nor VICE.

```sh
sudo dnf install -y git make python3
git clone https://github.com/Stephan83c/belote-lan-c64.git ~/c64-online
cd ~/c64-online
make test PYTHON=python3          # creates the venv with Fedora's Python and runs the tests
```

Then install the service as in steps 2 to 4. Step 3 (`enable-linger`) is **essential** on a VPS:
nobody keeps a session open there.

**Firewall**: Fedora uses firewalld, not ufw:

```sh
sudo firewall-cmd --permanent --add-port=6464/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports      # should show 6464/tcp
```

If the hosting provider also has a firewall in its web interface (OVH: *Network Firewall*), open
TCP port 6464 there too.

**Check from home**: `nc -vz <VPS-address> 6464` should answer *succeeded* (or *open*), and
`printf 'JOIN BOT2\n' | nc -w 3 <VPS-address> 6464` should answer `ERR NOM RESERVE`.

**Exposed to the Internet**, the server accepts anyone:

- there is no password, and anyone who knows the address and port can join the table;
- a player is recognised by name: choosing the name of an absent player takes over their seat;
- the protocol is not encrypted (plain text, as on the local network).

That is harmless for a friendly game of belote. To limit visitors, you can use a port other than
6464 (in `config.mk` and in the service), or open the firewall only to your players' addresses:

```sh
sudo firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=<a player public ip> port port=6464 protocol=tcp accept'
```

(in that case, do not use `--add-port` above).

## 7. Good to know

- **"Failed to connect to user scope bus … XDG_RUNTIME_DIR not defined"**: the session (often
  opened with `su` or `sudo -u`) has no systemd user manager. Enable lingering (step 3), then tell
  the session and try again:
  ```sh
  sudo loginctl enable-linger $USER
  export XDG_RUNTIME_DIR=/run/user/$(id -u)
  systemctl --user daemon-reload
  ```
  The `export` must be repeated in each new session where the error comes back. The service itself
  does not need it.

- **No console**: as a service, the server does not read the keyboard, so the terminal's `RAZ`
  command does not exist. The host wipes the game from their C64 with **F4** then **Y** (**O** in
  French).
- **Firewall (local network, Debian/Ubuntu)**: the port must be open to the C64s, for example
  `sudo ufw allow from 192.168.1.0/24 to any port 6464 proto tcp`. For Fedora and an Internet
  server, see part 6.
- **Change the service**: edit `~/.config/systemd/user/belote.service`, then
  `systemctl --user daemon-reload` and `systemctl --user restart belote`.
- **Uninstall**:
  ```sh
  systemctl --user disable --now belote
  rm ~/.config/systemd/user/belote.service
  systemctl --user daemon-reload
  ```
