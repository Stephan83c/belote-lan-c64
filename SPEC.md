# BELOTE LAN C64 — networked belote on the C64 (C / cc65) + chat

*English · [Français](SPEC.fr.md)*

**Consolidated specification — version 4**

Commodore 64 Ultimate client  •  Python table server  •  4 seats

*Update of the consolidated version of 27 October 2026. v3: network hardware, protocol, screen, scoring. v4: official rules of classic belote, central mat removed.*

Version 4 — 7 November 2026; last updated: 14 November 2026 (client v1.5, see section 13)

Status: functional and protocol specification

C64 network hardware: C64 Ultimate (Ultimate Command Interface, TCP)

*This is a translation of SPEC.fr.md; the two are kept in step. Protocol keywords (JOIN, ENCH, PASSE, COUP...) are French and are not translated: they are what travels on the network. Screen texts are given in English; the client shows them in French, English, German or Spanish (see 2.1). Terms: the **taker** is the player who chooses trumps; **dedans** ("inside") means the taker failed the contract; a **litige** is a tie; **dix de der** is the 10-point bonus for the last trick; **capot** means one team takes all 8 tricks.*

## Contents

0. Changes in versions 3 and 4

1. Overview

2. Game flow

3. Keys

4. Players, seats and bots

5. Belote rules

6. Architecture and server

7. Protocol

8. Interface, colours and sounds

9. Chat

10. Code conventions

11. Decisions

12. To do / open questions

13. Decision history

*Marks: (v3) = changed in version 3; (v4) = changed in version 4.*

## 0. Changes in versions 3 and 4

### Version 4 *(v4)*

| Topic | v4 change | Origin |
|---|---|---|
| Rules | The usual rules of classic belote apply: direction of play, trump obligations, no under-trumping, capot, contract including belote. No declarations (tierce, carré...): only belote-rebelote is announced, automatically. | Decision |
| Direction of play | Play and deal go anticlockwise. P1 becomes EAST and P3 becomes WEST; teams do not change. | Rule |
| In trumps | Going higher is compulsory even when the partner is winning. | Rule |
| Declarations | No combination declarations (tierce, fifty, hundred, four of a kind). Only belote-rebelote exists, announced automatically by the server. | Decision |
| Capot | 252 points for the team that takes all 8 tricks. | Rule |
| Screen | Central mat removed: each card played is shown under its player's name. Log enlarged to 6 lines. | Decision |
| Protocol | CAPOT added. | Completed |
| Settings | Server address typed on the C64; bots at 1 s; name colour per seat in the chat; F1: target score and idle timeout. | Decision |
| End of game | The first team to reach the target (1000 by default) wins; checked at the end of a round. An unclaimed reserve is lost. | Decision |

### Version 3 *(v3)*

| Topic | v3 change | Origin |
|---|---|---|
| Network hardware | C64 Ultimate chosen. Direct TCP connection from the C64 to the server through the Ultimate Command Interface. RS232, SwiftLink and WiFi modem dropped. | Decision |
| Transport / framing | Text protocol kept: one line per message, ending in LF (10), upper case ASCII, 64 bytes at most. Port 6400. | Completed |
| Screen | The C64 has 25 lines: the grid goes from L0–L25 to L0–L24 (the former empty line L11 is removed). | Correction |
| Key bar | Shorter labels: each bar fits in 39 characters at most. | Correction |
| Rules key | F8 (code 140). The HELP key does not exist on the C64 (it belongs to the C128). | Correction |
| Relative view | Each player sees themselves as SOUTH. The client receives its seat (BIENVENUE) and rotates the display. US/THEM are relative to the player. | Correction |
| Deal | Classic deal in two parts: 5 cards each + turned-up card, then 3 cards (2 + the turned-up card for the taker). The former "5 then 3 per seat + turned-up card" went over 32 cards. | Correction |
| COUP | COUP C sends the card code (0–31) instead of the position in the hand; MAIN is sent again after each change. | Correction |
| Messages | BIENVENUE, SIEGE, DONNEUR, RETOURNE, ENCHERES, TOUR P (broadcast), PREND, PASSE P, REDONNE, BELOTE, REBELOTE, NBCARTES, TAPIS, MANCHE, LITIGE, GAGNANT, INFO, PARAM added. | Completed |
| Scoring | Dedans: 162 to the defence, belote stays with the team that announced it. 81–81 tie: the taker's points go to a reserve. Raw points, no rounding. | Decision |

## 1. Overview

The project is a four-seat networked belote game, with a Commodore 64 client written in C and compiled with cc65, and an authoritative server on Linux in Python asyncio. At most four humans can sit at the table; empty or abandoned seats are played by bots on the server. The chat is public and built into the game screen. The client polls the keyboard and the network in turn, including while the chat is being typed.

| Item | Consolidated specification |
|---|---|
| Game | French belote for 4 players, two opposing teams. |
| Client | Commodore 64, C compiled with cc65: display, non-blocking keyboard and network exchange in turn. |
| Server | Python 3 asyncio server on Linux; sole authority on state, cards, rules, score and bots. |
| Seats / teams | P0 + P2 against P1 + P3; partners face each other. |
| Game | Several rounds; target score 1000 by default, set by the host. |
| C64 network hardware *(v3)* | C64 Ultimate: TCP sockets opened by the C64 program through the Ultimate Command Interface (registers $DF1C–$DF1F). The "Command Interface" option must be enabled in the Ultimate's menu. |
| Server address *(v4)* | Typed on the C64 at startup (host name or IP, port 6464 by default), with a default set at build time. Development: server on a PC of the local network; production: Linux VPS. |

## 2. Game flow

### 2.1 Connection and waiting *(v4)*

At startup, the client shows the connection screen. The SERVER field is pre-filled with the default address (SERVEUR_IP and SERVEUR_PORT in config.mk); the player can change it (DEL to erase) then confirms with RETURN. Format: host or IP, optionally followed by :port (6464 if absent), 31 characters at most. The C64 Ultimate resolves the host name itself. On failure, the message "CANNOT CONNECT" is shown and the field is offered again.

