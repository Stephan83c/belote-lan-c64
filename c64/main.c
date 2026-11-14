/* Belote LAN pour C64 Ultimate : connexion, boucle clavier/réseau, touches. */
#include "ascii.h"
#include <cbm.h>
#include <stdlib.h>
#include <string.h>
#include "ecran.h"
#include "jeu.h"
#include "son.h"
#include "textes.h"
#include "uci.h"
#include "ui.h"

#ifndef SERVEUR_DEFAUT
#define SERVEUR_DEFAUT "192.168.1.55:6464"
#endif
#ifndef VERSION
#define VERSION "?"
#endif
#define PORT_DEFAUT 6464
#define SERVEUR_MAX 31

#define K_RETURN 13
#define K_DEL    20
#define K_HAUT   145
#define K_BAS    17
#define K_F1     133
#define K_F3     134
#define K_F5     135
#define K_F7     136
#define K_F2     137
#define K_F4     138
#define K_F8     140

#define PEEK(a) (*(volatile unsigned char *)(a))

static char serveur[SERVEUR_MAX + 1];
static char nom[NOM_MAX + 1];
static char hote[SERVEUR_MAX + 1];
static int sock = -1;
static unsigned char perdu;          /* écriture refusée : connexion perdue */

static char ligne[65];
static unsigned char lg, deborde;
static char rx[64];
static char tx[66];

/* Horloge du KERNAL (60 Hz), 16 bits de poids faible. */
static unsigned jiffies(void)
{
    unsigned char b, h;
    do {
        b = PEEK(0xA2);
        h = PEEK(0xA1);
    } while (b != PEEK(0xA2));
    return (h << 8) | b;
}

static void envoyer(const char *s)
{
    unsigned char n = strlen(s);
    if (sock < 0 || n > 63) {
        return;
    }
    memcpy(tx, s, n);
    tx[n] = LF;
    if (!net_ecrire(sock, tx, n + 1)) {
        perdu = 1;
    }
}

/* Lit ce qui est arrivé et traite chaque ligne complète. */
static void reseau(void)
{
    unsigned char i, c, tours;
    int n;

    if (sock < 0) {
        return;
    }
    for (tours = 0; tours < 4; ++tours) {
        n = net_lire(sock, rx, sizeof(rx));
        if (n < 0) {
            /* L'Ultimate a déjà libéré ce socket et peut réutiliser son numéro
             * pour lui-même : ne plus jamais l'écrire ni le fermer. */
            sock = -1;
            perdu = 1;
            return;
        }
        if (!n) {
            return;
        }
        for (i = 0; i < n; ++i) {
            c = rx[i];
            if (c == LF) {
                if (!deborde) {
                    ligne[lg] = 0;
                    traiter_ligne(ligne);
                }
                lg = 0;
                deborde = 0;
            } else if (c != 13) {
                if (lg < 64) {
                    ligne[lg++] = c;
                } else {
                    deborde = 1;
                }
            }
        }
    }
}

/* ---- Écran de connexion (SPEC 2.1) ------------------------------------ */

