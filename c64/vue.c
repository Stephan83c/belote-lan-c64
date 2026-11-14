/* Dessin des écrans : table (SPEC 8.1), règles, réglages F1, fin de partie. */
#include "ascii.h"
#include <stdio.h>
#include <string.h>
#include "ecran.h"
#include "jeu.h"
#include "textes.h"
#include "ui.h"

unsigned char raz_conf, regles, param, param_sel, tchat, tchat_n;
unsigned param_cible, param_inactif;
char tchat_txt[TCHAT_MAX + 1];

static char t[41];

/* Positions par place relative : 0 SUD, 1 EST, 2 NORD, 3 OUEST */
static const unsigned char nom_x[4] = { 17, 27, 17, 1 };
static const unsigned char nom_y[4] = { 10, 5, 2, 5 };
static const unsigned char carte_x[4] = { 18, 28, 18, 4 };
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

static void barre(const char *s)
{
    ecrire_n(0, 24, s, 39, GRIS_CLAIR, FOND_VERT);   /* jamais la case 39 de L24 */
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
    }
    barre(T(s));
}

/* Titre d'un écran, aligné à droite de « BELOTE LAN C64 ». */
static void titre_ecran(unsigned char id)
{
    ecrire(0, 0, "BELOTE LAN C64", BLANC, FOND_VERT);
    ecrire(38 - strlen(T(id)), 0, T(id), BLANC, FOND_VERT);
    ligne_tirets(1);
}

static void entete(void)
{
    ecrire(0, 0, T(T_V_ATOUT), BLANC, FOND_VERT);
    if (atout >= 0) {
        t[0] = SYM(atout);
        t[1] = 0;
    } else {
        strcpy(t, "?");
    }
    ecrire_n(15, 0, t, 4, BLANC, FOND_VERT);
    sprintf(t, T(T_V_SCORES), scores[moi & 1], scores[(moi & 1) ^ 1]);
    ecrire(19, 0, t, BLANC, FOND_VERT);
}

/* Table redessinée sur place, sans effacer d'abord : chaque nom (13 cases, avec
 * « (CHEF) ») et chaque emplacement de carte est réécrit tel quel, rien ne
 * disparaît le temps du dessin (pas de clignotement). */
#define LARGEUR_NOM 13

static void zone_table(void)
{
    unsigned char y, p, r;
    const char *libelle = 0;

    if (moi < 0) {
        for (y = 2; y <= 10; ++y) {
            effacer(0, y, 40);
        }
        return;
    }
    for (p = 0; p < 4; ++p) {
        r = REL(p);
        t[0] = (etat == E_COURS && tour == (signed char)p) ? '*' : ' ';
        strcpy(t + 1, nom_place(p));
        if (humain[p]) {
            if ((etat == E_ATTENTE || etat == E_AUCUN) && chef == (signed char)p) {
                strcat(t, " (");
                strcat(t, T(T_V_CHEF));
                strcat(t, ")");
            }
        }
        ecrire_n(nom_x[r], nom_y[r], t, LARGEUR_NOM, coul_place[p], FOND_VERT);
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

/* Point k (sur GLISSE_ETAPES) entre a et b. Sans différence négative : cc65 la
 * multipliait mal par k et la carte montait en zigzag. */
static int etape(int a, int b, unsigned char k)
{
    if (b >= a) {
        return a + (unsigned)(b - a) * k / GLISSE_ETAPES;
    }
    return a - (unsigned)(a - b) * k / GLISSE_ETAPES;
}

/* La carte jouée par la place p glisse de sa main jusqu'à sa place sur le tapis :
 * depuis la main pour soi, depuis le bord de l'écran pour les autres. */
static void glisser(signed char p)
{
    unsigned char r = REL(p), i, k;
    int sx, sy, dx = 24 + carte_x[r] * 8, dy = 50 + carte_y[r] * 8;

    switch (r) {
    case 0:                                 /* soi : depuis la carte choisie */
        sx = dx;
        sy = 50 + 21 * 8;
        if (glisse_case >= 0) {
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
    for (k = 1; k <= GLISSE_ETAPES; ++k) {
        image_suivante();
        sprite_position(etape(sx, dx, k), etape(sy, dy, k));
    }
    image_suivante();
}

static void zone_journal(void)
{
    unsigned char i, y;
    struct entree *e;

    for (i = 0; i < JOURNAL_N; ++i) {
        y = 12 + i;
        e = &journal[i];
        if (e->nom[0]) {
            ecrire_n(0, y, e->nom, 5, e->coul_nom, FOND_VERT);
            ecrire(5, y, ": ", BLANC, FOND_VERT);
            ecrire_n(7, y, e->texte, 33, e->coul_texte, FOND_VERT);
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
        ecrire(5, 18, ": ", BLANC, FOND_VERT);
        ecrire(7, 18, tchat_txt, BLANC, FOND_VERT);
        curseur(7 + tchat_n, 18);
    }
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
            /* [1 PRENDRE ♠] [2 PASSE] */
            strcpy(t, "[1 ");
            strcat(t, T(T_V_PRENDRE));
            strcat(t, "  ] [2 ");
            strcat(t, T(T_V_PASSER));
            strcat(t, "]");
            t[4 + strlen(T(T_V_PRENDRE))] = SYM(retournee >> 3);
            ecrire(0, 19, t, JAUNE, FOND_VERT);
        } else {
            x = 0;
            k = 1;
            for (c = 0; c < 4; ++c) {
                if (c != (unsigned char)(retournee >> 3)) {
                    t[0] = '[';
                    t[1] = '0' + k++;
                    t[2] = ' ';
                    t[3] = SYM(c);
                    t[4] = ']';
                    t[5] = 0;
                    ecrire(x, 19, t, JAUNE, FOND_VERT);
                    x += 6;
                }
            }
            strcpy(t, "[4 ");
            strcat(t, T(T_V_PASSER));
            strcat(t, "]");
            ecrire(x, 19, t, JAUNE, FOND_VERT);
        }
        /* Le journal ne montre pas toujours les passes du 1er tour. */
        k = tour_ench == 1 ? T_V_TOUR1 : T_V_TOUR2;
        ecrire(40 - strlen(T(k)), 19, T(k), BLANC, FOND_VERT);
    } else if (etat == E_COURS && atout >= 0 && tour == moi) {
        ecrire(0, 19, T(T_V_A_VOUS), JAUNE, FOND_VERT);
    } else if (etat == E_FIN_MANCHE) {
        ecrire(0, 19, T(suis_chef() ? T_V_FIN_CHEF : T_V_FIN_AUTRE), GRIS_CLAIR, FOND_VERT);
    }
}

static void zone_main(void)
{
    unsigned char i, coul;

    /* Sur place, emplacement par emplacement (pas de clignotement). */
    coul = (etat == E_COURS && atout >= 0 && tour == moi) ? JAUNE : GRIS_FONCE;
    for (i = 0; i < 8; ++i) {
        if (i < nmain) {
            carte(i * 5, 21, main_c[i]);
            t[0] = '1' + i;
            t[1] = 0;
            ecrire(i * 5 + 1, 23, t, coul, FOND_VERT);
        } else {
            carte(i * 5, 21, -1);
            effacer(i * 5 + 1, 23, 1);
        }
    }
}

static void vue_table(void)
{
    if (sale == D_TOUT) {
        ligne_tirets(1);
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
    }
    switch (v) {
    case V_TABLE:  vue_table();  break;
    case V_REGLES: vue_regles(); break;
    case V_PARAM:  vue_param();  break;
    case V_FIN:    vue_fin();    break;
    }
    sale = 0;
}
