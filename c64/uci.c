#include "ascii.h"
#include <string.h>
#include "uci.h"

/* Registres : $DF1C contrôle (écriture) / état (lecture) ; $DF1D commande
 * (écriture) / identification $C9 (lecture) ; $DF1E données de réponse ;
 * $DF1F texte de statut. */
#define UCI_CTRL (*(volatile unsigned char *)0xDF1C)
#define UCI_CMD  (*(volatile unsigned char *)0xDF1D)
#define UCI_RESP (*(volatile unsigned char *)0xDF1E)
#define UCI_STAT (*(volatile unsigned char *)0xDF1F)

/* Bits de l'état */
#define ST_DATA_AV 0x80
#define ST_STAT_AV 0x40
#define ST_ETAT    0x30   /* 00 repos, 01 occupé, 10 dernières données, 11 suite */
#define ST_ERREUR  0x08
#define ST_ACC     0x02

/* Bits du contrôle */
#define CT_PUSH    0x01
#define CT_ACC     0x02
#define CT_ABORT   0x04
#define CT_CLR_ERR 0x08

#define CIBLE_RESEAU   0x03
#define NET_OUVRIR_TCP 0x07
#define NET_FERMER     0x09
#define NET_LIRE       0x10
#define NET_ECRIRE     0x11

#define REP_MAX  128
#define STAT_MAX 40

static unsigned char rep[REP_MAX];
static unsigned char rep_n;
char uci_statut[STAT_MAX + 1];
static unsigned char cmd[80];

unsigned char uci_present(void)
{
    return UCI_CMD == 0xC9;
}

static void attendre_repos(void)
{
    unsigned t = 0;
    unsigned char e;
    while ((e = UCI_CTRL & ST_ETAT) != 0) {
        if (e & 0x20) {            /* données d'une commande précédente : acquitter */
            UCI_CTRL = CT_ACC;
        }
        if (++t == 0) {            /* bloquée : abandon */
            UCI_CTRL = CT_ABORT;
            t = 0;
        }
    }
}

/* Envoie cmd[0..n-1] et lit la réponse dans rep / uci_statut.
 * Renvoie 1 si le statut commence par « 00 ». */
static unsigned char executer(unsigned char n)
{
    unsigned char i, s, ns = 0;

    rep_n = 0;
    uci_statut[0] = 0;
    attendre_repos();
    for (i = 0; i < n; ++i) {
        UCI_CMD = cmd[i];
    }
    UCI_CTRL = CT_PUSH;
    if (UCI_CTRL & ST_ERREUR) {
        UCI_CTRL = CT_CLR_ERR;
        return 0;
    }
    for (;;) {
        /* attendre la fin du traitement (état 10 ou 11) */
        while (((s = UCI_CTRL) & 0x20) == 0) {
        }
        while (UCI_CTRL & ST_DATA_AV) {
            i = UCI_RESP;
            if (rep_n < REP_MAX) {
                rep[rep_n++] = i;
            }
        }
        while (UCI_CTRL & ST_STAT_AV) {
            i = UCI_STAT;
            if (ns < STAT_MAX) {
                uci_statut[ns++] = i;
            }
        }
        if ((s & ST_ETAT) == 0x30) {   /* encore des données : acquitter et continuer */
            UCI_CTRL = CT_ACC;
            while (UCI_CTRL & ST_ACC) {
            }
            continue;
        }
        break;
    }
    uci_statut[ns] = 0;
    UCI_CTRL = CT_ACC;
    while (UCI_CTRL & ST_ACC) {
    }
    return uci_statut[0] == '0' && uci_statut[1] == '0';
}

int net_ouvrir(const char *hote, unsigned port)
{
    unsigned char n = strlen(hote);
    if (n > 60) {
        return -1;
    }
    cmd[0] = CIBLE_RESEAU;
    cmd[1] = NET_OUVRIR_TCP;
    cmd[2] = port & 0xFF;
    cmd[3] = port >> 8;
    memcpy(cmd + 4, hote, n);
    cmd[4 + n] = 0;
    if (!executer(5 + n) || rep_n < 1) {
        return -1;
    }
    return rep[0];
}

unsigned char net_lire(unsigned char sock, char *dst, unsigned char max)
{
    unsigned lu;
    cmd[0] = CIBLE_RESEAU;
    cmd[1] = NET_LIRE;
    cmd[2] = sock;
    cmd[3] = max;
    cmd[4] = 0;
    executer(5);
    if (rep_n < 2) {
        return 0;
    }
    /* 2 octets de longueur (petit-boutiste, négative si rien) puis les données */
    lu = rep[0] | (rep[1] << 8);
    if (lu == 0 || lu > max || lu > rep_n - 2) {
        return 0;
    }
    memcpy(dst, rep + 2, lu);
    return (unsigned char)lu;
}

unsigned char net_ecrire(unsigned char sock, const char *src, unsigned char n)
{
    if (n > 70) {
        return 0;
    }
    cmd[0] = CIBLE_RESEAU;
    cmd[1] = NET_ECRIRE;
    cmd[2] = sock;
    memcpy(cmd + 3, src, n);
    return executer(3 + n);
}

void net_fermer(unsigned char sock)
{
    cmd[0] = CIBLE_RESEAU;
    cmd[1] = NET_FERMER;
    cmd[2] = sock;
    executer(3);
}
