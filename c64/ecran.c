#include "ascii.h"
#include <string.h>
#include "ecran.h"
#include "jeu.h"

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

/* Coins arrondis des cartes : " $ % & deviennent les quatre coins (haut gauche,
 * haut droit, bas gauche, bas droit). Case au fond blanc de la carte, pixels en
 * vert du plateau : l'angle de la carte paraît arrondi. */
static const unsigned char code_coin[4] = { 34, 36, 37, 38 };
static const unsigned char motif_coin[4][8] = {
    { 0xC0, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 },
    { 0x03, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 },
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0xC0 },
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x03 },
};

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
    for (i = 0; i < 4; ++i) {
        memcpy(CARS + code_coin[i] * 8, motif_coin[i], 8);
    }
    POKE(1, port);
    __asm__("cli");

    POKE(0x0291, 0x80);                 /* SHIFT+C= ne change plus de jeu de caractères */
    POKE(0x0288, 0xC0);                 /* écran du KERNAL en $C000 */
    POKE(0xDD00, PEEK(0xDD00) & 0xFC);  /* banque VIC 3 : $C000-$FFFF */
    POKE(0xD018, 0x02);                 /* écran +$0000, caractères +$0800 */
    POKE(0xD020, VERT);
    POKE(0xD021, VERT);
    POKE(0xD022, BLANC);                /* fond des cartes */
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
        COULEUR[o] = (fond == FOND_VERT || fond == FOND_BLANC) ? FC(c - 1) : BLANC;
        return;
    }
    if (c == ' ' && fond == FOND_VERT) {
        ECRAN[o] = FEUTRE;
        COULEUR[o] = VERT_CLAIR;
        return;
    }
    if (c >= COIN_HG && c <= COIN_BD) {
        ECRAN[o] = code_coin[c - COIN_HG] | fond;
        COULEUR[o] = VERT;
        return;
    }
    if (c == '#' || c == '"' || c == '$' || c == '%' || c == '&') {
        c = '?';                        /* caractères devenus le tapis et les coins */
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
    const char *rang;
    unsigned char coul;

    if (c < 0) {
        effacer(x, y, 4);
        effacer(x, y + 1, 4);
        return;
    }
    coul = c >> 3;
    rang = nom_rang(c & 7);           /* figures de la langue choisie */
    haut[0] = COIN_HG;
    haut[1] = rang[0];
    haut[2] = rang[1] ? rang[1] : ' ';
    haut[3] = COIN_HD;
    bas[0] = COIN_BG;
    bas[1] = SYM(coul);
    bas[3] = COIN_BD;
    ecrire(x, y, haut, FC(coul), FOND_BLANC);
    ecrire(x, y + 1, bas, FC(coul), FOND_BLANC);
}

void curseur(unsigned char x, unsigned char y)
{
    unsigned o = off[y] + x;
    ECRAN[o] = 32 | FOND_GRIS;
}

/* ---- Carte qui glisse : deux sprites --------------------------------------
 * Sprite 1 : corps blanc de la carte, élargi (16 points doublés = 32 pixels),
 * 16 lignes, coins arrondis. Sprite 0, devant : rang et symbole dans la couleur
 * de la carte, copiés du jeu de caractères, une case à droite du bord comme la
 * carte en texte. Données en $C400 et $C440 (blocs 16 et 17 de la banque 3). */
#define SPR_DATA   ((unsigned char *)0xC400)
#define SPR_PTR    ((unsigned char *)0xC3F8)
#define VIC        ((unsigned char *)0xD000)

void sprite_carte(signed char c)
{
    unsigned char i, coul = c >> 3;
    const char *rang = nom_rang(c & 7);
    const unsigned char *g1, *g2, *gs;
    unsigned char *corps = SPR_DATA + 64, *dessus = SPR_DATA;

    memset(SPR_DATA, 0, 128);
    for (i = 0; i < 16; ++i) {
        corps[i * 3] = (i == 0 || i == 15) ? 0x7F : 0xFF;
        corps[i * 3 + 1] = (i == 0 || i == 15) ? 0xFE : 0xFF;
    }
    /* Codes écran : chiffres tels quels, lettres A-Z = 1-26 */
    g1 = CARS + (unsigned)(rang[0] >= 'A' ? rang[0] - 64 : rang[0]) * 8;
    g2 = CARS + (unsigned)(rang[1] ? (rang[1] >= 'A' ? rang[1] - 64 : rang[1]) : 32) * 8;
    gs = CARS + (unsigned)code_sym[coul] * 8;
    for (i = 0; i < 8; ++i) {
        dessus[i * 3] = g1[i];
        dessus[i * 3 + 1] = g2[i];
        dessus[(i + 8) * 3] = gs[i];
    }
    SPR_PTR[0] = 16;
    SPR_PTR[1] = 17;
    VIC[0x27] = FC(coul);               /* couleur du sprite 0 */
    VIC[0x28] = BLANC;                  /* sprite 1 */
    VIC[0x1D] = 0x02;                   /* sprite 1 élargi */
    VIC[0x17] = 0;
    VIC[0x1C] = 0;                      /* deux sprites haute résolution */
    VIC[0x1B] = 0;                      /* devant le texte */
}

/* Position en pixels du coin haut gauche de la carte (coordonnées des sprites). */
void sprite_position(int x, int y)
{
    int x0 = x + 8;
    VIC[0x02] = (unsigned char)x;
    VIC[0x03] = (unsigned char)y;
    VIC[0x00] = (unsigned char)x0;
    VIC[0x01] = (unsigned char)y;
    VIC[0x10] = (x0 > 255 ? 0x01 : 0) | (x > 255 ? 0x02 : 0);
    VIC[0x15] = 0x03;
}

void sprite_cacher(void)
{
    VIC[0x15] = 0;
}