```
L0  BELOTE LAN C64  V1.5
L1  ----------------------------------------
L3  SERVER  :51.38.50.79:6464
L5  NAME    :JEAN_
L7  RETURN = CONFIRM
L22 F1 = LANGUAGE
L24 FRANCAIS  ENGLISH  DEUTSCH  ESPANOL
```

**Language**: F1 switches to the next language (French, English, German, Spanish); each name is written in its own language, the current one in yellow, and the screen texts change at once. The choice holds for the whole session; the startup language is set at build time (`make LANGUE=0..3`). Everything is upper case without accents: extended colour mode only has 64 characters (UE for Ü, N for Ñ). Face cards follow the language: V D R (French), J Q K (English, Spanish), B D K (German). The protocol does not change: its keywords stay French and the client translates for display the ERR and INFO messages it recognises (an unknown text is shown as is). The texts live in tools/textes.py, which generates c64/textes.c and checks their widths.

Next, the client asks for a name of up to 5 characters (A–Z, 0–9), then joins the table. The server assigns a seat and confirms it with BIENVENUE. The first human connected becomes the host and first dealer. Bots fill the empty seats but do not play until the host starts the game with F2.

### 2.2 Cycle of a round *(v4)*

- First deal: 5 cards to each seat (20 cards), then the 21st card is turned face up to open the bidding.

- Two rounds of bidding following the classic belote rules described in section 5.

- Second deal: the taker receives the turned-up card and 2 cards, the three other seats receive 3 cards. Everyone then has 8 cards (32 in total).

- Eight tricks: each player plays one card; the winner of a trick leads the next one.

- Points are counted, the cumulative score is updated, then the end of the game is checked, only at the end of a round.

- If the game goes on, the host asks for the next round with F5. The deal moves on, including after a tie or a cancelled deal.

### 2.3 End of game

The target score is 1000 by default and can be changed by the host in the server settings. The score shown is cumulative from one round to the next. **The first team to reach or pass the target wins the game** *(v4)*. The check happens at the end of each round, after the full count (never in the middle of a round, as points are only known at the end: dedans, capot, reserve). If both teams reach the target in the same round, the higher one wins; on a perfect tie, an extra round is played and the deal moves on. Points still in reserve (tie) at the end of the game are lost.

```
L0  BELOTE LAN C64               GAME OVER
L1  ----------------------------------------
L2
L3
L4  US   : 1040
L5  THEM :  870
L6
L7  WE WIN!
L8
L9
L10
L11 F5 = NEW GAME   (HOST ONLY)
L12 F7 = QUIT
```

## 3. Keys

On the waiting table, F1 is reserved for the server settings. The game rules are shown with F8. F2 starts the game, F3 opens the chat, F5 moves to the next round at the end of a round (cumulative score kept) and F7 quits. On the end-of-game screen, F5 starts a new game and resets the scores. During bidding, 1 to 4 choose an option; during play, 1 to 8 play the numbered cards of the hand; RETURN confirms the name on the connection screen.

| Key | C64 code | Action / availability |
|---|---|---|
| F1 | 133 | Connection screen: next language. Waiting table: table settings, host only: target score and idle timeout (section 3.1). |
| F2 | 137 | Start the waiting game; host only. |
| F3 | 134 | Open the public chat, type then send a message. |
| F4 | 138 | Host, game started: wipe the game in progress, after confirmation (Y; O, J or S in the other languages). |
| F5 | 135 | End of round: next round, cumulative score kept. End-of-game screen: new game, scores reset. Host only. |
| F6 | 139 | No action. |
| F7 | 136 | Leave the table. |
| F8 *(v3)* | 140 | Show / hide the rules (local screen, network reception goes on). HELP does not exist on the C64. |
| 1 to 4 | Ordinary keys | Bidding choice, only on your bidding turn. |
| 1 to 8 | Ordinary keys | Play the card with this number, only on your turn. |
| RETURN | 13 | Confirm the name / join; send the chat message. |

### 3.1 F1 settings *(v4)*

F1 opens a small settings screen, for the host while waiting. Two settings, each changed with the + and − keys, confirmed with RETURN, cancelled with F1:

| Setting | Default | Range |
|---|---|---|
| Target score | 1000 | 500 to 5000, in steps of 100 |
| Idle time before a bot takes over | 3 min | 1 to 10 min, in steps of 1 |

Network reception goes on during this screen; new values are broadcast to all with PARAM.

### 3.2 Key bar (L24) *(v3)*

The bar shown depends on the state and the role. Each bar is 39 characters at most, so as never to write the last cell of the screen (risk of scrolling). The texts below are the English ones; every language has its own, checked by tools/textes.py.

| Situation | Bar shown (≤ 39 chars) |
|---|---|
| Host, waiting | F1 SETUP F2 GO F3 CHAT F7 QUIT F8 HELP |
| Other player, waiting | F3 CHAT F7 QUIT F8 HELP |
| Bidding, your turn | 1-4 BID F3 CHAT F7 QUIT F8 HELP |
| Play, your turn | 1-8 CARD F3 CHAT F7 QUIT F8 HELP |
| Not your turn | F3 CHAT F7 QUIT F8 HELP |
| Host, game started | F4 WIPE is added; F3 CHAT becomes F3 MSG when the line would go over 39 characters (e.g. 1-8 CARD F3 MSG F4 WIPE F7 QUIT F8 HELP) |
| Host, end of round | F3 MSG F4 WIPE F5 NEXT F7 QUIT F8 HELP |
| Other player, end of round | F3 CHAT F7 QUIT F8 HELP |
| Host, end of game | F5 NEW GAME F7 QUIT |
| Other player, end of game | F7 QUIT |
| Host, after F4 | WIPE THE GAME? Y YES, OTHER KEY NO |
| Typing the chat | RETURN SEND  DEL DELETE  F3 CANCEL |

