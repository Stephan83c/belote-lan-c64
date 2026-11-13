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

extern const unsigned char titre_bitmap[8000];
extern const unsigned char titre_ecran[1000];
extern const unsigned char titre_couleur[1000];

void titre(void)
{
    POKE(0xD011, PEEK(0xD011) & 0xEF);              /* écran éteint pendant la copie */
    memcpy((void *)0xE000, titre_bitmap, 8000);
    memcpy((void *)0xC000, titre_ecran, 1000);
    memcpy((void *)0xD800, titre_couleur, 1000);
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
