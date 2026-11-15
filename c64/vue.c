/* Dessin des écrans : table (SPEC 8.1), règles, réglages F1, fin de partie. */
#include "ascii.h"
#include <stdio.h>
#include <string.h>
#include "ecran.h"
#include "jeu.h"
#include "son.h"
#include "textes.h"
#include "ui.h"

unsigned char raz_conf, regles, param, param_sel, tchat, tchat_n;
unsigned param_cible, param_inactif;
char tchat_txt[TCHAT_MAX + 1];

static char t[41];

/* Positions par place relative : 0 SUD, 1 EST, 2 NORD, 3 OUEST, symétriques
 * autour du milieu de l'écran (entre les colonnes 19 et 20). nom_x : début de la
 * case du nom (13 cases : 6 lettres et « (CHEF) » ; 14 pour SUD et NORD, centrés
 * sur leur carte). OUEST de 1 à 13, EST de 27 à 39 : le centre de la ligne 5 (14
 * à 26) reste libre. Les noms s'alignent sur le bord extérieur de leur carte. */
static const unsigned char nom_x[4] = { 13, 27, 13, 1 };
static const unsigned char nom_y[4] = { 10, 5, 2, 5 };
static const unsigned char carte_x[4] = { 18, 32, 18, 4 };
static const unsigned char carte_y[4] = { 8, 6, 3, 6 };

static unsigned char suis_chef(void)
{
    return moi >= 0 && chef == moi;
}

unsigned char vue_courante(void)
{
    if (regles) {
        return V_REGLES;
    }
    if (param) {
        return V_PARAM;
    }
    if (etat == E_FIN_PARTIE) {
        return V_FIN;
    }
    return V_TABLE;
}

/* Barre de touches sur le bandeau noir du bas : les touches (F1 à F8, 1-8, 1-4)
 * en jaune, le reste en gris clair. */
void barre(const char *s)
{
    unsigned char x = 1, n = 0;
    char c[2];
    bandeau(24);
    c[1] = 0;
    while (*s && x < 40) {
        if ((s[0] == 'F' && s[1] >= '1' && s[1] <= '8') ||
            (s[0] >= '1' && s[0] <= '9' && s[1] == '-')) {
            n = s[1] == '-' ? 3 : 2;
        }
        c[0] = *s++;
        ecrire(x++, 24, c, n ? JAUNE : GRIS_CLAIR, FOND_NOIR);
        if (n) {
            --n;
        }
    }
}

static void barre_table(void)
{
    unsigned char s = T_B_BASE;
    if (raz_conf) {
        s = T_B_RAZ;
    } else if (tchat) {
        s = T_B_TCHAT;
    } else if (etat == E_ATTENTE || etat == E_AUCUN) {
        if (suis_chef()) {
            s = T_B_CHEF_ATTENTE;
        }
    } else if (suis_chef()) {
        /* Partie lancée : le chef a F4 RAZ ; TCHAT devient MSG faute de place. */
        if (etat == E_COURS && tour == moi) {
            s = atout < 0 ? T_B_CHEF_ENCH : T_B_CHEF_CARTE;
        } else if (etat == E_FIN_MANCHE) {
            s = T_B_CHEF_MANCHE;
        } else {
            s = T_B_CHEF;
        }
    } else if (etat == E_COURS && tour == moi) {
        s = atout < 0 ? T_B_ENCH : T_B_CARTE;
    } else if (etat == E_FIN_MANCHE && suite) {
        s = T_B_MANCHE;
    }
    barre(T(s));
}

/* Titre d'un écran, aligné à droite de « BELOTE LAN C64 ». */
static void titre_ecran(unsigned char id)
{
    bandeau(0);
    ecrire(1, 0, "BELOTE LAN C64", JAUNE, FOND_NOIR);
    ecrire(39 - strlen(T(id)), 0, T(id), BLANC, FOND_NOIR);
}

/* Bandeau noir du haut : BELOTE en jaune, l'atout dans sa couleur, puis les
 * scores, NOUS et EUX dans la couleur de chaque équipe. */