## 4. Players, seats and bots

### 4.1 Seats and teams

| Seat | Absolute position | Team | Order of play |
|---|---|---|---|
| P0 | SOUTH | Team 0 (P0 + P2) | 1 |
| P1 | EAST *(v4)* | Team 1 (P1 + P3) | 2 |
| P2 | NORTH | Team 0 (P0 + P2) | 3 |
| P3 | WEST *(v4)* | Team 1 (P1 + P3) | 4 |

Seats go round P0 → P1 → P2 → P3 → P0, that is SOUTH → EAST → NORTH → WEST: play goes anticlockwise, as in classic belote; the next player is always on the right. P0 and P2 are partners, as are P1 and P3. The server seats the first human at P0; the other free seats are bots.

**Relative display** *(v3)* — The positions above are the server's. Each client shows itself as SOUTH: the screen position of a seat P seen by player M is r = (P − M + 4) mod 4, with 0 = SOUTH, 1 = EAST, 2 = NORTH, 3 = WEST. US is the player's team, THEM the other.

### 4.2 Host

- The first human connected is the host and first dealer. They have the F1 settings and the F2 start.

- If the host leaves or is replaced for being idle, their seat becomes a bot and the first remaining human in the order P0→P3 becomes host. If no human is left, there is no host and the table waits.

- After the start, the former host leaving does not stop the game. The new host can ask for F5 at the end of a round; they do not restart the game in progress.

- The limit is four human connections. A fifth connection (and any after it) is refused with ERR TABLE PLEINE, then closed by the server; the C64 shows "TABLE FULL (4 PLAYERS): TRY LATER" on the connection screen. Bots do not count as human connections.

### 4.3 Names, replacement and presence

- Displayed name: 5 characters at most, letters A–Z and digits; unique among the players. On a duplicate, the last character is replaced by a numeric suffix (e.g. JEAN → JEA2), from 1 to 9; otherwise the connection is refused. The final name is sent back in BIENVENUE.

- Reserved names: BOT and BOT followed by digits (BOT1 to BOT4 name the bots on screen). The C64 refuses them before connecting; the server answers ERR NOM RESERVE without closing the connection, and a duplicate suffix never produces such a name. The C64 shows "NAME RESERVED FOR BOTS: CHOOSE ANOTHER" and puts the cursor back on the NAME field.

- Idle player (3 minutes by default, set by the host with F1): a bot takes over the seat. There are no spectators; an idle user who was released must reconnect.

- On reconnection, the user gets back their seat and the hand still held by the bot if that seat is still available. If another human has it, a free bot seat is given; if there is none, the reconnection is refused.

- Ghost connection: a restarted C64 (reset, new program) does not send LEAVE and its old TCP connection may stay open. A JOIN with the name of a human still seated, from the same IP address, takes back their seat: the old connection is closed, the client receives BIENVENUE and the full state, the other players an INFO NOM RECONNECTE. From another address, the duplicate rule applies.

- Explicit disconnection or connection loss during your turn: the bot plays at once, without waiting for the 3 minutes. It keeps the current hand; a later return picks up the updated state (see 7.4).

### 4.4 Bot strategy

Bots are computed by the server and only act after the start. Simple strategy: bid if the hand holds at least two potential trumps, otherwise pass; always play a legal move (section 5.3); rather play a low card if the partner is winning, and a card that can win if the opponent is winning. When leading, the bot plays the highest card left in a non-trump suit (the ace, or the 10 once the ace has fallen): it remembers the cards already played in the deal. Each bot action (bid or card) is played after a fixed delay of **1 second** *(v4)*, so that players can follow. The detailed strategy remains to be refined with use.

## 5. Belote rules

### 5.1 Deck, codes and order

32-card deck: 7, 8, 9, 10, Jack, Queen, King, Ace in the four suits. Card C = SUIT × 8 + RANK; suit 0=♠, 1=♥, 2=♣, 3=♦; rank 0=7, 1=8, 2=9, 3=10, 4=J, 5=Q, 6=K, 7=A. Cards are coded 0 to 31.

| Context | Order of strength (low → high) | Points |
|---|---|---|
| Not trumps | 7, 8, 9, J, Q, K, 10, A | 7/8/9 = 0; J=2; Q=3; K=4; 10=10; A=11 |
| Trumps | 7, 8, Q, K, 10, A, 9, J | 7/8=0; Q=3; K=4; 10=10; A=11; 9=14; J=20 |

Suits are sorted in the hand as spades, hearts, clubs, diamonds (0, 1, 2, 3). Trump values replace the non-trump values of the Jack and the 9.

### 5.2 Deal and bidding *(v4)*

- The first dealer is the first human connected. At each following round, the deal moves one seat on (to the right); this also applies after a tie and after a cancelled deal.

- The server shuffles the deck at each deal (the cut by the player on the left has no effect online).

- First deal, starting with the player to the dealer's right: 3 cards then 2 cards to each seat (5 cards). The 21st card is turned up and proposes the trump suit.

- First round: each player, starting to the dealer's right, can take the suit of the turned-up card or pass. If nobody takes, second round: each player can choose one of the three other suits or pass.

- As soon as a player takes, bidding stops: the trump suit and the taking team are set. The taker receives the turned-up card and 2 cards; the others receive 3 cards.

- If everyone passes in both rounds, the deal is cancelled (REDONNE) and dealt again by the next dealer.

### 5.3 Play and legal moves *(v4)*

The player to the dealer's right leads the first trick. The winner of a trick leads the next one; there are eight tricks. A trick is won by the highest trump or, without trumps, by the highest card of the suit led.

