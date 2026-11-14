/* État de l'interface locale (vues, saisie du tchat, réglages F1). */
#ifndef UI_H
#define UI_H

enum { V_TABLE, V_REGLES, V_PARAM, V_FIN };

extern unsigned char raz_conf;      /* F4 : confirmation O/N de l'effacement */
extern unsigned char regles;        /* F8 : règles affichées */
extern unsigned char param;         /* F1 : réglages ouverts */
extern unsigned char param_sel;     /* 0 cible, 1 inactivité */
extern unsigned param_cible, param_inactif;
extern unsigned char tchat;         /* F3 : saisie en cours */
extern char tchat_txt[];
extern unsigned char tchat_n;

unsigned char vue_courante(void);
void dessiner(void);
void vue_forcer(void);
/* Distribue la carte c (sprite qui glisse depuis le point sx, sy, en pixels de
 * sprite) jusqu'à la case x, y, où elle reste en texte. */
void donner(signed char c, int sx, int sy, unsigned char x, unsigned char y);
/* Écran titre, jusqu'à une touche. */
void titre(void);

#endif
