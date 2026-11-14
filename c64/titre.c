/* Écran titre : bitmap multicolore (tools/titre.py) affiché jusqu'à une touche.
 *
 * Banque VIC 3 : bitmap en $E000 (RAM sous le KERNAL : le VIC la lit, le CPU
 * y écrit), matrice de couleurs à la place de l'écran texte en $C000 ; le jeu
 * de caractères en $C800 n'est pas touché. */
#include <cbm.h>
#include <string.h>
#include "ecran.h"
#include "son.h"
#include "ui.h"

#define POKE(a, v) (*(volatile unsigned char *)(a) = (v))
#define PEEK(a)    (*(volatile unsigned char *)(a))

/* Image compressée par tools/titre.py : une case de feutre (8 octets de bitmap,
 * matrice, couleur), un bit par case (1 = feutre), puis les autres cases. */
extern const unsigned char titre_feutre[10];
extern const unsigned char titre_cases[125];
extern const unsigned char titre_autres[];

/* c64/titre_dec.s */
void titre_decompresser(void);

void titre(void)
{
    POKE(0xD011, PEEK(0xD011) & 0xEF);              /* écran éteint pendant la copie */
    titre_decompresser();
    POKE(0xD018, 0x08);                             /* matrice $C000, bitmap $E000 */
    POKE(0xD016, PEEK(0xD016) | 0x10);              /* multicolore */
    POKE(0xD011, (PEEK(0xD011) & 0xBF) | 0x30);     /* bitmap, écran allumé */

    son_musique(AIR_TITRE);
    while (!cbm_k_getin()) {
    }
    son_stop();

    POKE(0xD011, PEEK(0xD011) & 0xEF);
    POKE(0xD016, PEEK(0xD016) & 0xEF);
    POKE(0xD018, 0x02);
    ecran_effacer();
    POKE(0xD011, (PEEK(0xD011) & 0xDF) | 0x50);     /* texte ECM, écran allumé */
}
