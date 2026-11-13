/* Interprétation des messages serveur -> client (SPEC 7.2). */
#include "ascii.h"
#include <string.h>
#include <stdio.h>
#include "ecran.h"
#include "jeu.h"
#include "son.h"

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
unsigned char sale;
char erreur[41];
struct entree journal[JOURNAL_N];

const unsigned char coul_place[4] = { BLANC, JAUNE, CYAN, ORANGE };
const char *const positions[4] = { "SUD", "EST", "NORD", "OUEST" };

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

static const char *const nom_rang[8] = { "7", "8", "9", "10", "V", "D", "R", "A" };

static void manche_raz(void)
{
    retournee = atout = preneur = tour = prise = -1;
    tour_ench = 1;
    pli[0] = pli[1] = pli[2] = pli[3] = -1;
    pli_fini = 0;
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
    /* 33 caractères après « NOM  : », 40 pour un message serveur */
    strncpy(e->texte, texte, 39);
    e->texte[nom[0] ? 33 : 39] = 0;
    e->coul_texte = coul_texte;
    sale |= D_JOURNAL;
}

void journal_info(const char *texte)
{
    journal_ajouter("", 0, texte, GRIS_CLAIR);
}

/* Événement d'une place : nom en couleur de place, texte blanc. */
static void journal_place(signed char p, const char *texte)
{
    if (p < 0) {
        return;
    }
    /* Les bots s'appellent tous BOT : on les désigne par leur position. */
    journal_ajouter(humain[p] ? (const char *)noms[p] : positions[REL(p)], coul_place[p], texte, BLANC);
}

static const char *equipe(int e)
{
    return (moi >= 0 && e == (moi & 1)) ? "NOUS" : "EUX";
}

static char tampon[41];

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
        son_effet(FX_PLI);
        journal_place(p, "REMPORTE LE PLI");
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
                coul = coul_place[i];
            }
        }
        journal_ajouter(reste, coul, texte, BLANC);
        son_effet(FX_TCHAT);
    } else if (!strcmp(mot, "INFO")) {
        journal_info(reste);
    } else if (!strcmp(mot, "ERR")) {
        strncpy(erreur, reste, 40);
        erreur[40] = 0;
        strcpy(tampon, "REFUS : ");
        strncat(tampon, reste, 30);
        journal_info(tampon);
    } else if (!strcmp(mot, "PASSE")) {
        journal_place(place(), "PASSE");
    } else if (!strcmp(mot, "PREND")) {
        preneur = place();
        n = nombre();
        atout = (signed char)(n & 3);
        prise = retournee;
        retournee = -1;
        /* « PREND A V♠ », et l'atout s'il est choisi au second tour :
         * « PREND A V♠ ATOUT ♥ » (le preneur ramasse toujours la retournée). */
        strcpy(tampon, "PREND A ");
        i = strlen(tampon);
        if (prise >= 0) {
            strcpy(tampon + i, nom_rang[prise & 7]);
            i = strlen(tampon);
            tampon[i++] = SYM(prise >> 3);
            if ((prise >> 3) != atout) {
                strcpy(tampon + i, " ATOUT ");
                i += 7;
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
            journal_info("SECOND TOUR D'ENCHERES");
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
        if (!strcmp(reste, "ATTENTE")) {
            etat = E_ATTENTE;
            manche_raz();
            nmain = 0;
            nbcartes[0] = nbcartes[1] = nbcartes[2] = nbcartes[3] = 0;
            gagnant = -1;
        } else if (!strcmp(reste, "LANCEE")) {
            etat = E_LANCEE;
            gagnant = -1;
            journal_info("LA PARTIE COMMENCE");
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
        n = nombre();
        i = (unsigned char)(moi & 1);
        /* MANCHE E0 E1 : on affiche NOUS puis EUX */
        if (i) {
            int e1 = nombre();
            sprintf(tampon, "MANCHE : NOUS %d  EUX %d", e1, n);
        } else {
            sprintf(tampon, "MANCHE : NOUS %d  EUX %d", n, nombre());
        }
        journal_info(tampon);
    } else if (!strcmp(mot, "CAPOT")) {
        strcpy(tampon, "CAPOT POUR ");
        strcat(tampon, equipe(nombre()));
        journal_info(tampon);
    } else if (!strcmp(mot, "LITIGE")) {
        sprintf(tampon, "LITIGE : %d POINTS EN RESERVE", nombre());
        journal_info(tampon);
    } else if (!strcmp(mot, "GAGNANT")) {
        gagnant = (signed char)nombre();
        if (gagnant >= 0 && moi >= 0) {
            son_musique(gagnant == (moi & 1) ? AIR_VICTOIRE : AIR_DEFAITE);
        }
        sale = D_TOUT;
    } else if (!strcmp(mot, "REDONNE")) {
        journal_info("TOUT LE MONDE PASSE : ON REDONNE");
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