static void entete(void)
{
    unsigned char nous = moi & 1, x;
    bandeau(0);
    ecrire(1, 0, T(T_V_ATOUT), GRIS_CLAIR, FOND_NOIR);
    ecrire(1, 0, "BELOTE", JAUNE, FOND_NOIR);
    t[1] = 0;
    t[0] = atout >= 0 ? SYM(atout) : '?';
    ecrire(2 + strlen(T(T_V_ATOUT)), 0, t, BLANC, FOND_NOIR);
    ecrire(21, 0, T(T_NOUS), COUL_EQUIPE(nous), FOND_NOIR);
    sprintf(t, "%04u", scores[nous]);
    ecrire(22 + strlen(T(T_NOUS)), 0, t, BLANC, FOND_NOIR);
    sprintf(t, "%04u", scores[nous ^ 1]);
    x = 39 - 5 - strlen(T(T_EUX));
    ecrire(x, 0, T(T_EUX), COUL_EQUIPE(nous + 1), FOND_NOIR);
    ecrire(x + strlen(T(T_EUX)) + 1, 0, t, BLANC, FOND_NOIR);
}

/* Table redessinée sur place, sans effacer d'abord : chaque nom (13 cases, avec
 * « (CHEF) ») et chaque emplacement de carte est réécrit tel quel, rien ne
 * disparaît le temps du dessin (pas de clignotement). */
#define LARGEUR_NOM 13

static void zone_table(void)
{
    unsigned char y, p, r, n, d;
    const char *libelle = 0;

    if (moi < 0) {
        for (y = 2; y <= 10; ++y) {
            effacer(0, y, 40);
        }
        return;
    }
    for (p = 0; p < 4; ++p) {
        r = REL(p);
        strcpy(t, nom_place(p));
        if (humain[p]) {
            if ((etat == E_ATTENTE || etat == E_AUCUN) && chef == (signed char)p) {
                strcat(t, " (");
                strcat(t, T(T_V_CHEF));
                strcat(t, ")");
            }
        }
        /* Espaces devant le nom (sans différence négative, voir CLAUDE.md) :
         * OUEST commence au bord gauche de sa carte (colonne 4), EST finit au
         * bord droit de la sienne (35) ; un nom trop long reste dans sa case. */
        n = strlen(t);
        if (r == 1) {
            d = n < 9 ? 9 - n : 0;
        } else if (r == 3) {
            d = n < 11 ? 3 : 13 - n;
        } else {
            d = (14 - n) / 2;
        }
        memmove(t + d, t, n + 1);
        memset(t, ' ', d);
        ecrire_n(nom_x[r], nom_y[r], t, (r & 1) ? LARGEUR_NOM : LARGEUR_NOM + 1,
                 COUL_PLACE(p), FOND_VERT);
        carte(carte_x[r], carte_y[r], pli[p]);
    }
    /* Centre : carte retournée (enchères) ou prise, avec son libellé. Les cases 14
     * à 26 de la ligne 5 sont entre le nom de l'OUEST et celui de l'EST. */
    effacer(14, 5, 13);
    if (etat == E_COURS && retournee >= 0) {
        libelle = T(T_V_RETOURNEE);
        carte(18, 6, retournee);
    } else if (etat == E_COURS && prise >= 0) {
        libelle = T(T_V_PRISE);
        carte(18, 6, prise);
    } else {
        carte(18, 6, -1);
    }
    if (libelle) {
        ecrire(20 - (strlen(libelle) + 1) / 2, 5, libelle, GRIS_CLAIR, FOND_VERT);
    }
}

#define PEEK(a) (*(volatile unsigned char *)(a))
#define GLISSE_ETAPES 14

/* Attend le bas de l'écran (ligne 251) : une étape par image, sans scintillement. */
static void image_suivante(void)
{
    while (PEEK(0xD012) != 251) {
    }
    while (PEEK(0xD012) == 251) {
    }
}

