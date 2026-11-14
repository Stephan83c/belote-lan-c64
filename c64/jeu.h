/* État de la table vu par le client, tenu à jour par les messages du serveur. */
#ifndef JEU_H
#define JEU_H

enum { E_AUCUN, E_ATTENTE, E_LANCEE, E_COURS, E_FIN_MANCHE, E_FIN_PARTIE };

/* Parties de l'écran à redessiner */
#define D_ENTETE  0x01
#define D_TABLE   0x02
#define D_JOURNAL 0x04
#define D_ENCH    0x08
#define D_MAIN    0x10
#define D_BARRE   0x20
#define D_SAISIE  0x40
#define D_TOUT    0xFF

#define NOM_MAX   5
#define TCHAT_MAX 30

extern signed char moi;            /* place, -1 avant BIENVENUE */
extern char noms[4][NOM_MAX + 1];
extern unsigned char humain[4];
extern signed char chef;
extern unsigned char etat;
extern unsigned cible, inactif;
extern unsigned scores[2];
extern signed char donneur, tour, preneur, atout, retournee, gagnant;
/* Carte retournée qui vient d'être prise : affichée jusqu'à la première carte jouée. */
extern signed char prise;
/* Noms des bots par place absolue : BOT1 à BOT4. */
extern const char *const noms_bots[4];
extern unsigned char tour_ench;
extern signed char main_c[8];
extern unsigned char nmain;
extern unsigned char nbcartes[4];
extern signed char pli[4];
extern unsigned char pli_fini;
extern unsigned char sale;         /* drapeaux D_* */
extern char erreur[41];            /* dernier ERR reçu (connexion) */

/* Journal L12-L17 */
#define JOURNAL_N 6
struct entree {
    char nom[NOM_MAX + 1];         /* vide : message serveur sur toute la ligne */
    unsigned char coul_nom;
    char texte[40];
    unsigned char coul_texte;
};
extern struct entree journal[JOURNAL_N];

void jeu_raz(void);
void traiter_ligne(char *ligne);
void journal_info(const char *texte);
/* Texte d'un motif de refus (ERR) dans la langue choisie. */
const char *motif_refus(const char *code);
/* Rang d'une carte (0 = 7 ... 7 = A), figures de la langue choisie. */
const char *nom_rang(unsigned char r);
/* Position à l'écran (0 SUD, 1 EST, 2 NORD, 3 OUEST) d'une place absolue. */
#define REL(p) ((unsigned char)(((p) - moi + 4) & 3))
/* Couleur du nom d'une place dans le tchat */
extern const unsigned char coul_place[4];

#endif
