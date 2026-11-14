# Belote server protocol

*English · [Français](protocol.fr.md)*

The reference is `SPEC.md` section 7: ASCII text, one message per line ending in LF, 64 bytes at
most, TCP port 6464. This file sums up how to play by hand and records what the spec leaves open.

Keywords are French and stay so in every language of the client, which translates what it shows.
Glossary: JOIN join, LANCER start, ENCH bid, PASSE pass, COUP play a card, REJOUER play again,
RAZ reset, TCHAT chat, BIENVENUE welcome, SIEGE seat, CHEF host, ETAT state, ATTENTE waiting,
EN COURS in progress, FIN MANCHE end of round, FIN PARTIE end of game, DONNEUR dealer, MAIN hand,
RETOURNE turned-up card, ENCHERES bidding round, TOUR turn, PREND takes, JOUE plays, PLI trick,
MANCHE round score, LITIGE tie, GAGNANT winner, CIBLE target score, INACTIF idle timeout.

## Playing with nc

    make server            # in one terminal
    nc localhost 6464      # in another

    JOIN JEAN              join (seat P0 and host if the table is empty)
    PARAM CIBLE 500        optional, host, before the start
    LANCER                 start
    ENCH 1 / PASSE         on your TOUR, during bidding (suit 1 = hearts)
    COUP 14                on your TOUR, during play (card 14 = king of hearts)
    REJOUER                host: at ETAT FIN MANCHE or FIN PARTIE
    RAZ                    host: wipes the game in progress (like RAZ on the console)
    TCHAT HELLO            any time after JOIN
    LEAVE                  leave

Card = suit × 8 + rank.

    Suit \ rank      7   8   9  10   J   Q   K   A
    0 spades         0   1   2   3   4   5   6   7
    1 hearts         8   9  10  11  12  13  14  15
    2 clubs         16  17  18  19  20  21  22  23
    3 diamonds      24  25  26  27  28  29  30  31

## Server console

In the terminal of `make server` (the host can also send `RAZ`, see below; there is no console
when the server runs as a service, see docs/server-service.md):

    RAZ                    wipes the game in progress and goes back to ATTENTE

Scores, reserve and reserved seats are cleared; connected humans and settings stay. Clients
receive `INFO PARTIE EFFACEE`, `SCORE 0 0`, `ETAT ATTENTE`.

## Details beyond the spec

Errors added, in the form `ERR TEXT`:

| Message | Case |
|---|---|
| `ERR INCONNU` | Unknown keyword. |
| `ERR PARAM` | PARAM malformed or out of range. |
| `ERR PAS LANCEE` | REJOUER or RAZ while in ATTENTE (game not started). |
| `ERR NOM RESERVE` | JOIN with BOT or BOT followed by digits (the bots' names on screen). The connection stays open: the client may send JOIN again with another name. |

Other cases:

- Any command before JOIN, or a second JOIN, gets `ERR NOM`.
- A misplaced bid on your turn (wrong suit, or ENCH during play) and COUP during bidding get
  `ERR COUP REFUSE`.
- After REDONNE (redeal), the server follows with `ETAT EN COURS` and `DONNEUR P`, as for any deal.
- `MANCHE` includes the reserve won, so that `SCORE` stays the sum of the `MANCHE` lines; an
  `INFO RESERVE N POUR EQUIPE E` reports it.
- Order at the end of a round: `PLI`, `CAPOT`, `LITIGE`, `INFO RESERVE`, `MANCHE`, `SCORE`, then
  `GAGNANT` and `ETAT`. Each message is present only when it applies.
- On reconnection during bidding, `ENCHERES T` follows `RETOURNE`, so that the client knows which
  round to show.
- After an accepted `COUP`, the player's `MAIN` follows their `JOUE` at once (after any `BELOTE` or
  `REBELOTE`), usually in the same TCP packet: a client that needs the former hand (for example
  the slot of the card played) must read it as soon as `JOUE` arrives.
- The empty hand at the end of a round is written `MAIN` with no parameter.
- After `PREND`, if the first player is a bot, it waits three times its usual delay (3 s by
  default): time to see the card taken.
- PETSCII: everything the server sends (upper case, digits, space, `-`) has the same code in ASCII
  and in upper case/graphics PETSCII. On input, the lower-case-mode PETSCII capitals ($C1-$DA)
  count as A-Z, unless the next byte is $80-$BF (a UTF-8 character sent by nc, which stays `?`).
  The terminator stays LF: a C64 client must not end its lines with PETSCII's lone CR.
- `INFO` texts are fixed (see SPEC.md 7.2): the client recognises them to translate them, and shows
  any other text as is.

## Rule interpretation decisions

- **Partner winning (5.3)**: anything goes, including a trump lower than the one the partner
  trumped with.
- **Tie with the taker's belote (5.4, 5.5)**: the belote is scored at once, only its card points go
  to the reserve. A round with no winning team (a new tie) adds to the reserve.
- **Idle players (4.3)**: only the human the table is waiting for can be idle (player on turn, host
  at FIN MANCHE or FIN PARTIE). Never in ATTENTE. Any line received counts as activity.
- **Reconnection (4.3)**: the server recognises a player by name, without authentication. A
  newcomer avoids reserved seats as long as another one is free.
- **Ghost connection (4.3)**: a JOIN with the name of a human still seated, from the same IP
  address, replaces that connection (C64 restarted without LEAVE). The others receive
  `INFO NOM RECONNECTE`. The trade-off: two players behind the same IP (NAT) choosing the same
  name are no longer told apart by a suffix; the second takes the first one's seat.
- **Empty table (4.2)**: with no human, the bots stop and the game is on hold; the next player in
  picks it up and becomes host.
- **Duplicate names (4.3)**: suffixes are tried from 2 to 9, then 1, following the example
  JEAN → JEA2. BOT and BOT followed by digits are reserved for the bots: a suffix never produces
  such a name.