/* Point k (sur n) entre a et b. Sans différence négative : cc65 la multipliait
 * mal par k et la carte montait en zigzag. */
static int etape(int a, int b, unsigned char k, unsigned char n)
{
    if (b >= a) {
        return a + (unsigned)(b - a) * k / n;
    }
    return a - (unsigned)(a - b) * k / n;
}

/* La carte 0 (déjà dessinée par sprite_carte) va de a à b en n images, en
 * accélérant si accel. Chaque position est calculée avant d'attendre l'image. */
static void deplacer(int ax, int ay, int bx, int by, unsigned char n, unsigned char accel)
{
    unsigned char k, e;
    int x, y;

    for (k = 1; k <= n; ++k) {
        e = accel ? k * k / n : k;
        x = etape(ax, bx, e, n);
        y = etape(ay, by, e, n);
        image_suivante();
        sprite_position(x, y);
    }
}

/* La carte jouée par la place p glisse de sa main jusqu'à sa place sur le tapis :
 * depuis la main pour soi, depuis le bord de l'écran pour les autres. */
static void glisser(signed char p)
{
    unsigned char r = REL(p), i;
    int sx, sy, dx = 24 + carte_x[r] * 8, dy = 50 + carte_y[r] * 8;

    switch (r) {
    case 0:                                 /* soi : depuis la carte choisie */
        sx = dx;
        sy = 50 + 21 * 8;
        if (glisse_case >= 0) {
            /* Une fois le coup envoyé, la main est redescendue (lignes 21-22)
             * avant que JOUE n'arrive : la carte part de là. */
            i = (unsigned char)glisse_case;
            sx = 24 + i * 5 * 8;
            effacer(i * 5, 21, 4);          /* la carte quitte la main */
            effacer(i * 5, 22, 4);
        }
        break;
    case 1:  sx = 344; sy = dy; break;      /* EST : bord droit */
    case 2:  sx = dx;  sy = 20; break;      /* NORD : bord haut */
    default: sx = 0;   sy = dy; break;      /* OUEST : bord gauche */
    }
    sprite_carte(pli[p]);
    deplacer(sx, sy, dx, dy, GLISSE_ETAPES, 0);
    image_suivante();
}

/* Pli ramassé : le pli complet reste un instant, puis les cartes rejoignent le
 * centre une par une (la carte du gagnant en dernier, sur le dessus) et le paquet
 * part vers le gagnant : vers son nom pour soi, hors de l'écran par son bord pour
 * les autres. Une seule carte bouge à la fois (sprites 0 et 1, comme la carte
 * qui glisse). Le bruitage PLI (tools/musique.py, un glissement) part avec le
 * paquet. */
#define PAUSE_PLI      30   /* 1/60 s où le pli complet reste visible */
#define REUNIR_ETAPES   5   /* images (1/50 s) par carte */
#define CENTRE_CX      18   /* case 18, 6 : libre pendant les plis */
#define CENTRE_CY       6
#define CENTRE_X       (24 + CENTRE_CX * 8)
#define CENTRE_Y       (50 + CENTRE_CY * 8)

/* Départ du paquet selon la place relative du gagnant : arrivée et images. */
static const int sortie_x[4] = { CENTRE_X, 344, CENTRE_X, 0 };
static const unsigned char sortie_y[4] = { 50 + 10 * 8, CENTRE_Y, 20, CENTRE_Y };
static const unsigned char sortie_n[4] = { 8, 14, 14, 14 };

void donner(signed char c, int sx, int sy, unsigned char x, unsigned char y)
{
    int dx = 24 + x * 8, dy = 50 + y * 8;

    sprite_carte(c);
    son_effet(FX_CARTE);
    image_suivante();
    sprite_position(sx, sy);
    deplacer(sx, sy, dx, dy, GLISSE_ETAPES, 0);
    carte(x, y, c);
    image_suivante();
    sprite_cacher();
}

