/* Dessin des écrans : table (SPEC 8.1), règles, réglages F1, fin de partie. */
#include "ascii.h"
#include <stdio.h>
#include <string.h>
#include "ecran.h"
#include "jeu.h"
#include "ui.h"

unsigned char regles, param, param_sel, tchat, tchat_n;
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
    const char *s = "F3 TCHAT F7 QUIT F8 AIDE";
    if (tchat) {
        s = "RETURN ENVOYER  DEL EFFACER  F3 ANNULER";
    } else if (etat == E_ATTENTE || etat == E_AUCUN) {
        if (suis_chef()) {
            s = "F1 PARAM F2 GO F3 TCHAT F7 QUIT F8 AIDE";
        }
    } else if (etat == E_COURS && tour == moi) {
        s = atout < 0 ? "1-4 CHOIX F3 TCHAT F7 QUIT F8 AIDE"
                      : "1-8 CARTE F3 TCHAT F7 QUIT F8 AIDE";
    } else if (etat == E_FIN_MANCHE && suis_chef()) {
        s = "F3 TCHAT F5 SUITE F7 QUIT F8 AIDE";
    }
    barre(s);
}

static void entete(void)
{
    ecrire(0, 0, "BELOTE   ATOUT:", BLANC, FOND_VERT);
    if (atout >= 0) {
        t[0] = SYM(atout);
        t[1] = 0;
    } else {
        strcpy(t, "?");
    }
    ecrire_n(15, 0, t, 4, BLANC, FOND_VERT);
    sprintf(t, "NOUS:%04u   EUX:%04u", scores[moi & 1], scores[(moi & 1) ^ 1]);
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
        strcpy(t + 1, noms[p][0] ? noms[p] : "-");
        if (etat == E_ATTENTE || etat == E_AUCUN) {
            if (chef == (signed char)p) {
                strcat(t, " (CHEF)");
            }
        } else if (r != 0) {
            sprintf(t + strlen(t), " (%u)", nbcartes[p]);
        }
        ecrire(nom_x[r], nom_y[r], t, coul_place[p], FOND_VERT);
        carte(carte_x[r], carte_y[r], pli[p]);
    }
    if (etat == E_COURS && retournee >= 0) {
        ecrire(15, 5, "RETOURNEE", GRIS_CLAIR, FOND_VERT);
        carte(18, 6, retournee);
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
        ecrire(0, 18, "VOUS : ", BLANC, FOND_VERT);
        ecrire(7, 18, tchat_txt, BLANC, FOND_VERT);
        curseur(7 + tchat_n, 18);
    }
}

