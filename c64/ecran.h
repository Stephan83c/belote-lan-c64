/* Écran 40x25 en mode couleur étendue (ECM), écrit directement en mémoire.
 *
 * ECM : chaque case a sa couleur de texte (RAM couleur $D800) et l'un des
 * quatre fonds $D021-$D024, choisi par les bits 6-7 du code écran. On obtient
 * ainsi des cartes blanches, rang et symbole rouges ou noirs, sur un plateau vert. Seuls les
 * 64 premiers caractères existent : les symboles ♠ ♥ ♣ ♦ remplacent @ £ ↑ ←
 * dans un jeu de caractères copié en RAM, et le motif du tapis remplace # :
 * les cases vides du fond vert sont tissées de points vert clair.
 *
 * Banque VIC 3 : écran en $C000, caractères en $C800 (le programme s'arrête
 * sous $C000, voir __HIMEM__ dans le Makefile).
 */
#ifndef ECRAN_H
#define ECRAN_H

#define FOND_VERT  0x00
#define FOND_BLANC 0x40
#define FOND_NOIR  0x80
#define FOND_GRIS  0xC0

#define NOIR       0
#define BLANC      1
#define ROUGE      2
#define CYAN       3
#define VERT       5
#define VERT_CLAIR 13
#define BLEU       6
#define JAUNE      7
#define ORANGE     8
#define GRIS_FONCE 11
#define GRIS_CLAIR 15

/* Dans les chaînes affichées, les octets 1 à 4 dessinent ♠ ♥ ♣ ♦ (couleur 0-3 + 1)
 * dans la couleur de la carte. */
#define SYM(c) ((char)((c) + 1))
/* Octets 5 à 8 : coins arrondis d'une carte (haut gauche, haut droit, bas gauche, bas droit). */
#define COIN_HG 5
#define COIN_HD 6
#define COIN_BG 7
#define COIN_BD 8

void ecran_init(void);
void ecran_effacer(void);
void effacer(unsigned char x, unsigned char y, unsigned char n);
void ecrire(unsigned char x, unsigned char y, const char *s, unsigned char coul, unsigned char fond);
/* Écrit au plus n caractères et complète par des espaces. */
void ecrire_n(unsigned char x, unsigned char y, const char *s, unsigned char n,
              unsigned char coul, unsigned char fond);
void ligne_tirets(unsigned char y);
void carte(unsigned char x, unsigned char y, signed char c);
/* Carte qui glisse (sprites 0 et 1) : dessin de la carte c, position en pixels
 * sprite du coin haut gauche (case x, y de l'écran = 24 + 8x, 50 + 8y), effacement. */
void sprite_carte(signed char c);
void sprite_position(int x, int y);
void sprite_cacher(void);
/* Case de curseur (fond gris). */
void curseur(unsigned char x, unsigned char y);

/* Couleur C64 d'une couleur de carte : noir pour ♠ ♣, rouge pour ♥ ♦. */
#define FC(c) (((c) & 1) ? ROUGE : NOIR)

#endif