static void ramasser(signed char g)
{
    unsigned char i, p, r, t0 = PEEK(0xA2);

    while ((unsigned char)(PEEK(0xA2) - t0) < PAUSE_PLI) {
    }
    /* Dans l'ordre des places après le gagnant, lui en dernier. */
    for (i = 1; i <= 4; ++i) {
        p = (g + i) & 3;
        r = REL(p);
        sprite_carte(pli[p]);           /* sprite caché pendant qu'on le dessine */
        image_suivante();
        sprite_position(24 + carte_x[r] * 8, 50 + carte_y[r] * 8);
        carte(carte_x[r], carte_y[r], -1);
        deplacer(24 + carte_x[r] * 8, 50 + carte_y[r] * 8, CENTRE_X, CENTRE_Y,
                 REUNIR_ETAPES, 0);
        carte(CENTRE_CX, CENTRE_CY, pli[p]);    /* posée sur le paquet */
        son_effet(FX_RAMASSE);
        image_suivante();
        sprite_cacher();
    }
    /* Le paquet (la carte du gagnant, déjà dans le sprite) part. */
    r = REL(g);
    sprite_position(CENTRE_X, CENTRE_Y);
    carte(CENTRE_CX, CENTRE_CY, -1);
    son_effet(FX_PLI);
    deplacer(CENTRE_X, CENTRE_Y, sortie_x[r], sortie_y[r], sortie_n[r], 1);
    image_suivante();
    sprite_cacher();
    pli[0] = pli[1] = pli[2] = pli[3] = -1;
}

static void zone_journal(void)
{
    unsigned char i, y;
    struct entree *e;

    for (i = 0; i < JOURNAL_N; ++i) {
        y = 12 + i;
        e = &journal[i];
        if (e->nom[0]) {
            ecrire_n(0, y, e->nom, 6, e->coul_nom, FOND_VERT);
            ecrire(6, y, ": ", BLANC, FOND_VERT);
            ecrire_n(8, y, e->texte, 32, e->coul_texte, FOND_VERT);
        } else {
            ecrire_n(0, y, e->texte, 40, e->coul_texte, FOND_VERT);
        }
    }
}

static void zone_saisie(void)
{
    effacer(0, 18, 40);
    if (tchat) {
        ecrire(0, 18, T(T_V_VOUS), BLANC, FOND_VERT);
        ecrire(6, 18, ": ", BLANC, FOND_VERT);
        ecrire(8, 18, tchat_txt, BLANC, FOND_VERT);
        curseur(8 + tchat_n, 18);
    }
}

/* Un choix d'enchère : « 1 PRENDRE ♠ ». Celui qu'on a choisi (joystick, curseur)
 * est sur une étiquette blanche, sinon touche en jaune et mot en blanc. */
static unsigned char choix(unsigned char x, char touche, const char *mot, char sym,
                           unsigned char actif)
{
    unsigned char fond = actif ? FOND_BLANC : FOND_VERT;
    char s[2];
    s[1] = 0;
    s[0] = ' ';
    ecrire(x - 1, 19, s, BLANC, fond);
    s[0] = touche;
    ecrire(x, 19, s, actif ? ROUGE : JAUNE, fond);
    s[0] = ' ';
    ecrire(x + 1, 19, s, BLANC, fond);
    x += 2;
    if (*mot) {
        ecrire(x, 19, mot, actif ? NOIR : BLANC, fond);
        x += strlen(mot);
        if (sym) {
            ecrire(x++, 19, s, BLANC, fond);
        }
    }
    if (sym) {
        s[0] = sym;
        ecrire(x++, 19, s, BLANC, fond);
    }
    s[0] = ' ';
    ecrire(x, 19, s, BLANC, fond);
    return x + 3;
}

