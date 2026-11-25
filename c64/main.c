/* Belote LAN pour C64 Ultimate : connexion, boucle clavier/réseau, touches. */
#include "ascii.h"
#include <cbm.h>
#include <joystick.h>
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
#define IP_MAX 29               /* hôte ou IP, colonnes 10 à 38 (curseur en 39) */
#define PORT_MAX 5
#define CHAMP_X 10              /* champs IP et PORT (libellés en 1, « : » en 9) */

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
#define K_ESPACE 32
#define K_GAUCHE 157
#define K_DROITE 29
#define K_LANGUE_PREC 0xFE          /* joystick à gauche à la connexion (aucune touche) */

#define PEEK(a) (*(volatile unsigned char *)(a))

static char nom[NOM_MAX + 1];
static char hote[IP_MAX + 1];
static char port_txt[PORT_MAX + 1];
/* Écran de connexion : 0 le nom (centré), 1 l'IP, 2 le port (réglage du serveur, F3). */
static unsigned char reglage;
static unsigned char nom_cx;         /* colonne du champ NOM */
static int sock = -1;
static unsigned char perdu;          /* écriture refusée : connexion perdue */

static char ligne[65];
static unsigned char lg, deborde;
static char rx[64];
static char tx[66];

unsigned char sel, ench_sel;        /* carte et enchère choisies (joystick, curseur) */
static unsigned char joy_avant, ench_tour, ench_mien;

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

/* mode : 0 nom (lettres, chiffres), 1 hôte (et . -), 2 port (chiffres). */
static unsigned char accepte(unsigned char c, unsigned char mode)
{
    if (c >= '0' && c <= '9') {
        return 1;
    }
    if (mode == 2) {
        return 0;
    }
    return (c >= 'A' && c <= 'Z') || (mode && (c == '.' || c == '-'));
}

/* Attend une touche de l'écran de connexion ou des salons. Joystick (sur front) :
 * bouton = RETURN, haut/bas, droite/gauche = langue suivante/précédente. Surveille
 * aussi le réseau : une connexion coupée pendant le choix du salon rend F7. */
static unsigned char touche_connexion(void)
{
    unsigned char c, j, nv;

    /* Sortir dès qu'une action est reconnue : avant la v2.1, la boucle rappelait
     * cbm_k_getin() et écrasait la touche du joystick (bogue présent depuis la v1.7). */
    for (;;) {
        if ((c = cbm_k_getin()) != 0) {
            return c;
        }
        reseau();
        if (perdu) {
            return K_F7;
        }
        j = joy_read(JOY_2);
        nv = j & ~joy_avant;
        joy_avant = j;
        if (JOY_BTN_1(nv)) {
            return K_RETURN;
        } else if (JOY_RIGHT(nv)) {
            return K_F1;
        } else if (JOY_LEFT(nv)) {
            return K_LANGUE_PREC;
        } else if (JOY_UP(nv)) {
            return K_HAUT;
        } else if (JOY_DOWN(nv)) {
            return K_BAS;
        }
    }
}

/* Saisie bloquante d'un champ ; renvoie la touche qui la termine. */
static unsigned char saisir(unsigned char x, unsigned char y, char *buf, unsigned char max,
                            unsigned char mode)
{
    unsigned char n = strlen(buf), c;
    for (;;) {
        ecrire_n(x, y, buf, max + 1, BLANC, FOND_VERT);
        if (n < max) {
            curseur(x + n, y);
        }
        c = touche_connexion();
        if (c == K_RETURN || c == K_HAUT || c == K_BAS || c == K_F1 || c == K_F3
            || c == K_LANGUE_PREC) {
            ecrire_n(x, y, buf, max + 1, BLANC, FOND_VERT);
            return c;
        }
        if (c == K_DEL) {
            if (n) {
                buf[--n] = 0;
            }
        } else if (n < max && accepte(c, mode)) {
            buf[n++] = c;
            buf[n] = 0;
        }
    }
}

#define Y_MESSAGE 7