| Situation | Obligation |
|---|---|
| Suit led (not trumps), the player has it | Follow suit (any card of that suit). |
| Trumps led | Play a trump and go higher (play a trump higher than the highest already played) if possible, even when the partner is winning. Without a higher trump: a lower trump. Without trumps: free discard. |
| Suit led missing, partner winning | Free: discard or trump. |
| Suit led missing, opponent winning | Trumping is compulsory if possible. If an opponent has already trumped, over-trump if possible. |
| Cannot over-trump | Under-trumping (a lower trump) is forbidden: discard another suit. If the player has only trumps left, they play a lower trump. |
| No card of the suit and no trump | Free discard. |

The server checks the turn, the card in hand and these obligations; on refusal, it sends ERR COUP REFUSE and waits for a new action from the same player. The client may grey out forbidden cards, but the server is authoritative.

### 5.4 Belote-rebelote *(v4)*

The player who holds the King and Queen of trumps scores 20 points. The server announces "belote" automatically when the first of these cards is played, then "rebelote" when the second one is; the player has nothing to do. These 20 points always stay with the team that announces them, even if it is dedans.

**No other declarations**: tierces, fifties, hundreds and four of a kind are not played.

### 5.5 Points and contracts *(v4)*

Total card points: 152, plus 10 points for the last trick (dix de der): 162 points per round, plus 20 points for a belote-rebelote, if any.

| Case | Rule |
|---|---|
| Contract made | The taker scores strictly more points than the defence, cards + dix de der + belote included (82 out of 162 without belote). Each team scores its points. |
| Dedans | The taker scores less than the defence: the defence scores 162 (+ its own belote, if any). The taker scores 0, plus their belote-rebelote if they announced it. |
| Litige (tie) | The defence scores its points. The taker's points go to a reserve and go to the team that wins the next round (the taker if they make it, or the defence if the taker is dedans). A cancelled deal does not settle the reserve. |
| Capot | The team that takes all 8 tricks scores 252 points (instead of 162) + its belote; the other scores only its belote, if any. If the defence makes capot, the taker is dedans. |
| Rounding | None: points are added raw to the cumulative score. |

The round score (MANCHE) and the cumulative score (SCORE) are sent after the eighth trick.

## 6. Architecture and server

### 6.1 Technical stack

- **Server** — Python 3 asyncio on Linux: asyncio.start_server on port 6464, one coroutine per client, central game state, line-by-line text protocol (StreamReader.readline()).

- **Client** — C for the C64 compiled with cc65 (cl65 -t c64); 40×25 screen in extended colour mode (ECM), written directly to memory ($C000, characters at $C800); non-blocking main loop alternating keyboard (KERNAL GETIN, cbm_k_getin) and network, so as to keep receiving while typing. Two sprites for the sliding card (8.1); multicolour bitmap title screen; music and sound effects on the SID (8.3).

- **C64 network** *(v3)* — Ultimate Command Interface of the C64 Ultimate, network target: a TCP connection is opened, then non-blocking reads happen at each pass of the loop. The client gathers bytes up to LF, then handles the line.

- **Encoding** *(v3)* — The network carries ASCII. In upper case/graphics mode, letters A–Z have the same codes in ASCII and PETSCII. cc65 would convert literals for the c64 target: c64/ascii.h forces the identity for $40–$5F, so literals, keyboard and network share the same code, with no conversion when sending or receiving.

### 6.2 Division of responsibilities

| Linux server (Python 3 asyncio) | C64 client (C / cc65) |
|---|---|
| asyncio.start_server; one coroutine per client; central game state and line-by-line text protocol. | Shows the table and its own hand only, in relative view (itself as SOUTH). |
| Deals, runs the bidding, validates moves and counts points. | Receives and interprets messages; sends key choices and chat. |
| Plays the bots and acts at once on a disconnection during the turn. | Never receives the hidden cards of the other seats. |
| Handles connections, the host, states, timers and selective broadcast. | Non-blocking loop: polls keyboard and network in turn; reception goes on while the chat is typed. |

The server is the sole authority; opposing hands are never sent to clients. A client receives its private hand, the number of cards left to the others, the cards played and public table events.

### 6.3 Table states

| State | Meaning |
|---|---|
| ATTENTE | Table open; humans join/leave; bots idle; only the host can start. |
| LANCEE | Start accepted; the first round begins. |
| EN COURS | Bidding or play of a round in progress. |
| FIN MANCHE | Result published; waiting for the host's F5. |
| FIN PARTIE *(v3)* | The target is reached at the end of a round; winner shown. F5 (host) starts a new game, scores reset. |

### 6.4 Historical conceptual data

```
PT(P) = 0 bot / 1 human, P=0..3
PN$(P) = displayed name
MAIN(P,K) = card, K=1..8 ; -1 if played
NMAIN(P) = number of cards left
DONNEUR = dealer's seat ; CHEF = host's seat, -1 if none
ATOUT, PRENEUR, ENTAMEUR, PLI(P), RETOURNEE
BELOTE(P)
POINTS(E), SCORE(E), RESERVE ; E=0 : P0+P2, E=1 : P1+P3
```

## 7. Protocol *(v3)*

### 7.1 Transport and framing

| Point | Rule |
|---|---|
| Transport | TCP, port 6464. One connection per client. |
| Frame | One line per message, ending in LF (code 10). A CR before the LF is ignored. |
| Fields | Upper case keyword, then parameters separated by a space. For TCHAT, INFO and ERR, the text is the rest of the line. |
| Encoding | ASCII 32–95 (upper case, digits, punctuation). The server converts to upper case and replaces any other character with "?". |
| Length | 64 bytes at most, LF included. The server ignores a longer line (ERR TROP LONG). |
| Values | Seats 0–3 (absolute), cards 0–31, suits 0–3, teams 0–1, numbers in decimal. |
| Errors | A refused action gets ERR TEXT; the server state does not change. |

### 7.2 Server → client