static void zone_encheres(void)
{
    unsigned char c, k, x;

    effacer(0, 19, 40);
    if (etat == E_ATTENTE) {
        sprintf(t, T(T_V_ATTENTE), nom_place(chef), cible);
        ecrire(0, 19, t, GRIS_CLAIR, FOND_VERT);
    } else if (etat == E_COURS && atout < 0 && retournee >= 0) {
        if (tour != moi) {
            sprintf(t, T(T_V_AU_TOUR), nom_place(tour));
            ecrire(0, 19, t, GRIS_CLAIR, FOND_VERT);
        } else if (tour_ench == 1) {
            /* 1 PRENDRE ♠   2 PASSE */
            x = choix(1, '1', T(T_V_PRENDRE), SYM(retournee >> 3), ench_sel == 0);
            choix(x, '2', T(T_V_PASSER), 0, ench_sel == 1);
        } else {
            x = 1;
            k = 0;
            for (c = 0; c < 4; ++c) {
                if (c != (unsigned char)(retournee >> 3)) {
                    x = choix(x, '1' + k, "", SYM(c), ench_sel == k);
                    ++k;
                }
            }
            choix(x, '4', T(T_V_PASSER), 0, ench_sel == 3);
        }
        /* Le journal ne montre pas toujours les passes du 1er tour. */
        k = tour_ench == 1 ? T_V_TOUR1 : T_V_TOUR2;
        ecrire(40 - strlen(T(k)), 19, T(k), BLANC, FOND_VERT);
    } else if (etat == E_COURS && atout >= 0 && tour == moi) {
        ecrire(0, 19, T(T_V_A_VOUS), JAUNE, FOND_VERT);
    } else if (etat == E_FIN_MANCHE && suite) {
        suite_vue = suite_secondes();
        sprintf(t, T(T_V_SUITE), T(manche_nous ? T_NOUS : T_EUX), suite_vue);
        ecrire(0, 19, t, COUL_EQUIPE(manche_nous ? moi : moi + 1), FOND_VERT);
    } else if (etat == E_FIN_MANCHE) {          /* serveur sans SUITE (v1.5) */
        ecrire(0, 19, T(suis_chef() ? T_V_FIN_CHEF : T_V_FIN_AUTRE), GRIS_CLAIR, FOND_VERT);
    }
}

/* Main, sur place, emplacement par emplacement (pas de clignotement). À mon tour,
 * les cartes que la règle permet sortent du rang (lignes 20-21, sur les tirets) ;
 * le numéro de la carte choisie (joystick, curseur) est sur fond blanc. */
static void zone_main(void)
{
    unsigned char i, x, ok[8], a_moi = etat == E_COURS && atout >= 0 && tour == moi;

    jouables(ok);
    if (a_moi && (sel >= nmain || !ok[sel])) {
        for (sel = 0; sel < nmain && !ok[sel]; ++sel) {
        }
    }
    t[1] = 0;
    for (i = 0; i < 8; ++i) {
        x = i * 5;
        if (i < nmain && a_moi && ok[i]) {
            carte(x, 20, main_c[i]);
            effacer(x, 22, 4);
        } else {
            trait(x, 20, 5);
            carte(x, 21, i < nmain ? main_c[i] : -1);
        }
        effacer(x + 1, 23, 1);
        if (i < nmain) {
            t[0] = '1' + i;
            if (a_moi && i == sel) {
                ecrire(x + 1, 23, t, NOIR, FOND_BLANC);
            } else {
                ecrire(x + 1, 23, t, !a_moi ? GRIS_FONCE : (ok[i] ? JAUNE : GRIS_CLAIR), FOND_VERT);
            }
        }
    }
}

/* Tableau de fin de manche : une grande carte blanche aux coins arrondis, posée
 * au centre du tapis (cases 10 à 29, lignes 3 à 9), dessinée après les noms.
 * Équipes en bleu et en rouge foncés, lisibles sur le blanc. */
#define PX 10
#define PW 20
static unsigned char panneau_pose;
#define COUL_FONCE(e) (((e) & 1) ? ROUGE : BLEU)

static void ligne_panneau(unsigned char y, const char *s, unsigned char coul)
{
    ecrire_n(PX + 1, y, "", PW - 2, NOIR, FOND_BLANC);
    ecrire(PX + 1 + (PW - 2 - strlen(s)) / 2, y, s, coul, FOND_BLANC);
}

