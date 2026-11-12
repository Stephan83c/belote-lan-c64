/* État de l'interface locale (vues, saisie du tchat, réglages F1). */
#ifndef UI_H
#define UI_H

enum { V_TABLE, V_REGLES, V_PARAM, V_FIN };

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

#endif
