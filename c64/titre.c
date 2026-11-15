/* Écran titre : bitmap multicolore (tools/titre.py) affiché jusqu'à une touche.
 *
 * Banque VIC 3 : bitmap en $E000 (RAM sous le KERNAL : le VIC la lit, le CPU
 * y écrit), matrice de couleurs à la place de l'écran texte en $C000 ; le jeu
 * de caractères en $C800 n'est pas touché. */
#include <cbm.h>
#include <joystick.h>
#include <string.h>
#include "ecran.h"
#include "son.h"
#include "ui.h"

#define POKE(a, v) (*(volatile unsigned char *)(a) = (v))
#define PEEK(a)    (*(volatile unsigned char *)(a))

/* L'image (tools/titre.py) est déjà décompressée, au chargement, par un
 * constructeur de c64/titre_dec.s : sa place sert ensuite aux variables. Appelée
 * avant ecran_init(), qui écrase la matrice de couleurs et rallume l'écran. */
void titre(void)
{
    POKE(0xD018, 0x08);                             /* matrice $C000, bitmap $E000 */
    POKE(0xD016, PEEK(0xD016) | 0x10);              /* multicolore */
    POKE(0xD011, (PEEK(0xD011) & 0xBF) | 0x30);     /* bitmap, écran allumé */

    son_musique(AIR_TITRE);
    /* SPACE (toute touche) ou le bouton du joystick ; on attend qu'il soit relâché */
    while (!cbm_k_getin() && !JOY_BTN_1(joy_read(JOY_2))) {
    }
    while (JOY_BTN_1(joy_read(JOY_2))) {
    }
    son_stop();

    POKE(0xD011, PEEK(0xD011) & 0xCF);              /* écran éteint, fin du bitmap */
    POKE(0xD016, PEEK(0xD016) & 0xEF);
}
