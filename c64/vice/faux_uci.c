/* Réseau simulé pour VICE, qui n'émule pas la Command Interface de l'Ultimate.
 * Remplace uci.c : le client « reçoit » un scénario écrit d'avance, puis plus
 * rien ; ce qu'il envoie est ignoré. make vice-demo SCENARIO=1, 2 ou 3 :
 * 1 table d'attente et tchat, 2 partie reprise en cours de manche, 3 fin de partie,
 * 4 le serveur ferme la connexion : bordure rouge si le client touche encore au socket,
 * 5 second tour d'enchères, à notre tour. */
#include "../ascii.h"
#include <string.h>
#include "../uci.h"
char uci_statut[41];
unsigned char uci_bloquee;
#if SCENARIO == 1
static const char *const lignes[] = {
 "BIENVENUE JEAN 2", "SIEGE 0 H MARC", "SIEGE 1 B BOT", "SIEGE 2 H JEAN", "SIEGE 3 H LEA",
 "CHEF 0", "ETAT ATTENTE", "PARAM CIBLE 1500", "PARAM INACTIF 3",
 "TCHAT MARC SALUT LA COMPAGNIE", "TCHAT LEA ON Y VA ?", "TCHAT JEAN 123456789012345678901234567890",
 "INFO PAUL INACTIF REMPLACE PAR UN BOT", "ERR CHEF SEUL", 0 };
#elif SCENARIO == 2
static const char *const lignes[] = {
 "BIENVENUE JEAN 1", "SIEGE 0 H MARC", "SIEGE 1 H JEAN", "SIEGE 2 B BOT", "SIEGE 3 B BOT",
 "CHEF 0", "ETAT EN COURS", "SCORE 432 1018", "DONNEUR 0",
 "MAIN 3 5 6 11 15 22", "NBCARTES 6 6 7 7", "RETOURNE 30", "ENCHERES 1",
 "PASSE 1", "PREND 2 3", "BELOTE 2", "INFO MARC RECONNECTE",
 "PLICOURS 7 -1 29 31", "TOUR 1", 0 };
#elif SCENARIO == 3
static const char *const lignes[] = {
 "BIENVENUE JEAN 1", "SIEGE 0 H MARC", "SIEGE 1 H JEAN", "SIEGE 2 B BOT", "SIEGE 3 B BOT",
 "CHEF 1", "ETAT EN COURS", "MANCHE 40 122", "SCORE 960 1052", "GAGNANT 1", "ETAT FIN PARTIE", 0 };
#elif SCENARIO == 5
static const char *const lignes[] = {
 "BIENVENUE JEAN 0", "SIEGE 0 H JEAN", "SIEGE 1 B BOT", "SIEGE 2 B BOT", "SIEGE 3 B BOT",
 "CHEF 0", "ETAT EN COURS", "DONNEUR 3", "MAIN 3 5 6 11 15", "NBCARTES 5 5 5 5",
 "RETOURNE 20", "ENCHERES 1", "TOUR 0", "PASSE 0", "TOUR 1", "PASSE 1", "TOUR 2",
 "PASSE 2", "TOUR 3", "PASSE 3", "ENCHERES 2", "TOUR 0", 0 };
#else
static const char *const lignes[] = {
 "BIENVENUE JEAN 0", "SIEGE 0 H JEAN", "SIEGE 1 B BOT", "SIEGE 2 B BOT", "SIEGE 3 B BOT",
 "CHEF 0", "ETAT ATTENTE", 0 };
#define FERMER_APRES 1
#endif
static unsigned char fermee;
#define FAUTE() (*(volatile unsigned char *)0xD020 = 2)
static unsigned char i;
unsigned char uci_present(void) { return 1; }
int net_ouvrir(const char *h, unsigned p) { (void)h; (void)p; return 0; }
int net_lire(unsigned char s, char *dst, unsigned char max)
{
    unsigned char n;
    (void)s; (void)max;
    if (fermee) { FAUTE(); return -1; }
    if (!lignes[i]) {
#ifdef FERMER_APRES
        fermee = 1;
        return -1;
#else
        return 0;
#endif
    }
    n = strlen(lignes[i]);
    memcpy(dst, lignes[i++], n);
    dst[n] = LF;
    return n + 1;
}
unsigned char net_ecrire(unsigned char s, const char *src, unsigned char n) { (void)s; (void)src; (void)n; if (fermee) FAUTE(); return 1; }
void net_fermer(unsigned char s) { (void)s; if (fermee) FAUTE(); }