| Message | Audience | Meaning / data |
|---|---|---|
| BIENVENUE NAME P *(v3)* | Client | Connection accepted: final name (possibly changed) and seat P. |
| SIEGE P T NAME *(v3)* | All | Occupant of seat P: T = H (human) or B (bot). Replaces TABLE P0 P1 P2 P3. Sent for the 4 seats on connection and on each change. |
| CHEF P | All | Host's seat, 0..3; -1 if none. |
| ETAT X | All | ATTENTE, LANCEE, EN COURS, FIN MANCHE or FIN PARTIE. |
| PARAM CIBLE N *(v3)* | All | Current target score. |
| PARAM INACTIF M *(v4)* | All | Current idle timeout, in minutes. |
| DONNEUR P *(v3)* | All | Dealer of the round. |
| MAIN C1 .. Cn | Client | Its full hand (n ≤ 8), sorted. Sent again after each deal and each accepted move. |
| NBCARTES N0 N1 N2 N3 *(v3)* | All | Number of cards of each seat (after a deal and on reconnection). |
| RETOURNE C *(v3)* | All | Turned-up card for the bidding. |
| ENCHERES T *(v3)* | All | Start of bidding round T (1 or 2). |
| TOUR P *(v3)* | All | Seat P must act (bid or card depending on the phase). Broadcast to all for the * marker. |
| PREND P C *(v3)* | All | Seat P takes; trumps are suit C. |
| PASSE P *(v3)* | All | Seat P passes. |
| REDONNE *(v3)* | All | Everyone passed: deal cancelled. |
| JOUE P C | All | Seat P played card C. |
| BELOTE P / REBELOTE P *(v3)* | All | Automatic announcement when the King or Queen of trumps is played. |
| PLI P | All | Seat P wins the trick. |
| PLICOURS C0 C1 C2 C3 *(v4)* | Client | Cards of the current trick per seat (-1 = not played yet); on reconnection. Replaces TAPIS. |
| CAPOT E *(v4)* | All | Team E took all 8 tricks. |
| MANCHE E0 E1 *(v3)* | All | Round points of team 0 (P0+P2) and team 1 (P1+P3). |
| LITIGE N *(v3)* | All | N points put in reserve (tie). |
| SCORE E0 E1 | All | Cumulative score per absolute team; the client shows US/THEM according to its seat. |
| GAGNANT E *(v3)* | All | Winning team of the game. |
| TCHAT NAME TXT | All | Public message, name and content. |
| INFO TXT *(v3)* | Client or all | Information shown in the log (name changed, player replaced by a bot, etc.). Fixed texts, which the client recognises to translate them: NOM CHANGE EN NAME, NAME RECONNECTE, NAME REMPLACE PAR UN BOT, NAME INACTIF REMPLACE PAR UN BOT, INACTIF : PLACE RENDUE AU BOT, PARTIE EFFACEE, RESERVE N POUR EQUIPE E. |
| ERR TEXT | Client | ERR CHEF SEUL, ERR TABLE PLEINE, ERR PAS TON TOUR, ERR COUP REFUSE, ERR DEJA LANCEE, ERR PAS LANCEE, ERR NOM, ERR NOM RESERVE, ERR PARAM, ERR INCONNU, ERR TROP LONG (details in protocol.md). The client shows them translated in the log ("REFUSED: …"). |

### 7.3 Client → server

| Message | Trigger | Meaning / server check |
|---|---|---|
| JOIN NAME | RETURN after typing the name | Join; name of 5 characters at most, uniqueness enforced by the server. |
| LANCER | F2 | Host only, in ATTENTE; otherwise ERR CHEF SEUL or ERR DEJA LANCEE. |
| PARAM CIBLE N *(v3)* | F1 then setting | Host only, in ATTENTE; N from 500 to 5000. |
| PARAM INACTIF M *(v4)* | F1 then setting | Host only, in ATTENTE; M from 1 to 10 minutes. |
| ENCH C | Keys 1–4 during bidding | Take with suit C. In round 1, C must be the turned-up suit; in round 2, another suit. |
| PASSE | PASS bidding key | Pass. |
| COUP C *(v3)* | Key 1–8 | Play the card with code C (the client turns the displayed number into a code). Valid only on your turn. On the last trick, the client sends it by itself (8.1). |
| TCHAT TXT | F3, typing, RETURN | Public message, cut to 30 characters by the client and the server. |
| REJOUER | F5 | Host only: next round in FIN MANCHE, new game in FIN PARTIE. |
| RAZ | F4 then Y (O, J, S) | Host only, game started: wipes the game (scores, reserve, reserved seats) and goes back to ATTENTE; clients receive INFO PARTIE EFFACEE, SCORE 0 0, ETAT ATTENTE. Otherwise ERR CHEF SEUL or ERR PAS LANCEE. |
| LEAVE | F7 | Leave; the seat goes to a bot. |

### 7.4 Sequences

**Connection and start**

```
C64 -> srv : JOIN JEAN
srv -> C64 : BIENVENUE JEAN 0
srv -> all : SIEGE 0 H JEAN / SIEGE 1 B BOT / SIEGE 2 B BOT / SIEGE 3 B BOT
srv -> all : CHEF 0 / ETAT ATTENTE / PARAM CIBLE 1000 / PARAM INACTIF 3
host-> srv : LANCER
srv -> all : ETAT LANCEE / SCORE 0 0
```

**A round**

```
srv -> all : ETAT EN COURS / DONNEUR 0
srv -> each: MAIN c1..c5          (private)
srv -> all : NBCARTES 5 5 5 5 / RETOURNE 12 / ENCHERES 1
srv -> all : TOUR 1 / PASSE 1 / TOUR 2 / PREND 2 1
srv -> each: MAIN c1..c8          (private)
srv -> all : NBCARTES 8 8 8 8 / TOUR 1
P1  -> srv : COUP 14
srv -> all : JOUE 1 14 / TOUR 2 ...
            (srv -> P1 : MAIN ...)
srv -> all : PLI 3 / TOUR 3 ...   (x 8 tricks)
srv -> all : MANCHE 72 110 / SCORE 72 110 / ETAT FIN MANCHE
host-> srv : REJOUER
```