static void zone_encheres(void)
{
    unsigned char c, k, x;

    effacer(0, 19, 40);
    if (etat == E_ATTENTE) {
        sprintf(t, "CHEF : %s   CIBLE : %u POINTS", chef >= 0 ? noms[chef] : "-", cible);
        ecrire(0, 19, t, GRIS_CLAIR, FOND_VERT);
    } else if (etat == E_COURS && atout < 0 && retournee >= 0) {
        if (tour != moi) {
            sprintf(t, "ENCHERES : AU TOUR DE %s...", tour >= 0 ? noms[tour] : "-");
            ecrire(0, 19, t, GRIS_CLAIR, FOND_VERT);
        } else if (tour_ench == 1) {
            strcpy(t, "[1 PRENDRE  ] [2 PASSE]");
            t[11] = SYM(retournee >> 3);
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
            ecrire(x, 19, "[4 PASSE]", JAUNE, FOND_VERT);
        }
    } else if (etat == E_COURS && atout >= 0 && tour == moi) {
        ecrire(0, 19, "A VOUS DE JOUER : 1-8", JAUNE, FOND_VERT);
    } else if (etat == E_FIN_MANCHE) {
        ecrire(0, 19, suis_chef() ? "MANCHE TERMINEE : F5 POUR LA SUIVANTE"
                                  : "MANCHE TERMINEE : ON ATTEND LE CHEF",
               GRIS_CLAIR, FOND_VERT);
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

static const char *const texte_regles[] = {
    "32 CARTES. VOUS ET NORD CONTRE EST ET",
    "OUEST. ON JOUE VERS LA DROITE.",
    "ENCHERES, TOUR 1 : PRENDRE A LA COULEUR",
    "RETOURNEE (1) OU PASSER (2). TOUR 2 :",
    "UNE AUTRE COULEUR (1-3) OU PASSER (4).",
    "",
    "FOURNIR LA COULEUR DEMANDEE. A L'ATOUT,",
    "MONTER SI POSSIBLE. SANS LA COULEUR :",
    "COUPER SI L'ADVERSAIRE EST MAITRE, ET",
    "SURCOUPER SI POSSIBLE. PARTENAIRE",
    "MAITRE : JEU LIBRE.",
    "",
    "ATOUT : V 20, 9 14, A 11, 10 10, R 4,",
    "D 3. HORS ATOUT : A 11, 10 10, R 4,",
    "D 3, V 2. DIX DE DER 10, BELOTE 20.",
    "",
    "LE PRENEUR DOIT FAIRE PLUS QUE LA",
    "DEFENSE, SINON IL EST DEDANS : 162 A",
    "LA DEFENSE. CAPOT : 252.",
};

static void vue_regles(void)
{
    unsigned char i;
    if (sale != D_TOUT) {
        return;
    }
    ecrire(0, 0, "BELOTE LAN C64          REGLES DU JEU", BLANC, FOND_VERT);
    ligne_tirets(1);
    for (i = 0; i < sizeof(texte_regles) / sizeof(texte_regles[0]); ++i) {
        ecrire(0, 3 + i, texte_regles[i], BLANC, FOND_VERT);
    }
    barre("F8 RETOUR AU JEU");
}

static void vue_param(void)
{
    ecrire(0, 0, "BELOTE LAN C64             PARAMETRES", BLANC, FOND_VERT);
    ligne_tirets(1);
    sprintf(t, "%c SCORE CIBLE : %u", param_sel == 0 ? '>' : ' ', param_cible);
    ecrire_n(0, 4, t, 40, param_sel == 0 ? JAUNE : BLANC, FOND_VERT);
    sprintf(t, "%c INACTIVITE  : %u MIN", param_sel == 1 ? '>' : ' ', param_inactif);
    ecrire_n(0, 6, t, 40, param_sel == 1 ? JAUNE : BLANC, FOND_VERT);
    ecrire(0, 9, "CRSR HAUT/BAS : CHOISIR", GRIS_CLAIR, FOND_VERT);
    ecrire(0, 10, "+ / -         : MODIFIER", GRIS_CLAIR, FOND_VERT);
    barre("RETURN VALIDER  F1 ANNULER");
}

static void vue_fin(void)
{
    unsigned nous = scores[moi & 1], eux = scores[(moi & 1) ^ 1];
    if (sale != D_TOUT) {
        return;
    }
    ecrire(0, 0, "BELOTE LAN C64         PARTIE TERMINEE", BLANC, FOND_VERT);
    ligne_tirets(1);
    sprintf(t, "NOUS : %4u", nous);
    ecrire(0, 4, t, BLANC, FOND_VERT);
    sprintf(t, "EUX  : %4u", eux);
    ecrire(0, 5, t, BLANC, FOND_VERT);
    if (gagnant >= 0) {
        ecrire(0, 7, gagnant == (moi & 1) ? "VICTOIRE DE NOUS !" : "VICTOIRE DE EUX !",
               JAUNE, FOND_VERT);
    }
    ecrire(0, 11, "F5 = NOUVELLE PARTIE   (CHEF SEULEMENT)", BLANC, FOND_VERT);
    ecrire(0, 12, "F7 = QUITTER", BLANC, FOND_VERT);
    barre(suis_chef() ? "F5 NOUVELLE PARTIE F7 QUIT" : "F7 QUIT");
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
