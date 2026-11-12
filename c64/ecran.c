#include "ascii.h"
#include <string.h>
#include "ecran.h"

#define ECRAN   ((unsigned char *)0xC000)
#define CARS    ((unsigned char *)0xC800)
#define COULEUR ((unsigned char *)0xD800)
#define ROM_CAR ((unsigned char *)0xD000)

#define POKE(a, v) (*(volatile unsigned char *)(a) = (v))
#define PEEK(a)    (*(volatile unsigned char *)(a))

/* Codes écran des symboles dans notre jeu de caractères : @ £ ↑ ← */
static const unsigned char code_sym[4] = { 0, 28, 30, 31 };
/* Codes écran des symboles dans la ROM majuscules/graphiques */
static const unsigned char rom_sym[4] = { 65, 83, 88, 90 };

/* Tapis : le caractère # devient un motif de feutre, dessiné en vert clair
 * sur le fond vert dans toutes les cases vides. */
#define FEUTRE 35
static const unsigned char motif_feutre[8] = {
    0x80, 0x00, 0x08, 0x00, 0x80, 0x00, 0x08, 0x00
};

static const char *const rangs[8] = { "7 ", "8 ", "9 ", "10", "V ", "D ", "R ", "A " };

static unsigned off[25];

void ecran_init(void)
{
    unsigned char i, port;

    for (i = 0; i < 25; ++i) {
        off[i] = i * 40;
    }

    /* Copie des 64 premiers caractères de la ROM, puis des 4 symboles. */
    __asm__("sei");
    port = PEEK(1);
    POKE(1, port & 0xFB);               /* ROM caractères visible en $D000 */
    memcpy(CARS, ROM_CAR, 64 * 8);
    for (i = 0; i < 4; ++i) {
        memcpy(CARS + code_sym[i] * 8, ROM_CAR + rom_sym[i] * 8, 8);
    }
    memcpy(CARS + FEUTRE * 8, motif_feutre, 8);
    POKE(1, port);
    __asm__("cli");

    POKE(0x0291, 0x80);                 /* SHIFT+C= ne change plus de jeu de caractères */
    POKE(0x0288, 0xC0);                 /* écran du KERNAL en $C000 */
    POKE(0xDD00, PEEK(0xDD00) & 0xFC);  /* banque VIC 3 : $C000-$FFFF */
    POKE(0xD018, 0x02);                 /* écran +$0000, caractères +$0800 */
    POKE(0xD020, VERT);
    POKE(0xD021, VERT);
    POKE(0xD022, ROUGE);
    POKE(0xD023, NOIR);
    POKE(0xD024, GRIS_FONCE);
    ecran_effacer();
    POKE(0xD011, PEEK(0xD011) | 0x40);  /* mode couleur étendue */
}

void ecran_effacer(void)
{
    memset(ECRAN, FEUTRE, 1000);
    memset(COULEUR, VERT_CLAIR, 1000);
}

void effacer(unsigned char x, unsigned char y, unsigned char n)
{
    unsigned o = off[y] + x;
    memset(ECRAN + o, FEUTRE, n);
    memset(COULEUR + o, VERT_CLAIR, n);
}

/* Écrit un caractère ASCII (ou un symbole 1-4) en position o. */
static void car(unsigned o, unsigned char c, unsigned char coul, unsigned char fond)
{
    if (c >= 1 && c <= 4) {
        ECRAN[o] = code_sym[c - 1] | fond;
        COULEUR[o] = fond == FOND_VERT ? FC(c - 1) : BLANC;
        return;
    }
    if (c == ' ' && fond == FOND_VERT) {
        ECRAN[o] = FEUTRE;
        COULEUR[o] = VERT_CLAIR;
        return;
    }
    if (c == '#') {
        c = '?';                        /* son caractère dessine le tapis */
    } else if (c >= 32 && c < 64) {
        /* espace, chiffres, ponctuation : même code */
    } else if ((c >= 65 && c <= 91) || c == 93) {
        c -= 64;                        /* A-Z [ ] */
    } else {
        c = '?';                        /* @ \ ^ _ sont devenus des symboles */
    }
    ECRAN[o] = c | fond;
    COULEUR[o] = coul;
}

void ecrire(unsigned char x, unsigned char y, const char *s, unsigned char coul, unsigned char fond)
{
    unsigned o = off[y] + x;
    while (*s && x < 40) {
        car(o++, *s++, coul, fond);
        ++x;
    }
}

void ecrire_n(unsigned char x, unsigned char y, const char *s, unsigned char n,
              unsigned char coul, unsigned char fond)
{
    unsigned o = off[y] + x;
    while (n--) {
        car(o++, *s ? *s++ : ' ', coul, fond);
    }
}

void ligne_tirets(unsigned char y)
{
    unsigned o = off[y];
    memset(ECRAN + o, '-', 40);
    memset(COULEUR + o, BLANC, 40);
}

void carte(unsigned char x, unsigned char y, signed char c)
{
    char haut[5] = "    ";
    char bas[5] = "    ";
    unsigned char fond, coul;

    if (c < 0) {
        effacer(x, y, 4);
        effacer(x, y + 1, 4);
        return;
    }
    coul = c >> 3;
    fond = (coul & 1) ? FOND_ROUGE : FOND_NOIR;
    haut[1] = rangs[c & 7][0];
    haut[2] = rangs[c & 7][1];
    bas[1] = SYM(coul);
    ecrire(x, y, haut, BLANC, fond);
    ecrire(x, y + 1, bas, BLANC, fond);
}

void curseur(unsigned char x, unsigned char y)
{
    unsigned o = off[y] + x;
    ECRAN[o] = 32 | FOND_GRIS;
}