**Reconnection** — after BIENVENUE, the server sends the full state: SIEGE ×4, CHEF, ETAT, PARAM, SCORE, DONNEUR, then depending on the phase RETOURNE or PREND, MAIN, NBCARTES, PLICOURS and TOUR.

## 8. Interface, colours and sounds

### 8.1 Reference screen grid *(v4)*

Grid of 40 columns (0–39) and 25 lines (L0–L24). The central mat is removed: the card played by each player is shown under their name. A bot is named after its real seat, BOT1 to BOT4 (P0 to P3), on the table as in the log: the same name on every screen, whatever each player's seat. Names, points and cards are examples (the player is P0), with the English texts.

```
    0         1         2         3
    0123456789012345678901234567890123456789
L0  BELOTE   TRUMP:♥   US:0000    THEM:0000
L1  ----------------------------------------
L2                    BOT3
L3                    [Q ]
L4                    [♥ ]
L5    BOT4                      BOT2
L6      [K ]                    [10]
L7      [♣ ]                    [♦ ]
L8  
L9  
L10                  *JEAN
L11 ----------------------------------------
L12 BOT3 : PASSES
L13 BOT2 : TAKES Q♥
L14 BOT2 : BELOTE
L15 LEA  : WELL PLAYED!
L16 BOT2 : REBELOTE
L17 BOT2 : WINS THE TRICK
L18 YOU  : _
L19 YOUR TURN: 1-8
L20 ----------------------------------------
L21 [J ] [9 ] [Q ] [10] [7 ] [K ]
L22 [♠ ] [♠ ] [♠ ] [♦ ] [♦ ] [♥ ]
L23  1    2    3    4    5    6
L24 1-8 CARD F3 CHAT F7 QUIT F8 HELP
```

**Play area (L2–L10)**: each player's name at their relative position (NORTH = partner, EAST = on the right, WEST = on the left, SOUTH = yourself), preceded by * for the player whose turn it is. Under each name, the card they played in the current trick, or nothing. The cards of a finished trick stay shown until the first card of the next trick. Opposing hands are not drawn. Humans are shown by name (followed by "(HOST)" while waiting), bots as BOT1 to BOT4 after their real seat (P0 to P3), the same for all players. In the centre (L5–L7): during bidding, the turned-up card under "TURNED UP"; after the take, the card taken under "TAKEN", until the first card is played.

**Log (L12–L17)**: six lines for bids, belote-rebelote, tricks, chat and INFO; a player event fits in 33 characters after "NAME : ", a server message takes the whole line (40); new events replace the oldest ones. **L18** is used to type the chat.

**L19** is the status line. While waiting: "HOST: <NAME>   TARGET: 1000 POINTS". During play, on your turn: "YOUR TURN: 1-8". At the end of a round: "ROUND OVER: F5 FOR THE NEXT ONE" (host) or "…: WAITING FOR THE HOST". During bidding, first round: "[1 TAKE <turned-up suit>] [2 PASS]". Second round: the 3 other suits then PASS (e.g. "[1 ♠] [2 ♣] [3 ♦] [4 PASS]"). On another player's turn: "BIDDING: <NAME> TO PLAY...". On the right of the line, the current bidding round ("ROUND 1" or "ROUND 2"), as the log does not always show the passes of the first round. The player concerned uses keys 1 to 4.

**Hand (L21–L23)**: up to 8 cards numbered 1 to 8, sorted spades-hearts-clubs-diamonds; the numbers are yellow when it is your turn to play a card, dark grey otherwise. L0 shows TRUMP:? until the end of the bidding; US and THEM show the cumulative score on 4 digits at most.

**Sliding card**: each card played (JOUE) slides to its place on the table in 14 frames (about a quarter of a second), drawn with two sprites: the white body with rounded corners (sprite 1, X-expanded) and, in front, the rank and suit in the card's colour (sprite 0); data at $C400. Your own card starts from its slot in the hand (remembered when JOUE arrives, before the MAIN that follows); the partner's from the top of the screen, the opponents' from the right (EAST) or left (WEST) edge. During that quarter of a second, the client does not read the network: messages wait in the Ultimate. The table and the hand are redrawn in place, without being cleared first: nothing flickers.

**Last trick**: the last card is played automatically half a second after the player's TOUR (a single COUP per card).

### 8.2 C64 colours