/* Message de l'écran de connexion, centré sous le nom. */
static void message(const char *s)
{
    effacer(0, Y_MESSAGE, 40);
    ecrire((40 - strlen(s)) / 2, Y_MESSAGE, s, JAUNE, FOND_VERT);
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

/* Message de refus du serveur (ERR ...) en clair  */
static void refus(void)
{
    if (!strcmp(erreur, "TABLE PLEINE")) {
        message(T(T_M_PLEINE));
        return;
    }
    if (!strcmp(erreur, "NOM RESERVE")) {
        message(T(T_M_NOM_BOT));
        return;
    }
    if (!strcmp(erreur, "NOM")) {
        message(T(T_M_NOM_REFUSE));
        return;
    }
    strcpy(tx, T(T_REFUS));
    strncat(tx, motif_refus(erreur), 40 - strlen(tx));
    message(tx);
}

static void ferme(void)
{
    if (sock >= 0) {
        net_fermer(sock);
        sock = -1;
    }
}

/* Lignes 3 et 5 : le NOM centré, ou le réglage du serveur (IP et PORT). */
static void champs_connexion(void)
{
    unsigned char l;

    effacer(0, 3, 40);
    effacer(0, 5, 40);
    if (reglage) {
        ecrire(1, 3, "IP", BLANC, FOND_VERT);
        ecrire(1, 5, T(T_C_PORT), BLANC, FOND_VERT);
        ecrire(CHAMP_X - 1, 3, ":", BLANC, FOND_VERT);
        ecrire(CHAMP_X - 1, 5, ":", BLANC, FOND_VERT);
        ecrire(CHAMP_X, 3, hote, BLANC, FOND_VERT);
        ecrire(CHAMP_X, 5, port_txt, BLANC, FOND_VERT);
    } else {
        /* « NOM : JEAN » centré, le champ réservé sur 6 lettres et le curseur. */
        l = strlen(T(T_C_NOM));
        nom_cx = (40 - 3 - NOM_MAX - 1 - l) / 2 + l + 3;
        ecrire(nom_cx - 3 - l, 5, T(T_C_NOM), BLANC, FOND_VERT);
        ecrire(nom_cx - 2, 5, ":", BLANC, FOND_VERT);
        ecrire(nom_cx, 5, nom, BLANC, FOND_VERT);
    }
}

/* Libellés de l'écran de connexion dans la langue choisie ; en bas, les
 * langues dans la leur, celle en cours en jaune (F1 passe à la suivante), et la
 * barre de touches comme en jeu. */
static void textes_connexion(void)
{
    unsigned char i, x;
    const char *s = T(T_C_INFO);

    champs_connexion();
    effacer(0, 16, 40);
    ecrire((40 - strlen(s)) / 2, 16, s, GRIS_CLAIR, FOND_VERT);
    /* FRANCAIS ENGLISH DEUTSCH ESPANOL, chacun dans sa langue : 35 colonnes
     * quelle que soit la langue, centrées à partir de la colonne 2. */
    x = 2;
    for (i = 0; i < NB_LANGUES; ++i) {
        ecrire(x, 22, textes[i][T_LANGUE], i == langue ? JAUNE : GRIS_FONCE, FOND_VERT);
        x += strlen(textes[i][T_LANGUE]) + 2;
    }
    barre(T(T_B_CONNEXION));
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

static void ecran_connexion(unsigned char animer)
{
    ecran_effacer();
    bandeau(0);
    ecrire(1, 0, "BELOTE LAN C64", JAUNE, FOND_NOIR);
    ecrire(39 - sizeof(VERSION), 0, "V" VERSION, GRIS_CLAIR, FOND_NOIR);   /* jusqu'à la case 38 */
    ligne_tirets(20);
    textes_connexion();
    cartes_connexion(animer);
}

/* Liste des salons, une fois connecté (SPEC 2.1) : renvoie le salon choisi (1 à 9),
 * 0 si le serveur n'a pas de salons (il répond ERR à SALONS : JOIN sans numéro),
 * K_F7 pour revenir au nom ou si la connexion est coupée. msg : sous la liste. */
#define Y_SALONS 5
static unsigned char choisir_salon(const char *msg)
{
    unsigned char i, k, sel = 0;
    unsigned debut = jiffies();

    nb_salons = -1;
    erreur[0] = 0;
    envoyer("SALONS");
    while ((nb_salons < 0 || sal_recus < (unsigned char)nb_salons) && !erreur[0] && !perdu
           && moi < 0 && jiffies() - debut < 5 * 60) {
        reseau();
    }
    if (perdu) {
        return K_F7;
    }
    if (nb_salons <= 0 || sal_recus < (unsigned char)nb_salons) {
        erreur[0] = 0;
        return 0;
    }
    for (i = 3; i < 16; ++i) {
        effacer(0, i, 40);
    }
    ecrire((40 - strlen(T(T_S_TITRE))) / 2, 3, T(T_S_TITRE), JAUNE, FOND_VERT);
    if (msg) {
        ecrire((40 - strlen(msg)) / 2, 15, msg, JAUNE, FOND_VERT);
    }
    barre(T(T_B_SALONS));
    for (;;) {
        for (i = 0; i < (unsigned char)nb_salons; ++i) {
            fmt(tx, "%c %s %u   %u/4   %s", i == sel ? '>' : ' ', T(T_S_SALON), i + 1, sal_h[i],
                T(sal_jeu[i] ? T_S_JEU : T_S_ATTENTE));
            ecrire_n(8, Y_SALONS + i, tx, 26, i == sel ? JAUNE : BLANC, FOND_VERT);
        }
        k = touche_connexion();
        if (k == K_F7 || k == K_RETURN) {
            return k == K_F7 ? K_F7 : sel + 1;
        }
        if (k >= '1' && k < '1' + (unsigned char)nb_salons) {
            return k - '0';
        }
        if (k == K_HAUT && sel) {
            --sel;
        } else if (k == K_BAS && sel + 1 < (unsigned char)nb_salons) {
            ++sel;
        }
    }
}

/* Revient quand le serveur a confirmé la place par BIENVENUE. */
static void connexion(void)
{
    unsigned char k, s;
    unsigned port, debut;
    const char *msg;
    static unsigned char deja;      /* donne déjà animée */

    reglage = 0;
    /* La donne animée une fois, en arrivant de l'écran titre. */
    ecran_connexion(!deja);
    deja = 1;
    if (perdu) {
        message(T(T_M_PERDUE));
        perdu = 0;
    }

    for (;;) {
        k = reglage == 0 ? saisir(nom_cx, 5, nom, NOM_MAX, 0)
            : reglage == 1 ? saisir(CHAMP_X, 3, hote, IP_MAX, 1)
            : saisir(CHAMP_X, 5, port_txt, PORT_MAX, 2);
        if (k == K_F1 || k == K_LANGUE_PREC) {
            langue_choisir(k == K_F1 ? langue + 1 : (langue + NB_LANGUES - 1) % NB_LANGUES);
            textes_connexion();
            cartes_connexion(0);            /* figures de la nouvelle langue */
            effacer(0, Y_MESSAGE, 40);
            continue;
        }
        /* Réglage du serveur : F3 l'ouvre et le ferme ; haut, bas ou RETURN sur
         * l'IP passent d'un champ à l'autre, RETURN sur le port revient au nom. */
        if (reglage && (k == K_HAUT || k == K_BAS || (k == K_RETURN && reglage == 1))) {
            reglage ^= 3;
            continue;
        }
        if (k == K_F3 || (reglage && k == K_RETURN)) {
            reglage = reglage ? 0 : 1;
            champs_connexion();
            continue;
        }
        if (k != K_RETURN) {
            continue;
        }
        if (!nom[0]) {
            message(T(T_M_ENTREZ_NOM));
            continue;
        }
        if (nom_de_bot(nom)) {
            message(T(T_M_NOM_BOT));
            continue;
        }
        if (!hote[0]) {
            reglage = 1;
            champs_connexion();
            continue;
        }
        if (!uci_present()) {
            message(T(T_M_UCI));
            continue;
        }

        port = atoi(port_txt);
        if (!port) {
            port = PORT_DEFAUT;
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
            continue;
        }

        jeu_raz();
        lg = deborde = 0;
        perdu = 0;
        msg = 0;
        for (;;) {
            s = choisir_salon(msg);
            if (s == K_F7) {
                break;
            }
            strcpy(tx, "JOIN ");
            strcat(tx, nom);
            if (s) {                        /* « JOIN JEAN 3 » */
                k = strlen(tx);
                tx[k] = ' ';
                tx[k + 1] = '0' + s;
                tx[k + 2] = 0;
            }
            envoyer(tx);
            debut = jiffies();
            while (moi < 0 && !erreur[0] && !perdu && jiffies() - debut < 5 * 60) {
                reseau();
            }
            if (moi >= 0) {
                return;
            }
            /* Salon rempli entre-temps : la connexion reste ouverte, la liste à jour. */
            if (!s || perdu || strcmp(erreur, "TABLE PLEINE")) {
                break;
            }
            msg = T(T_M_PLEINE);
        }
        ecran_connexion(0);
        if (erreur[0]) {
            refus();
        } else if (perdu) {
            message(T(T_M_FERMEE));
        } else if (s != K_F7) {
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
static unsigned char a_moi_d_encherir(void)
{
    return etat == E_COURS && tour == moi && atout < 0 && retournee >= 0;
}

static unsigned char a_moi_de_jouer(void)
{
    return etat == E_COURS && tour == moi && atout >= 0;
}

static void enchere(unsigned char k)
{
    unsigned char c, couleur = retournee >> 3;
    if (!a_moi_d_encherir()) {
        return;
    }
    tour = -1;                      /* plus mon tour : pas de second envoi */
    sale |= D_ENCH | D_TABLE;
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

/* Joue la carte i de la main si la règle le permet (sinon rien : elle n'est pas
 * sortie du rang). */
static void jouer(unsigned char i)
{
    unsigned char ok[8];
    if (!a_moi_de_jouer() || i >= nmain) {
        return;
    }
    jouables(ok);
    if (!ok[i]) {
        return;
    }
    envoyer_nombre("COUP ", (unsigned char)main_c[i]);
    tour = -1;                      /* plus mon tour : pas de second envoi */
    sale |= D_MAIN | D_ENCH;
}

/* Gauche (d = 255) ou droite (d = 1) : enchère voisine, ou carte jouable voisine. */
static void choisir(unsigned char d)
{
    unsigned char ok[8], i, k, n;
    if (a_moi_d_encherir()) {
        n = tour_ench == 1 ? 2 : 4;
        ench_sel = d == 1 ? (ench_sel + 1) % n : (ench_sel + n - 1) % n;
        sale |= D_ENCH;
        return;
    }
    if (!a_moi_de_jouer()) {
        return;
    }
    jouables(ok);
    i = sel;
    for (k = 0; k < nmain; ++k) {
        i = (unsigned char)(i + d) & 7;
        if (i < nmain && ok[i]) {
            sel = i;
            break;
        }
    }
    sale |= D_MAIN;
}

/* RETURN, ESPACE ou le bouton : l'enchère choisie, la carte choisie, ou en fin de
 * manche la suite (comme F5). */
static void valider(void)
{
    if (a_moi_d_encherir()) {
        enchere(ench_sel + 1);
    } else if (a_moi_de_jouer()) {
        jouer(sel);
    } else if (etat == E_FIN_MANCHE && (suite || suis_chef())) {
        envoyer("REJOUER");
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
    case K_GAUCHE:
        choisir(255);
        break;
    case K_DROITE:
        choisir(1);
        break;
    case K_RETURN:
    case K_ESPACE:
        valider();
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
        } else {
            jouer(c - 1);
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
        tour = -1;                  /* comme jouer() : la main redescend aussitôt */
        sale |= D_MAIN | D_ENCH;
    }
}

/* Joystick en port 2 : gauche, droite, bouton (sur front). */
static void joystick(void)
{
    unsigned char j = joy_read(JOY_2), nouveau = j & ~joy_avant;
    joy_avant = j;
    if (!nouveau || tchat || regles || param || raz_conf) {
        return;
    }
    if (JOY_LEFT(nouveau)) {
        choisir(255);
    } else if (JOY_RIGHT(nouveau)) {
        choisir(1);
    } else if (JOY_BTN_1(nouveau)) {
        valider();
    }
}

static void partie(void)
{
    regles = param = tchat = raz_conf = 0;
    vue_forcer();
    for (;;) {
        reseau();
        derniere_carte();
        joystick();
        /* nouveau tour d'enchères pour moi : le choix repart sur PASSE (un
         * appui involontaire ne fait jamais prendre) */
        if (a_moi_d_encherir() && (!ench_mien || tour_ench != ench_tour)) {
            ench_sel = tour_ench == 1 ? 1 : 3;
            ench_tour = tour_ench;
            sale |= D_ENCH;
        }
        ench_mien = a_moi_d_encherir();
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
    char *p;

    langue_choisir(langue);
    joy_install(joy_static_stddrv);
    son_init();
    titre();                        /* avant ecran_init : l'image est déjà en place */
    ecran_init();
    /* « hôte:port » de config.mk, coupé en ses deux champs. */
    strcpy(hote, SERVEUR_DEFAUT);
    p = strchr(hote, ':');
    if (p) {
        *p = 0;
        strcpy(port_txt, p + 1);
    }
    for (;;) {
        connexion();
        partie();
    }
    return 0;
}
