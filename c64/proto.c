/* Interprétation des messages serveur -> client (SPEC 7.2). */
#include "ascii.h"
#include <string.h>
#include <stdio.h>
#include <time.h>
#include "ecran.h"
#include "jeu.h"
#include "son.h"
#include "textes.h"

signed char moi = -1;
char noms[4][NOM_MAX + 1];
unsigned char humain[4];
signed char chef = -1;
unsigned char etat = E_AUCUN;
unsigned cible = 1000, inactif = 3;
unsigned scores[2];
signed char donneur = -1, tour = -1, preneur = -1, atout = -1, retournee = -1, gagnant = -1;
signed char prise = -1;
unsigned char tour_ench = 1;
signed char main_c[8];
unsigned char nmain;
unsigned char nbcartes[4];
signed char pli[4];
unsigned char pli_fini;
signed char glisse = -1;
signed char glisse_case = -1;
signed char ramasse = -1;
unsigned char suite, suite_vue, manche_nous;
static clock_t suite_fin;
unsigned char sale;
char erreur[41];
struct entree journal[JOURNAL_N];

/* Équipe P0+P2 en bleus, P1+P3 en rouges : mêmes couleurs sur tous les écrans. */
const unsigned char coul_place[4] = { BLEU_CLAIR, ROUGE_CLAIR, BLEU, ROUGE };
/* Nom d'un bot : sa place réelle, le même sur tous les écrans. */
const char *const noms_bots[4] = { "BOT1", "BOT2", "BOT3", "BOT4" };

static char *reste;   /* paramètres non encore lus de la ligne en cours */

static int nombre(void)
{
    int n = 0;
    unsigned char neg = 0;
    while (*reste == ' ') {
        ++reste;
    }
    if (*reste == '-') {
        neg = 1;
        ++reste;
    }
    while (*reste >= '0' && *reste <= '9') {
        n = n * 10 + (*reste++ - '0');
    }
    return neg ? -n : n;
}

static signed char place(void)
{
    int p = nombre();
    return (p >= 0 && p <= 3) ? (signed char)p : -1;
}

/* Secondes avant la manche suivante annoncée par SUITE, arrondies au-dessus. */
unsigned char suite_secondes(void)
{
    clock_t t = clock();
    if (t >= suite_fin) {
        return 0;
    }
    return (unsigned char)((suite_fin - t + CLOCKS_PER_SEC - 1) / CLOCKS_PER_SEC);
}

/* Rang d'une carte : 7 8 9 10, figures de la langue (V D R, J Q K...), A. */
const char *nom_rang(unsigned char r)
{
    static const char *const chiffres[4] = { "7", "8", "9", "10" };
    static char fig[2];
    if (r < 4) {
        return chiffres[r];
    }
    fig[0] = r == 7 ? 'A' : T(T_FIGURES)[r - 4];
    return fig;
}

/* Motifs des refus (ERR) : mot-clé du protocole, puis son texte. */
static const char *const codes_err[] = {
    "TROP LONG", "NOM", "CHEF SEUL", "PAS LANCEE", "INCONNU", "PAS TON TOUR",
    "COUP REFUSE", "NOM RESERVE", "TABLE PLEINE", "DEJA LANCEE", "PARAM"
};

const char *motif_refus(const char *code)
{
    unsigned char i;
    for (i = 0; i < sizeof(codes_err) / sizeof(codes_err[0]); ++i) {
        if (!strcmp(code, codes_err[i])) {
            return T(T_E_TROP_LONG + i);
        }
    }
    return code;                    /* motif inconnu (serveur plus récent) : tel quel */
}

static void manche_raz(void)
{
    retournee = atout = preneur = tour = prise = -1;
    tour_ench = 1;
    pli[0] = pli[1] = pli[2] = pli[3] = -1;
    pli_fini = 0;
    ramasse = -1;
}

void jeu_raz(void)
{
    unsigned char i;
    moi = chef = donneur = gagnant = -1;
    etat = E_AUCUN;
    cible = 1000;
    inactif = 3;
    scores[0] = scores[1] = 0;
    nmain = 0;
    for (i = 0; i < 4; ++i) {
        noms[i][0] = 0;
        humain[i] = 0;
        nbcartes[i] = 0;
    }
    for (i = 0; i < JOURNAL_N; ++i) {
        journal[i].nom[0] = 0;
        journal[i].texte[0] = 0;
    }
    erreur[0] = 0;
    manche_raz();
    sale = D_TOUT;
}