/* « NOUS 72  EUX 90 » centré. */
static void scores_panneau(unsigned char y, int a, int b)
{
    unsigned char nous = moi & 1, x, e = 1;
    char n1[6], n2[6];
    sprintf(n1, "%d", nous ? b : a);
    sprintf(n2, "%d", nous ? a : b);
    x = strlen(T(T_NOUS)) + strlen(n1) + strlen(T(T_EUX)) + strlen(n2) + 4;
    if (x > PW - 2) {                   /* espagnol, deux scores à 4 chiffres */
        e = 0;
        x -= 2;
    }
    ecrire_n(PX + 1, y, "", PW - 2, NOIR, FOND_BLANC);
    x = PX + 1 + (PW - 2 - x) / 2;
    ecrire(x, y, T(T_NOUS), COUL_FONCE(nous), FOND_BLANC);
    x += strlen(T(T_NOUS)) + e;
    ecrire(x, y, n1, NOIR, FOND_BLANC);
    x += strlen(n1) + 2;
    ecrire(x, y, T(T_EUX), COUL_FONCE(nous + 1), FOND_BLANC);
    x += strlen(T(T_EUX)) + e;
    ecrire(x, y, n2, NOIR, FOND_BLANC);
}

static void panneau_manche(void)
{
    unsigned char id = 0, coul = NOIR;
    signed char pe = preneur >= 0 ? (preneur & 1) : -1;
    char coin[2];

    coin[1] = 0;
    ligne_panneau(3, "", NOIR);
    ligne_panneau(9, "", NOIR);
    coin[0] = COIN_HG;
    ecrire(PX, 3, coin, VERT, FOND_BLANC);
    coin[0] = COIN_HD;
    ecrire(PX + PW - 1, 3, coin, VERT, FOND_BLANC);
    coin[0] = COIN_BG;
    ecrire(PX, 9, coin, VERT, FOND_BLANC);
    coin[0] = COIN_BD;
    ecrire(PX + PW - 1, 9, coin, VERT, FOND_BLANC);
    for (id = 4; id <= 8; ++id) {
        ecrire_n(PX, id, "", 1, NOIR, FOND_BLANC);
        ecrire_n(PX + PW - 1, id, "", 1, NOIR, FOND_BLANC);
    }
    id = 0;
    ligne_panneau(4, T(T_P_MANCHE), NOIR);
    scores_panneau(5, manche_pts[0], manche_pts[1]);
    if (capot_eq >= 0) {
        id = T_P_CAPOT;
        coul = COUL_FONCE(capot_eq);
    } else if (litige_m) {
        id = T_P_LITIGE;
    } else if (pe >= 0) {
        id = manche_pts[pe] == 0 ? T_P_DEDANS : T_P_REUSSI;
        coul = COUL_FONCE(manche_pts[pe] == 0 ? pe + 1 : pe);
    }
    if (id) {
        ligne_panneau(6, T(id), coul);
    } else {
        ligne_panneau(6, "", NOIR);
    }
    ligne_panneau(7, T(T_P_TOTAL), GRIS_FONCE);
    scores_panneau(8, scores[0], scores[1]);
    panneau_pose = 1;
}

