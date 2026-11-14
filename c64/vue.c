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

static void zone_table(void)
{
    unsigned char y, p, r;

    for (y = 2; y <= 10; ++y) {
        effacer(0, y, 40);
    }
    if (moi < 0) {
        return;
    }
    for (p = 0; p < 4; ++p) {
        r = REL(p);
        t[0] = (etat == E_COURS && tour == (signed char)p) ? '*' : ' ';
        /* Les bots s'appellent tous BOT : on les nomme par leur place,
         * comme dans le journal, pareil sur tous les écrans. */
        if (!humain[p] && noms[p][0]) {
            strcpy(t + 1, noms_bots[p]);
        } else {
            strcpy(t + 1, noms[p][0] ? noms[p] : "-");
            if ((etat == E_ATTENTE || etat == E_AUCUN) && chef == (signed char)p) {
                strcat(t, " (");
                strcat(t, T(T_V_CHEF));
                strcat(t, ")");
            }
        }
        ecrire(nom_x[r], nom_y[r], t, coul_place[p], FOND_VERT);
        carte(carte_x[r], carte_y[r], pli[p]);
    }
    if (etat == E_COURS && retournee >= 0) {
        ecrire(20 - (strlen(T(T_V_RETOURNEE)) + 1) / 2, 5, T(T_V_RETOURNEE), GRIS_CLAIR, FOND_VERT);
        carte(18, 6, retournee);
    } else if (etat == E_COURS && prise >= 0) {
        ecrire(20 - (strlen(T(T_V_PRISE)) + 1) / 2, 5, T(T_V_PRISE), GRIS_CLAIR, FOND_VERT);
        carte(18, 6, prise);
    }
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
        sprintf(t, T(T_V_ATTENTE), chef >= 0 ? noms[chef] : "-", cible);
        ecrire(0, 19, t, GRIS_CLAIR, FOND_VERT);
    } else if (etat == E_COURS && atout < 0 && retournee >= 0) {
        if (tour != moi) {
            sprintf(t, T(T_V_AU_TOUR), tour >= 0 ? noms[tour] : "-");
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

    for (i = 21; i <= 23; ++i) {
        effacer(0, i, 40);
    }
    coul = (etat == E_COURS && atout >= 0 && tour == moi) ? JAUNE : GRIS_FONCE;
    for (i = 0; i < nmain; ++i) {
        carte(i * 5, 21, main_c[i]);
        t[0] = '1' + i;
        t[1] = 0;
        ecrire(i * 5 + 1, 23, t, coul, FOND_VERT);
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
        zone_table();
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
    switch (v) {
    case V_TABLE:  vue_table();  break;
    case V_REGLES: vue_regles(); break;
    case V_PARAM:  vue_param();  break;
    case V_FIN:    vue_fin();    break;
    }
    sale = 0;
}