static void journal_ajouter(const char *nom, unsigned char coul_nom,
                            const char *texte, unsigned char coul_texte)
{
    struct entree *e = &journal[JOURNAL_N - 1];
    memmove(journal, journal + 1, sizeof(struct entree) * (JOURNAL_N - 1));
    strncpy(e->nom, nom, NOM_MAX);
    e->nom[NOM_MAX] = 0;
    e->coul_nom = coul_nom;
    /* 32 caractères après « NOM6  : », 40 pour un message serveur */
    strncpy(e->texte, texte, 39);
    e->texte[nom[0] ? 32 : 39] = 0;
    e->coul_texte = coul_texte;
    sale |= D_JOURNAL;
}

void journal_info(const char *texte)
{
    journal_ajouter("", 0, texte, GRIS_CLAIR);
}

/* Nom affiché d'une place : celui du joueur, ou BOT1 à BOT4 pour un bot (ils
 * s'appellent tous BOT pour le serveur), le même sur tous les écrans. */
const char *nom_place(signed char p)
{
    if (p < 0 || !noms[p][0]) {
        return "-";
    }
    if (!humain[p]) {
        return noms_bots[p];
    }
    return noms[p];
}

/* Événement d'une place : nom en couleur de place, texte blanc. */
static void journal_place(signed char p, const char *texte)
{
    if (p < 0) {
        return;
    }
    journal_ajouter(nom_place(p), COUL_PLACE(p), texte, BLANC);
}

static char tampon[41];

/* s est-il « NOM fin » ? Si oui, renvoie la longueur du nom plus l'espace, sinon 0. */
static unsigned char finit_par(const char *s, const char *fin)
{
    unsigned char ls = strlen(s), lf = strlen(fin);
    return (ls > lf && ls - lf <= NOM_MAX + 1 && !strcmp(s + ls - lf, fin) &&
            s[ls - lf - 1] == ' ') ? ls - lf : 0;
}

/* Les INFO du serveur ont un texte fixe (voir server/belote/table.py) : on
 * reconnaît chacun pour le traduire ; un INFO inconnu s'affiche tel quel. */
static void info(char *s)
{
    unsigned char n;
    unsigned pts;
    int e;

    if (!strcmp(s, "PARTIE EFFACEE")) {
        journal_info(T(T_I_EFFACEE));
    } else if (!strcmp(s, "INACTIF : PLACE RENDUE AU BOT")) {
        journal_info(T(T_I_INACTIF));
    } else if (!strncmp(s, "NOM CHANGE EN ", 14) && strlen(s + 14) <= NOM_MAX) {
        sprintf(tampon, T(T_I_NOM_CHANGE), s + 14);
        journal_info(tampon);
    } else if (!strncmp(s, "RESERVE ", 8)) {
        /* RESERVE N POUR EQUIPE E */
        reste = s + 8;
        pts = nombre();
        if (!strncmp(reste, " POUR EQUIPE ", 13)) {
            reste += 13;
            e = nombre();
            sprintf(tampon, T(moi >= 0 && e == (moi & 1) ? T_I_RESERVE_NOUS : T_I_RESERVE_EUX), pts);
            journal_info(tampon);
        } else {
            journal_info(s);
        }
    } else if ((n = finit_par(s, "RECONNECTE")) != 0) {
        s[n - 1] = 0;
        sprintf(tampon, T(T_I_RECONNECTE), s);
        journal_info(tampon);
    } else if ((n = finit_par(s, "INACTIF REMPLACE PAR UN BOT")) != 0) {
        s[n - 1] = 0;
        sprintf(tampon, T(T_I_INACTIF_BOT), s);
        journal_info(tampon);
    } else if ((n = finit_par(s, "REMPLACE PAR UN BOT")) != 0) {
        s[n - 1] = 0;
        sprintf(tampon, T(T_I_BOT), s);
        journal_info(tampon);
    } else {
        journal_info(s);
    }
}