static void vue_table(void)
{
    unsigned char y;
    if (panneau_pose && (etat != E_FIN_MANCHE || sale == D_TOUT)) {
        for (y = 3; y <= 9; ++y) {
            effacer(PX, y, PW);
        }
        panneau_pose = 0;
        sale |= D_TABLE;
    }
    if (sale == D_TOUT) {
        ligne_tirets(11);
        ligne_tirets(20);
    }
    if (sale & D_ENTETE) {
        entete();
    }
    if (sale & D_TABLE) {
        if (glisse >= 0 && pli[glisse] >= 0) {
            /* tapis sans la carte, glissement, puis la carte en texte */
            signed char c = pli[glisse];
            pli[glisse] = -1;
            zone_table();
            pli[glisse] = c;
            glisser(glisse);
            carte(carte_x[REL(glisse)], carte_y[REL(glisse)], c);   /* seule la carte arrivée */
            sprite_cacher();
        } else {
            zone_table();
        }
        glisse = -1;
        if (ramasse >= 0) {
            if (pli[0] >= 0 && pli[1] >= 0 && pli[2] >= 0 && pli[3] >= 0) {
                ramasser(ramasse);
            } else {
                son_effet(FX_PLI);
            }
            ramasse = -1;
        }
        if (etat == E_FIN_MANCHE) {
            panneau_manche();
        }
    }
    if (sale & D_JOURNAL) {
        zone_journal();
    }
    if (sale & D_SAISIE) {
        zone_saisie();
    }
    if (sale & D_ENCH) {
        zone_encheres();
    }
    if (sale & D_MAIN) {
        zone_main();
    }
    if (sale & D_BARRE) {
        barre_table();
    }
}

static void vue_regles(void)
{
    unsigned char i;
    if (sale != D_TOUT) {
        return;
    }
    titre_ecran(T_T_REGLES);
    for (i = 0; i < NB_REGLES; ++i) {
        ecrire(0, 3 + i, T(T_REGLES + i), BLANC, FOND_VERT);
    }
    barre(T(T_B_RETOUR));
}

static void vue_param(void)
{
    titre_ecran(T_T_PARAM);
    sprintf(t, T(T_P_CIBLE), param_sel == 0 ? '>' : ' ', param_cible);
    ecrire_n(0, 4, t, 40, param_sel == 0 ? JAUNE : BLANC, FOND_VERT);
    sprintf(t, T(T_P_INACTIF), param_sel == 1 ? '>' : ' ', param_inactif);
    ecrire_n(0, 6, t, 40, param_sel == 1 ? JAUNE : BLANC, FOND_VERT);
    ecrire(0, 9, T(T_P_CHOISIR), GRIS_CLAIR, FOND_VERT);
    ecrire(0, 10, T(T_P_MODIFIER), GRIS_CLAIR, FOND_VERT);
    barre(T(T_B_PARAM));
}

static void vue_fin(void)
{
    unsigned nous = scores[moi & 1], eux = scores[(moi & 1) ^ 1];
    if (sale != D_TOUT) {
        return;
    }
    titre_ecran(T_T_FIN);
    sprintf(t, "%-5s: %4u", T(T_NOUS), nous);
    ecrire(0, 4, t, BLANC, FOND_VERT);
    sprintf(t, "%-5s: %4u", T(T_EUX), eux);
    ecrire(0, 5, t, BLANC, FOND_VERT);
    if (gagnant >= 0) {
        ecrire(0, 7, T(gagnant == (moi & 1) ? T_F_VICT_NOUS : T_F_VICT_EUX), JAUNE, FOND_VERT);
    }
    ecrire(0, 11, T(T_F_NOUVELLE), BLANC, FOND_VERT);
    ecrire(0, 12, T(T_F_QUITTER), BLANC, FOND_VERT);
    barre(T(suis_chef() ? T_B_FIN_CHEF : T_B_FIN));
}

static unsigned char derniere = 0xFF;

/* Tout redessiner au prochain appel (retour de l'écran de connexion). */
void vue_forcer(void)
{
    derniere = 0xFF;
}

void dessiner(void)
{
    unsigned char v = vue_courante();

    if (v != derniere) {
        ecran_effacer();
        sale = D_TOUT;
        derniere = v;
    }
    if (!sale) {
        return;
    }
    if (v != V_TABLE) {
        glisse = -1;
        if (ramasse >= 0) {
            son_effet(FX_PLI);          /* pas d'animation hors de la table */
            ramasse = -1;
        }
    }
    switch (v) {
    case V_TABLE:  vue_table();  break;
    case V_REGLES: vue_regles(); break;
    case V_PARAM:  vue_param();  break;
    case V_FIN:    vue_fin();    break;
    }
    sale = 0;
}