static unsigned char accepte(unsigned char c, unsigned char hote_permis)
{
    if ((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')) {
        return 1;
    }
    return hote_permis && (c == '.' || c == '-' || c == ':');
}

/* Saisie bloquante d'un champ ; renvoie la touche qui la termine. */
static unsigned char saisir(unsigned char y, char *buf, unsigned char max, unsigned char hote_permis)
{
    unsigned char n = strlen(buf), c;
    for (;;) {
        ecrire_n(9, y, buf, 40 - 9, BLANC, FOND_VERT);
        if (n < max) {
            curseur(9 + n, y);
        }
        while (!(c = cbm_k_getin())) {
        }
        if (c == K_RETURN || c == K_HAUT || c == K_BAS || c == K_F1) {
            ecrire_n(9, y, buf, 40 - 9, BLANC, FOND_VERT);
            return c;
        }
        if (c == K_DEL) {
            if (n) {
                buf[--n] = 0;
            }
        } else if (n < max && accepte(c, hote_permis)) {
            buf[n++] = c;
            buf[n] = 0;
        }
    }
}

#define Y_MESSAGE 7

static void message(const char *s)
{
    ecrire_n(0, Y_MESSAGE, s, 40, JAUNE, FOND_VERT);
}

/* BOT, BOT1... : noms donnés aux bots, refusés aux joueurs (le serveur aussi). */
static unsigned char nom_de_bot(const char *s)
{
    if (strncmp(s, "BOT", 3)) {
        return 0;
    }
    for (s += 3; *s; ++s) {
        if (*s < '0' || *s > '9') {
            return 0;
        }
    }
    return 1;
}

/* Message de refus du serveur (ERR ...) en clair ; renvoie le champ à corriger. */
static unsigned char refus(void)
{
    if (!strcmp(erreur, "TABLE PLEINE")) {
        message(T(T_M_PLEINE));
        return 0;
    }
    if (!strcmp(erreur, "NOM RESERVE")) {
        message(T(T_M_NOM_BOT));
        return 1;
    }
    if (!strcmp(erreur, "NOM")) {
        message(T(T_M_NOM_REFUSE));
        return 1;
    }
    strcpy(tx, T(T_REFUS));
    strncat(tx, motif_refus(erreur), 40 - strlen(tx));
    message(tx);
    return 0;
}

static void ferme(void)
{
    if (sock >= 0) {
        net_fermer(sock);
        sock = -1;
    }
}

/* Libellés de l'écran de connexion dans la langue choisie ; en bas, les
 * langues dans la leur, celle en cours en jaune (F1 passe à la suivante), et la
 * barre de touches comme en jeu. */
static void textes_connexion(void)
{
    unsigned char i, x = 0;
    const char *s = T(T_C_INFO);

    ecrire_n(0, 3, T(T_C_SERVEUR), 8, BLANC, FOND_VERT);
    ecrire(8, 3, ":", BLANC, FOND_VERT);
    ecrire_n(0, 5, T(T_C_NOM), 8, BLANC, FOND_VERT);
    ecrire(8, 5, ":", BLANC, FOND_VERT);
    effacer(0, 16, 40);
    ecrire((40 - strlen(s)) / 2, 16, s, GRIS_CLAIR, FOND_VERT);
    for (i = 0; i < NB_LANGUES; ++i) {
        ecrire(x, 22, textes[i][T_LANGUE], i == langue ? JAUNE : GRIS_FONCE, FOND_VERT);
        x += strlen(textes[i][T_LANGUE]) + 2;
    }
    ecrire_n(0, 24, T(T_B_CONNEXION), 39, GRIS_CLAIR, FOND_VERT);
}

/* L'éventail de l'écran titre en cartes de la table : valet de trèfle, as de
 * pique, puis la belote (dame et roi de coeur), les cartes du bord plus bas. */
static const signed char eventail[4] = { 2 * 8 + 4, 0 * 8 + 7, 1 * 8 + 5, 1 * 8 + 6 };

static void cartes_connexion(unsigned char animer)
{
    unsigned char i, x, y;

    for (i = 0; i < 4; ++i) {
        x = 10 + i * 5;
        y = (i == 0 || i == 3) ? 12 : 11;
        if (animer) {
            donner(eventail[i], 24 + 18 * 8, 20, x, y);   /* depuis le haut, comme une donne */
        } else {
            carte(x, y, eventail[i]);
        }
    }
}

/* Revient quand le serveur a confirmé la place par BIENVENUE. */
static void connexion(void)
{
    unsigned char champ = 0, k;
    unsigned port, debut;
    char *dp;
    static unsigned char deja;      /* donne déjà animée */

    ecran_effacer();
    ecrire(0, 0, "BELOTE LAN C64", BLANC, FOND_VERT);
    ecrire(39 - sizeof(VERSION), 0, "V" VERSION, GRIS_CLAIR, FOND_VERT);   /* jusqu'à la case 38 */
    ligne_tirets(1);
    ligne_tirets(20);
    textes_connexion();
    ecrire_n(9, 3, serveur, 31, BLANC, FOND_VERT);
    ecrire_n(9, 5, nom, 31, BLANC, FOND_VERT);
    /* Serveur déjà rempli (le cas courant) : le curseur commence sur le nom. */
    champ = serveur[0] ? 1 : 0;
    /* La donne animée une fois, en arrivant de l'écran titre. */
    cartes_connexion(!deja);
    deja = 1;
    if (perdu) {
        message(T(T_M_PERDUE));
        perdu = 0;
    }

    for (;;) {
        k = champ == 0 ? saisir(3, serveur, SERVEUR_MAX, 1) : saisir(5, nom, NOM_MAX, 0);
        if (k == K_F1) {
            langue_choisir(langue + 1);
            textes_connexion();
            cartes_connexion(0);            /* figures de la nouvelle langue */
            effacer(0, Y_MESSAGE, 40);
            continue;
        }
        if (k == K_HAUT || k == K_BAS || (k == K_RETURN && champ == 0)) {
            champ ^= 1;
            continue;
        }
        if (!nom[0]) {
            message(T(T_M_ENTREZ_NOM));
            continue;
        }
        if (nom_de_bot(nom)) {
            message(T(T_M_NOM_BOT));
            champ = 1;
            continue;
        }
        if (!serveur[0]) {
            champ = 0;
            continue;
        }
        if (!uci_present()) {
            message(T(T_M_UCI));
            continue;
        }

        strcpy(hote, serveur);
        port = PORT_DEFAUT;
        dp = strchr(hote, ':');
        if (dp) {
            *dp = 0;
            port = atoi(dp + 1);
            if (!port) {
                port = PORT_DEFAUT;
            }
        }
        message(T(T_M_CONNEXION));
        sock = net_ouvrir(hote, port);
        if (uci_bloquee) {
            message(T(T_M_BLOQUE));
            uci_bloquee = 0;
            sock = -1;
            continue;
        }
        if (sock < 0) {
            message(T(T_M_IMPOSSIBLE));
            champ = 0;
            continue;
        }

        jeu_raz();
        lg = deborde = 0;
        strcpy(tx, "JOIN ");
        strcat(tx, nom);
        envoyer(tx);
        debut = jiffies();
        perdu = 0;
        while (moi < 0 && !erreur[0] && !perdu && jiffies() - debut < 5 * 60) {
            reseau();
        }
        if (moi >= 0) {
            return;
        }
        champ = 0;
        if (erreur[0]) {
            champ = refus();
        } else if (perdu) {
            message(T(T_M_FERMEE));
        } else {
            message(T(T_M_MUET));
        }
        perdu = 0;
        ferme();
    }
}

/* ---- Partie ----------------------------------------------------------- */

static unsigned char suis_chef(void)
{
    return chef == moi;
}

static void envoyer_nombre(const char *mot, unsigned n)
{
    char tmp[8];
    strcpy(tx, mot);
    utoa(n, tmp, 10);
    strcat(tx, tmp);
    envoyer(tx);
}

static void touche_param(unsigned char c)
{
    if (c == K_HAUT || c == K_BAS) {
        param_sel ^= 1;
    } else if (c == '+') {
        if (param_sel == 0 && param_cible < 5000) {
            param_cible += 100;
        } else if (param_sel == 1 && param_inactif < 10) {
            ++param_inactif;
        }
    } else if (c == '-') {
        if (param_sel == 0 && param_cible > 500) {
            param_cible -= 100;
        } else if (param_sel == 1 && param_inactif > 1) {
            --param_inactif;
        }
    } else if (c == K_RETURN) {
        if (param_cible != cible) {
            envoyer_nombre("PARAM CIBLE ", param_cible);
        }
        if (param_inactif != inactif) {
            envoyer_nombre("PARAM INACTIF ", param_inactif);
        }
        param = 0;
    } else if (c == K_F1) {
        param = 0;
    }
    sale = D_TOUT;
}

static void touche_tchat(unsigned char c)
{
    if (c == K_RETURN) {
        if (tchat_n) {
            strcpy(tx, "TCHAT ");
            strcat(tx, tchat_txt);
            envoyer(tx);
        }
        tchat = 0;
        sale |= D_BARRE;
    } else if (c == K_F3) {
        tchat = 0;
        sale |= D_BARRE;
    } else if (c == K_DEL) {
        if (tchat_n) {
            tchat_txt[--tchat_n] = 0;
        }
    } else if (tchat_n < TCHAT_MAX &&
               ((c >= 32 && c < 64 && c != '#') || (c >= 'A' && c <= '[') || c == ']')) {
        tchat_txt[tchat_n++] = c;
        tchat_txt[tchat_n] = 0;
    }
    sale |= D_SAISIE;
}

/* Touches 1-4 pendant les enchères. */
static void enchere(unsigned char k)
{
    unsigned char c, couleur = retournee >> 3;
    if (tour_ench == 1) {
        if (k == 1) {
            envoyer_nombre("ENCH ", couleur);
        } else if (k == 2) {
            envoyer("PASSE");
        }
        return;
    }
    if (k == 4) {
        envoyer("PASSE");
        return;
    }
    for (c = 0; c < 4; ++c) {
        if (c != couleur && --k == 0) {
            envoyer_nombre("ENCH ", c);
            return;
        }
    }
}

/* Renvoie 0 si le joueur quitte la table. */
static unsigned char touche(void)
{
    unsigned char c = cbm_k_getin();
    unsigned char v;

    if (!c) {
        return 1;
    }
    if (c == K_F7) {                /* quitter, quel que soit l'écran */
        envoyer("LEAVE");
        ferme();
        return 0;
    }
    if (raz_conf) {                 /* F4 : O (Y, J, S) confirme, toute autre touche annule */
        if (c == T(T_TOUCHE_OUI)[0]) {
            envoyer("RAZ");
        }
        raz_conf = 0;
        sale |= D_BARRE;
        return 1;
    }
    if (param) {
        touche_param(c);
        return 1;
    }
    if (c == K_F8) {
        regles ^= 1;
        return 1;
    }
    if (regles) {
        return 1;
    }
    v = vue_courante();
    if (tchat && v == V_TABLE) {
        touche_tchat(c);
        return 1;
    }
    switch (c) {
    case K_F1:
        if (suis_chef() && etat == E_ATTENTE) {
            param = 1;
            param_sel = 0;
            param_cible = cible;
            param_inactif = inactif;
        }
        break;
    case K_F2:
        if (suis_chef() && etat == E_ATTENTE) {
            envoyer("LANCER");
        }
        break;
    case K_F3:
        if (v == V_TABLE) {
            tchat = 1;
            tchat_n = 0;
            tchat_txt[0] = 0;
            sale |= D_SAISIE | D_BARRE;
        }
        break;
    case K_F4:
        if (suis_chef() && v == V_TABLE && etat != E_ATTENTE && etat != E_AUCUN) {
            raz_conf = 1;
            tchat = 0;
            sale |= D_BARRE | D_SAISIE;
        }
        break;
    case K_F5:
        /* Fin de manche : tout joueur écourte la pause (serveur qui envoie SUITE) ;
         * nouvelle partie : le chef seulement. */
        if ((etat == E_FIN_MANCHE && (suite || suis_chef()))
            || (etat == E_FIN_PARTIE && suis_chef())) {
            envoyer("REJOUER");
        }
        break;
    default:
        if (etat != E_COURS || tour != moi || c < '1' || c > '8') {
            break;
        }
        c -= '0';
        if (atout < 0) {
            if (retournee >= 0 && c <= 4) {
                enchere(c);
            }
        } else if (c <= nmain) {
            envoyer_nombre("COUP ", main_c[c - 1]);
        }
    }
    return 1;
}

/* Dernier pli : une seule carte possible, le C64 la joue seul après une
 * demi-seconde (le temps de voir que c'est à soi). Une fois par carte. */
static void derniere_carte(void)
{
    static signed char jouee = -1;
    static unsigned depuis;

    if (etat != E_COURS || atout < 0 || tour != moi || nmain != 1) {
        jouee = -1;
        depuis = jiffies();
        return;
    }
    if (jouee != main_c[0] && jiffies() - depuis >= 30) {
        jouee = main_c[0];
        envoyer_nombre("COUP ", jouee);
    }
}

static void partie(void)
{
    regles = param = tchat = raz_conf = 0;
    vue_forcer();
    for (;;) {
        reseau();
        derniere_carte();
        if (uci_bloquee) {
            uci_bloquee = 0;
            perdu = 1;
        }
        if (!touche() || perdu) {
            break;
        }
        /* Les réglages se ferment si la table n'est plus en attente ou change de chef. */
        if (param && (etat != E_ATTENTE || chef != moi)) {
            param = 0;
        }
        if (raz_conf && (etat == E_ATTENTE || chef != moi)) {
            raz_conf = 0;
            sale |= D_BARRE;
        }
        /* Compte à rebours de fin de manche, une fois par seconde. */
        if (suite && etat == E_FIN_MANCHE && suite_secondes() != suite_vue) {
            sale |= D_ENCH;
        }
        dessiner();
    }
    ferme();
}

int main(void)
{
    langue_choisir(langue);
    ecran_init();
    son_init();
    titre();
    strcpy(serveur, SERVEUR_DEFAUT);
    for (;;) {
        connexion();
        partie();
    }
    return 0;
}