| Area / item | Value | Rendering |
|---|---|---|
| Board and border | C64 green = 5 | Green background; empty cells carry a felt pattern (light green dots = 13, the redrawn # character). |
| Cards | White background (ECM, $D022 = 1), rounded corners | Rank and suit in the card's colour. The corners are four redrawn characters (" $ % &): a 2-pixel arc in the board's green. |
| Hearts and diamonds | C64 red = 2 | Red rank and suit on the white card. |
| Spades and clubs | C64 black = 0 | Black rank and suit on the white card. |
| Colour RAM | Address $D800 | Colour attributes of the screen cells. |

Colour codes per suit: FC(0)=0, FC(1)=2, FC(2)=0, FC(3)=2.

### 8.3 Sounds

The client plays the music and sound effects on the SID, only from messages already received: the server and the protocol know nothing about them.

| Moment | Trigger | Sound |
|---|---|---|
| Title screen | image shown, until a key | Original 3-voice musette waltz, looping. |
| Card played | JOUE (any player) | Short snap (noise). |
| Trick taken | PLI | Cards sliding, after the snap of the last card. |
| Chat | TCHAT (any player message) | Two bright notes. |
| Game won | GAGNANT, the player's team | Rising fanfare. |
| Game lost | GAGNANT, the other team | Descent ending in minor. |

The player (c64/son.s) runs in the KERNAL interrupt, 60 times a second, so also during network commands. Tunes use voices 1 to 3 and sound effects voice 3: an effect requested while another plays waits for it to end. Notes, durations and envelopes are written in tools/musique.py, which generates c64/son_donnees.s.

## 9. Chat

- Public only: no private chat. Opened with F3, sent with RETURN.

- Displayed name limited to 5 characters. Text limited to 30 characters: the client limits typing and the server cuts for safety.

- The message is broadcast to all with TCHAT NAME TXT and shown in the log L12–L17; typed in L18.

- Typing the chat does not stop network reception: the main loop checks the keyboard without blocking (KERNAL GETIN) and handles network data in turn.

- Name colour, on the table and in the log: one fixed colour per seat, the same on every screen, in two shades per team: P0 cyan (3) and P2 blue (6) for team P0+P2; P1 orange (8) and P3 red (2) for team P1+P3. Light red (10), too close to green in brightness, is left out. The message text stays white; INFO and server messages in light grey (15).

- Bots are named BOT1 to BOT4 after their real seat (P0 to P3): in the chat, "BOT2" means the same bot for everyone.

## 10. Code conventions

The C/cc65 client (c64/) and the Python server (server/) are written and in service. The BASIC extracts below come from the original design: their conventions (card codes, seats, colours) are still those of the code.

### 10.1 Card and seat coding

```
REM Card C = SUIT*8 + RANK, C=0..31
REM SUIT : 0=Spades, 1=Hearts, 2=Clubs, 3=Diamonds
REM RANK : 0=7, 1=8, 2=9, 3=10, 4=J, 5=Q, 6=K, 7=A
REM Seats : P0=SOUTH, P1=EAST, P2=NORTH, P3=WEST (absolute)
REM Direction : P0 -> P1 -> P2 -> P3 (anticlockwise)
REM Screen : relative position r = (P - ME + 4) MOD 4
REM Teams : E0 = P0+P2 ; E1 = P1+P3
```

### 10.2 Graphic conventions

```
REM Board/border colour : 5 (green)
REM Cards : white background, rank and suit red=2 or black=0
REM Extended colour mode (ECM) ; colour RAM : $D800
REM FC(0)=0 spades ; FC(1)=2 hearts ; FC(2)=0 clubs ; FC(3)=2 diamonds
```

### 10.3 Server logic

```
DEAL       : shuffle ; 3 then 2 cards per seat ; TURNED-UP = 21st
BIDDING    : round 1 on the turned-up suit ; round 2 another suit
COMPLETE   : taker = turned-up + 2 ; others = 3
LEADER     = (DEALER + 1) MOD 4
BELOTE     : auto when the K or Q of trumps is played if the player has both
TRICK      : 4 valid moves ; winner = LEADER of the next trick
END ROUND  : count (contract/dedans/tie/capot) ; SCORE ; DEALER+1
BOT        : always a legal move (section 5.3)
```

### 10.4 Project layout *(v3)*

```
c64-online/
  c64/         C client (cc65), built by the Makefile at the root (cl65 -t c64)
  c64/vice/    simulated network for VICE (make vice-demo SCENARIO=1..6)
  server/      Python asyncio server + pytest tests
  tools/       generators: texts (4 languages), music, title screen; belote.service
  docs/        screenshots (FR and EN), systemd service guide
  config.mk    addresses: default server, C64 Ultimate
  protocol.md  extract of section 7 (protocol.fr.md in French)
  CLAUDE.md    build/deploy instructions (French)
  SPEC.md, README.md, protocol.md: English translations (*.fr.md: French)
```

Development deployment: make deploy sends build/belote_lan.prg to the C64 Ultimate through its REST API (POST /v1/runners:run_prg). The server can be tested without a C64 with nc or telnet on port 6464.

## 11. Decisions

These decisions override contradictory or older wording.

| Topic | Consolidated decision | Status |
|---|---|---|
| Keys | F1 settings (host); F2 start (host); F3 chat; F4 wipe the game (host); F5 next round / new game (host); F7 quit; F8 rules; 1–4 bidding; 1–8 cards; RETURN confirm. | Adopted; F8 *(v3)* |
| Seats / partners | P0=SOUTH, P1=EAST, P2=NORTH, P3=WEST; order P0→P1→P2→P3, anticlockwise; teams P0+P2 against P1+P3; relative display, each player as SOUTH. | Adopted; direction *(v4)* |
| Deal and bidding | Classic belote: 3 + 2 cards + turned-up card, two rounds of bidding, then 3 cards (taker: turned-up card + 2). Everyone passes: redeal, next dealer. | Adopted; deal *(v3)* |
| Play *(v4)* | Follow suit; in trumps always go higher; trump if the opponent is winning, over-trump if possible; under-trumping forbidden unless only trumps are left; free if the partner is winning. | Adopted *(v4)* |
| Declarations *(v4)* | Only belote-rebelote (+20), announced automatically by the server. No tierce, fifty, hundred or four of a kind. | Adopted *(v4)* |
| Points | 162 per round (152 + dix de der), belote-rebelote +20; target 1000 by default, configurable; the first team to reach the target wins (checked at the end of a round); both in the same round: the higher; perfect tie = new round; unclaimed reserve lost. | Adopted; end *(v4)* |
| Contract | Taker: strictly more than the defence, belote included. Dedans: 162 to the defence, belote stays with the team that announced it. Tie: the taker's points in reserve. Capot: 252. Raw points. | Adopted *(v3)*; capot *(v4)* |
| Presence | No spectators. Idle timeout 3 min by default (F1: 1 to 10 min): bot. Return to your seat possible if free. Disconnection on your turn: the bot plays at once. | Adopted |
| Chat | Public; name 5 characters; message 30 characters; non-blocking loop; name colour per seat, two shades per team (cyan and blue, orange and red); bots BOT1 to BOT4. | Adopted; bot colours and names (client v1.3) |
| Graphics | Board/border green 5 with felt pattern; white cards with rounded corners, rank and suit red 2 / black 0; colour RAM $D800; sliding played card (two sprites). | Adopted; white cards (client v1.3); corners and sliding (client v1.5) |
| Sounds | Music on the title screen; sound effects for card played, trick, chat; win and loss jingles. Client side only (section 8.3). | Adopted |
| Languages | French, English, German, Spanish, chosen with F1 on the connection screen; upper case without accents; protocol unchanged, ERR and INFO translated by the client (section 2.1). | Adopted (client v1.5) |
| Screen | 40 × 25 grid (L0–L24), no central mat: card played under each player's name; opposing hands not shown; 6-line log; key bar ≤ 39 characters on L24; * before the player on turn. | Adopted; no mat *(v4)* |
| Server | Python asyncio on Linux (VPS in production), port 6464; address typed on the C64; deals, validates, counts, plays the bots (1 s delay); 4 humans max. | Adopted; address *(v4)* |
| F1 settings *(v4)* | Target score (500–5000, default 1000) and idle timeout (1–10 min, default 3). | Adopted *(v4)* |
| Network hardware *(v3)* | C64 Ultimate, Ultimate Command Interface, direct TCP. | Adopted *(v3)* |
| Protocol *(v3)* | ASCII text, one line per message ending in LF, 64 bytes max; messages of section 7. | Adopted *(v3)* |

## 12. To do / open questions

- **Bots** — Strategy to refine: bidding (count the jack, 9 and ace of trumps rather than the number of trumps), play with the partner, count the trumps played. The 1 s delay and the names BOT1 to BOT4 are set; see step 18 for what was measured.

- **Several tables** — The server has a single 4-seat table: a fifth player gets TABLE PLEINE, and strangers can take the seats of a group of friends. To plan before a public announcement (protocol, server and C64 screen).

- **Accessibility** — A C64 Ultimate (or Ultimate 64 / Ultimate-II+) is needed: VICE does not emulate the Command Interface. A version using VICE's emulated network (RR-Net) would allow trying it without the hardware.

## 13. Decision history

| Step | Decision / change | Outcome |
|---|---|---|
| 1 | Initial concept: networked belote, server in charge of the game; messages JOIN, COUP, ENCH, PASSE, TCHAT, REJOUER, LEAVE. | Kept and detailed. |
| 2 | First human: host role, F2 start and host handover. | Kept; F1 reassigned to settings. |
| 3 | Simplified bidding and provisional scoring. | Replaced by classic bidding and 162 points. |
| 4 | Classic rules: turned-up card then another suit; belote/rebelote; trump obligations. | Integrated. |
| 5 | 40-column text screen, hidden opponents, mat, * for the turn. | Kept; brought down to 25 lines in v3. |
| 6 | 4 humans at most, bots, names, reconnection, idle players. | Consolidated. |
| 7 | Target score 1000, checked at the end of a round, deal moving on after a tie. | Kept. |
| 8 | Decisions: keys, seats/teams, C64 colours, chat, Linux VPS. | Applied. |
| 9 | Bidding area and end-of-game screen. | Kept. |
| 10 | Stack: Python asyncio + cc65 client. | Adopted. |
| 11 *(v3)* | C64 Ultimate chosen; protocol completed (transport, framing, new messages, COUP by code); 25-line screen; F8; relative view; deal corrected; dedans / tie / raw points rules. | Version 3 (7 November 2026). |
| 12 *(v4)* | Official rules of classic belote: direction of play, obligations, capot, belote included in the contract; only belote is announced (automatically); the first team to 1000 wins; address typed on the C64, bots at 1 s, chat colours, F1 settings. Central mat removed. | Version 4 (7 November 2026). |
| 13 | Sounds on the SID: title screen music, sound effects (card, trick, chat), end-of-game jingles. No protocol change. | Client v1.2 (13 November 2026). |
| 14 | Bots named BOT1 to BOT4 after their real seat (and no longer after their relative position, which differed from one screen to another); name colours per team: cyan and blue, orange and red. | Client v1.3. |
| 15 | White cards, rank and suit in the card's colour (red or black), instead of red or black cards with white text. | Client v1.3. |
| 16 | Names BOT and BOT + digits refused to players (ERR NOM RESERVE); refusal messages in plain words on the connection screen (table full, name reserved or refused). | Server and client v1.4. |
| 17 | Client in four languages (French, English, German, Spanish), chosen with F1 on the connection screen; face cards of the language; ERR and INFO translated by the client; on the title screen, a drawn SPACE key replaces "ESPACE POUR JOUER". No protocol or server change (see 2.1). English translation of the documentation (SPEC.md, README.md, protocol.md, docs/server-service.md), French kept as *.fr.md. GitHub release v1.5 (notes in English and French), repository description in English. | Client v1.5 (14 November 2026). Public server updated. |
| 18 | Bots, after a full game on the public server (Stéphan against Claude, 1115 to 687) and an analysis of its log: the 10s the bots gave away were forced moves, not mistakes. Memory of the cards played; lead with the highest card left in a suit (master 10 once the ace has fallen), +1 % points over 40,000 deals simulated against the former strategy. Trumping or winning with a master card rather than the lowest winning card was tried and dropped (−6.8 %). | Server v1.5, fix after the release (14 November 2026): release notes completed, tag unchanged, public server updated. |
| 19 | Cards with rounded corners (2-pixel arc, preferred to 3 after trying it on the C64); the characters " $ % & become the corners and show as "?" in the chat; tools/textes.py refuses them in translations; documentation screenshots redone (FR and EN). | Client v1.5, update (14 November 2026): release PRG replaced, tag unchanged. |
| 20 | Sliding card (two sprites) from the hand or the screen edge to the table; table and hand redrawn in place, without flicker; your card starts from the chosen slot; last card played automatically. Tuned by trying it on the C64: the first version flickered (table and hand were cleared then redrawn, twice per card); the card rose in a zigzag (cc65 got a negative difference multiplied by the step wrong); it started from under the table (MAIN arrives with JOUE and had already removed the card: its slot is now remembered as soon as JOUE arrives). Demo 6 matches the server (MAIN after JOUE). No protocol or server change. | Client v1.5, update (14 November 2026): release PRG replaced, tag unchanged. |
