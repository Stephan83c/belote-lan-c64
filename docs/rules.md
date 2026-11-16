# Belote in 5 minutes

*To play your first game of BELOTE LAN C64, even if you have never held a card.*
Français : [regles.fr.md](regles.fr.md)

## The goal

You play in **four**, in **two teams**: you and your partner (opposite you, North) against your
two opponents (East and West). The deck has **32 cards**: 7, 8, 9, 10, Jack, Queen, King and Ace
in the four suits (spades, hearts, clubs, diamonds).

You play **rounds** of eight tricks. Points add up from round to round; the **first team to reach
1000 points wins**.

## A round at a glance

1. Everyone gets **5 cards**, and one card is turned up in the middle: it **suggests the trump**.
2. **Bidding**: a player *takes* (and so picks the trump suit), or everyone passes.
3. The taker gets the turned-up card, the others are topped up: everyone has **8 cards**.
4. You play **8 tricks**. The winner of a trick leads the next one.
5. Points are counted: the taker must score **more than the opponents**.

## Trump

**Trump** is a suit chosen for the round. A trump card **beats every card of the other suits**,
even an Ace. Within the trump suit, the order of strength changes:

| **Trump order** (strongest to weakest) | Jack, 9, Ace, 10, King, Queen, 8, 7 |
|---|---|
| **Plain-suit order** (strongest to weakest) | Ace, 10, King, Queen, Jack, 9, 8, 7 |

The **Jack of trumps** is therefore the strongest card in the game, followed by the **9 of trumps**.

## Bidding

It starts with the player to the dealer's right, and everyone speaks once.

- **First round**: you may **take** in the suit of the turned-up card, or **pass**.
- **Second round** (if nobody took): you may take in **another suit**, or pass.
- If everyone passes in both rounds, the deal is cancelled and the next dealer deals again.

As soon as a player takes, bidding stops. **The taker's team commits to scoring more points than
the other team.**

**When to take?** A simple guideline, not a rule: take if you hold the **Jack** of that suit plus
at least one other trump, or the **9 and the Ace**, or **four or more trumps**. A lone Jack is
fragile; with no trumps, pass. With experience you will refine this: a partner who passes also
tells you something.

## Playing a trick

The player to the dealer's right leads the first trick: they play a card, which sets the **suit
led**. Everyone then plays one card, **going to the right**. The trick is won by:

- the **highest trump**, if there is one;
- otherwise the **highest card of the suit led**.

The winner collects the trick and leads the next one.

## What you must do

You cannot play just any card. The game **greys out or lifts** the forbidden cards: on your turn,
only the playable cards stick out of the row. The server rejects an illegal play anyway.

| Your situation | What you must do |
|---|---|
| You hold the suit led | **Follow suit**: play a card of that suit. |
| Trump is led and you hold some | Play a trump, and **go higher** (than the highest trump already played) if you can. Otherwise, a lower trump. |
| You lack the suit, **your partner is winning the trick** | Free: discard anything, or trump. |
| You lack the suit, **an opponent is winning** | You must **trump** (play a trump). If an opponent has already trumped, **overtrump** (go higher) if you can. |
| You cannot overtrump | You may not **undertrump**: discard another suit (unless you hold only trumps). |
| Neither the suit nor any trump | Discard anything. |

*Winning* means: the card that is currently taking the trick.

## Points

| Card | Plain suit | Trump |
|---|---|---|
| Jack | 2 | **20** |
| 9 | 0 | **14** |
| Ace | 11 | 11 |
| 10 | 10 | 10 |
| King | 4 | 4 |
| Queen | 3 | 3 |
| 8, 7 | 0 | 0 |

The cards are worth **152 points**. On top of that:

- the **last trick** ("dix de der"): 10 points to the team that wins the **final trick**;
- **belote-rebelote**: 20 points to whoever holds the **King and Queen of trumps**. The game
  announces it by itself when you play those two cards; there is nothing to do. Those 20 points
  always stay with you, even if you are "dedans".

A round is therefore worth **162 points** (plus 20 for belote, if any).

## The contract

- **Contract made**: the taker scores **strictly more** than the defence (82 out of 162 without
  belote). Each team keeps its points.
- **Dedans** (failed): the taker scores less. The **defence scores 162**; the taker keeps only
  their belote, if any.
- **Tie (litige)**: the defence scores its points; the taker's points are **held in reserve** for
  the team that wins the next round.
- **Capot**: a team wins **all 8 tricks** and scores **252** instead of 162. If it is the defence,
  the taker is dedans.

Points are counted **exactly** here, without rounding: 162 and 252. At the table many players round
to the nearest ten and say "160" for a dedans and "250" for a capot: it is the same thing, not a
mistake.

There are no declarations (tierce, fifty, hundred, four of a kind): only belote-rebelote counts.

## A trick, explained

Trump is **hearts ♥**. You are South and you lead the 10 of spades.

| Player | Card | Why |
|---|---|---|
| You (South) | 10♠ | You lead spades. |
| West | Queen♠ | They hold spades, so they must follow. |
| North (partner) | 7♠ | Follows suit too. They cannot win, but it is their only spade. |
| East | 8♥ | Out of spades, and an opponent (you) is winning: they must **trump**. |

Winner: **East**, with the 8♥, because a trump beats any spade, even the 10. They collect the
trick (10 + 3 + 0 + 0 = **13 points**) and lead the next one.

## Keys

**C64**: digits 1 to 8 play the numbered card, 1 to 4 choose a bid, **F8** shows the rules, **F3**
the chat, **F7** quits. The joystick in port 2 (or the arrows and RETURN) does everything without
the keyboard.

**PC client**: arrows and Enter, or 1 to 8; **A** the rules, **D** the last trick, **T** the chat,
**Q** quit.

Have a good game!
