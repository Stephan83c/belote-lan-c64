# La belote en 5 minutes

*Pour jouer sa première partie de BELOTE LAN C64, sans avoir jamais touché une carte.*
English: [rules.md](rules.md)

## Le but

On joue à **quatre**, en **deux équipes** : vous et votre partenaire (en face de vous, au
Nord) contre vos deux adversaires (à l'Est et à l'Ouest). Le jeu compte **32 cartes** : 7, 8, 9,
10, Valet, Dame, Roi et As dans les quatre couleurs (pique, cœur, trèfle, carreau).

On joue des **manches** de huit plis. Les points s'additionnent d'une manche à l'autre ; la
**première équipe à 1000 points gagne**.

## Une manche, d'un coup d'œil

1. Chacun reçoit **5 cartes**, et une carte est retournée au milieu : elle **propose l'atout**.
2. Les **enchères** : un joueur *prend* (il choisit l'atout) ou tout le monde passe.
3. Le preneur reçoit la carte retournée, les autres complètent : chacun a **8 cartes**.
4. On joue **8 plis**. Le gagnant d'un pli entame le suivant.
5. On compte les points : le preneur doit faire **plus que ses adversaires**.

## L'atout

L'**atout** est une couleur choisie pour la manche. Une carte d'atout **bat toutes les cartes
des autres couleurs**, même un As. Dans la couleur d'atout, l'ordre de force change :

| Ordre à l'atout (du plus fort au plus faible) | Valet, 9, As, 10, Roi, Dame, 8, 7 |
|---|---|
| **Ordre hors atout** (du plus fort au plus faible) | As, 10, Roi, Dame, Valet, 9, 8, 7 |

Le **Valet d'atout** est donc la plus forte carte du jeu, suivi du **9 d'atout**.

## Les enchères

On commence par le joueur à droite du donneur, et chacun parle une fois.

- **Premier tour** : vous pouvez **prendre** à la couleur de la carte retournée, ou **passer**.
- **Second tour** (si personne n'a pris) : vous pouvez prendre à **une autre couleur**, ou passer.
- Si tout le monde passe aux deux tours, la donne est annulée et le donneur suivant redonne.

Dès qu'un joueur prend, les enchères s'arrêtent. **L'équipe du preneur s'engage à faire plus de
points que l'autre.**

**Quand prendre ?** Un repère simple, pas une règle : prenez si vous avez le **Valet** de cette
couleur avec au moins un autre atout, ou le **9 et l'As**, ou **quatre atouts ou plus**. Un
Valet seul est fragile ; sans atouts, passez. Avec l'expérience, vous affinerez : le partenaire
qui passe vous apprend aussi quelque chose.

## Jouer un pli

Le joueur à droite du donneur entame le premier pli : il joue une carte, c'est la **couleur
demandée**. Chacun joue ensuite une carte, **vers la droite**.
Le pli est gagné par :

- le **plus fort atout** s'il y en a ;
- sinon la **plus forte carte de la couleur demandée**.

Le gagnant ramasse le pli et joue la première carte du suivant.

## Les obligations

Vous ne jouez pas n'importe quelle carte. Le jeu **grise ou rentre** les cartes interdites : à
votre tour, seules les cartes jouables sortent du rang. Le serveur refuse de toute façon un
coup illégal.

| Votre situation | Ce que vous devez faire |
|---|---|
| Vous avez la couleur demandée | **Fournir** : jouer une carte de cette couleur. |
| On demande de l'atout et vous en avez | Jouer de l'atout, et **monter** (plus fort que le plus fort atout déjà posé) si vous le pouvez. Sinon, un atout plus faible. |
| Vous n'avez pas la couleur, **votre partenaire est maître du pli** | Libre : défaussez ce que vous voulez, ou coupez. |
| Vous n'avez pas la couleur, **un adversaire est maître** | **Couper** : jouer de l'atout. Si un adversaire a déjà coupé, **surcoupez** (plus fort) si vous le pouvez. |
| Vous ne pouvez pas surcouper | Vous ne **sous-coupez** pas : défaussez une autre couleur (sauf si vous n'avez que de l'atout). |
| Ni la couleur ni l'atout | Défaussez ce que vous voulez. |

*Maître* veut dire : la carte qui gagne le pli pour l'instant.

## Les points

| Carte | Hors atout | À l'atout |
|---|---|---|
| Valet | 2 | **20** |
| 9 | 0 | **14** |
| As | 11 | 11 |
| 10 | 10 | 10 |
| Roi | 4 | 4 |
| Dame | 3 | 3 |
| 8, 7 | 0 | 0 |

Les cartes valent **152 points**. S'y ajoutent :

- le **dix de der** : 10 points à l'équipe qui gagne le **dernier pli** ;
- la **belote-rebelote** : 20 points à qui possède le **Roi et la Dame d'atout**. Le jeu
  l'annonce tout seul quand vous posez ces deux cartes ; il n'y a rien à faire. Ces 20 points
  vous restent toujours, même si vous êtes dedans.

Une manche vaut donc **162 points** (plus 20 de belote s'il y en a).

## Le contrat

- **Contrat rempli** : le preneur fait **strictement plus** que la défense (82 sur 162 sans
  belote). Chaque équipe garde ses points.
- **Dedans** : le preneur fait moins. La **défense marque 162** ; le preneur ne garde que sa
  belote éventuelle.
- **Égalité (litige)** : la défense marque ses points ; ceux du preneur sont **mis en réserve**
  pour l'équipe qui gagnera la manche suivante.
- **Capot** : une équipe gagne **les 8 plis** et marque **252** au lieu de 162. Si c'est la
  défense, le preneur est dedans.

Il n'y a pas d'annonces (tierce, cinquante, cent, carré) : seule la belote-rebelote compte.

## Un pli commenté

L'atout est **cœur ♥**. Vous êtes au Sud et vous entamez avec le 10 de pique.

| Joueur | Carte | Pourquoi |
|---|---|---|
| Vous (Sud) | 10♠ | Vous demandez pique. |
| Ouest | Dame♠ | Il a du pique, il doit fournir. |
| Nord (partenaire) | 7♠ | Il fournit aussi. Il ne peut pas gagner, mais c'est son seul pique. |
| Est | 8♥ | Il n'a plus de pique et un adversaire (vous) est maître : il doit **couper** à l'atout. |

Gagnant : **Est**, avec le 8♥, car un atout bat toute carte de pique, même le 10. Il ramasse
le pli (10 + 3 + 0 + 0 = **13 points**) et entame le suivant.

## Les touches

**C64** : les chiffres 1 à 8 jouent la carte numérotée, 1 à 4 choisissent à l'enchère, **F8** affiche les règles, **F3** le tchat,
**F7** quitte. Le joystick en port 2 (ou les flèches et RETURN) permet de tout faire sans le
clavier.

**Client PC** : flèches et Entrée, ou 1 à 8 ; **A** les règles, **D** le dernier pli, **T** le
tchat, **Q** quitter.

Bonne partie !