void traiter_ligne(char *ligne)
{
    char *mot = ligne;
    signed char p;
    unsigned char i;
    int n;

    reste = strchr(ligne, ' ');
    if (reste) {
        *reste++ = 0;
    } else {
        reste = ligne + strlen(ligne);
    }

    if (!strcmp(mot, "TOUR")) {
        tour = place();
        sale |= D_TABLE | D_ENCH | D_MAIN | D_BARRE;
    } else if (!strcmp(mot, "JOUE")) {
        p = place();
        n = nombre();
        prise = -1;
        if (p >= 0) {
            if (pli_fini) {
                pli[0] = pli[1] = pli[2] = pli[3] = -1;
                pli_fini = 0;
            }
            pli[p] = (signed char)n;
            glisse = p;
            /* Sa propre carte : son emplacement dans la main, avant que MAIN
             * (qui suit aussitôt) ne la retire. */
            glisse_case = -1;
            if (p == moi) {
                for (i = 0; i < nmain; ++i) {
                    if (main_c[i] == (signed char)n) {
                        glisse_case = (signed char)i;
                    }
                }
            }
            son_effet(FX_CARTE);
            if (nbcartes[p]) {
                --nbcartes[p];
            }
        }
        sale |= D_TABLE;
    } else if (!strcmp(mot, "MAIN")) {
        nmain = 0;
        while (*reste && nmain < 8) {
            main_c[nmain++] = (signed char)nombre();
        }
        sale |= D_MAIN;
    } else if (!strcmp(mot, "PLI")) {
        p = place();
        pli_fini = 1;
        /* Le bruitage part avec les cartes, au dessin (vue.c, ramasser). */
        ramasse = p;
        sale |= D_TABLE;
        journal_place(p, T(T_J_PLI));
    } else if (!strcmp(mot, "TCHAT")) {
        /* TCHAT NOM TEXTE */
        char *texte = strchr(reste, ' ');
        unsigned char coul = BLANC;
        if (texte) {
            *texte++ = 0;
        } else {
            texte = "";
        }
        for (i = 0; i < 4; ++i) {
            if (humain[i] && !strcmp(noms[i], reste)) {
                coul = COUL_PLACE(i);
            }
        }
        journal_ajouter(reste, coul, texte, BLANC);
        son_effet(FX_TCHAT);
    } else if (!strcmp(mot, "INFO")) {
        info(reste);
    } else if (!strcmp(mot, "ERR")) {
        strncpy(erreur, reste, 40);
        erreur[40] = 0;
        strcpy(tampon, T(T_REFUS));
        strncat(tampon, motif_refus(erreur), 39 - strlen(tampon));
        journal_info(tampon);
    } else if (!strcmp(mot, "PASSE")) {
        journal_place(place(), T(T_J_PASSE));
    } else if (!strcmp(mot, "PREND")) {
        preneur = place();
        n = nombre();
        atout = (signed char)(n & 3);
        prise = retournee;
        retournee = -1;
        /* « PREND A V♠ », et l'atout s'il est choisi au second tour :
         * « PREND A V♠ ATOUT ♥ » (le preneur ramasse toujours la retournée). */
        strcpy(tampon, T(T_J_PREND));
        i = strlen(tampon);
        if (prise >= 0) {
            strcpy(tampon + i, nom_rang(prise & 7));
            i = strlen(tampon);
            tampon[i++] = SYM(prise >> 3);
            if ((prise >> 3) != atout) {
                strcpy(tampon + i, T(T_J_ATOUT));
                i = strlen(tampon);
                tampon[i++] = SYM(atout);
            }
        } else {
            tampon[i++] = SYM(atout);
        }
        tampon[i] = 0;
        journal_place(preneur, tampon);
        sale |= D_ENTETE | D_TABLE | D_ENCH | D_MAIN | D_BARRE;
    } else if (!strcmp(mot, "RETOURNE")) {
        retournee = (signed char)nombre();
        sale |= D_TABLE | D_ENCH;
    } else if (!strcmp(mot, "ENCHERES")) {
        tour_ench = (unsigned char)nombre();
        if (tour_ench == 2) {
            journal_info(T(T_J_SECOND));
        }
        sale |= D_ENCH;
    } else if (!strcmp(mot, "NBCARTES")) {
        for (i = 0; i < 4; ++i) {
            nbcartes[i] = (unsigned char)nombre();
        }
        sale |= D_TABLE;
    } else if (!strcmp(mot, "BELOTE")) {
        journal_place(place(), "BELOTE");
    } else if (!strcmp(mot, "REBELOTE")) {
        journal_place(place(), "REBELOTE");
    } else if (!strcmp(mot, "PLICOURS")) {
        for (i = 0; i < 4; ++i) {
            pli[i] = (signed char)nombre();
        }
        pli_fini = 0;
        prise = -1;
        sale |= D_TABLE;
    } else if (!strcmp(mot, "SIEGE")) {
        /* SIEGE P T NOM */
        p = place();
        while (*reste == ' ') {
            ++reste;
        }
        if (p >= 0) {
            humain[p] = *reste == 'H';
            strncpy(noms[p], reste + 2, NOM_MAX);
            noms[p][NOM_MAX] = 0;
        }
        sale |= D_TABLE | D_ENCH;
    } else if (!strcmp(mot, "CHEF")) {
        n = nombre();
        chef = (n >= 0 && n <= 3) ? (signed char)n : -1;
        sale |= D_TABLE | D_ENCH | D_BARRE;
    } else if (!strcmp(mot, "ETAT")) {
        suite = 0;
        if (!strcmp(reste, "ATTENTE")) {
            etat = E_ATTENTE;
            manche_raz();
            nmain = 0;
            nbcartes[0] = nbcartes[1] = nbcartes[2] = nbcartes[3] = 0;
            gagnant = -1;
        } else if (!strcmp(reste, "LANCEE")) {
            etat = E_LANCEE;
            gagnant = -1;
            journal_info(T(T_J_COMMENCE));
        } else if (!strcmp(reste, "EN COURS")) {
            etat = E_COURS;
            manche_raz();
        } else if (!strcmp(reste, "FIN MANCHE")) {
            etat = E_FIN_MANCHE;
            tour = -1;
        } else if (!strcmp(reste, "FIN PARTIE")) {
            etat = E_FIN_PARTIE;
            tour = -1;
        }
        sale = D_TOUT;
    } else if (!strcmp(mot, "PARAM")) {
        if (!strncmp(reste, "CIBLE ", 6)) {
            reste += 6;
            cible = nombre();
        } else if (!strncmp(reste, "INACTIF ", 8)) {
            reste += 8;
            inactif = nombre();
        }
        sale |= D_ENCH;
    } else if (!strcmp(mot, "SCORE")) {
        scores[0] = nombre();
        scores[1] = nombre();
        sale |= D_ENTETE;
    } else if (!strcmp(mot, "DONNEUR")) {
        donneur = place();
        sale |= D_TABLE;
    } else if (!strcmp(mot, "MANCHE")) {
        /* MANCHE E0 E1 : on affiche NOUS puis EUX */
        {
            int e0 = nombre(), e1 = nombre(), nous = e0, eux = e1;
            if (moi & 1) {
                nous = e1;
                eux = e0;
            }
            manche_nous = nous > eux;
            sprintf(tampon, T(T_J_MANCHE), nous, eux);
        }
        journal_info(tampon);
    } else if (!strcmp(mot, "CAPOT")) {
        n = nombre();
        journal_info(T(moi >= 0 && n == (moi & 1) ? T_J_CAPOT_NOUS : T_J_CAPOT_EUX));
    } else if (!strcmp(mot, "LITIGE")) {
        sprintf(tampon, T(T_J_LITIGE), nombre());
        journal_info(tampon);
    } else if (!strcmp(mot, "GAGNANT")) {
        gagnant = (signed char)nombre();
        if (gagnant >= 0 && moi >= 0) {
            son_musique(gagnant == (moi & 1) ? AIR_VICTOIRE : AIR_DEFAITE);
        }
        sale = D_TOUT;
    } else if (!strcmp(mot, "SUITE")) {
        /* SUITE S : la manche suivante démarre seule dans S secondes. */
        n = nombre();
        if (n > 0) {
            suite_fin = clock() + (clock_t)n * CLOCKS_PER_SEC;
            suite = 1;
            suite_vue = 0xFF;
            sale |= D_ENCH | D_BARRE;
        }
    } else if (!strcmp(mot, "REDONNE")) {
        journal_info(T(T_J_REDONNE));
    } else if (!strcmp(mot, "BIENVENUE")) {
        /* BIENVENUE NOM P */
        char *esp = strchr(reste, ' ');
        if (esp) {
            reste = esp + 1;
            moi = place();
        }
        sale = D_TOUT;
    }
}
