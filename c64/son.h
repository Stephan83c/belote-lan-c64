/* Musique et bruitages (c64/son.s, données générées par tools/musique.py). */
#ifndef SON_H
#define SON_H

/* Airs, dans l'ordre de AIRS de tools/musique.py */
#define AIR_TITRE    0
#define AIR_VICTOIRE 1
#define AIR_DEFAITE  2

/* Bruitages (voix 3), dans l'ordre de EFFETS */
#define FX_CARTE 0
#define FX_PLI   1
#define FX_TCHAT 2
#define FX_RAMASSE 3

/* Volume et branchement sur l'interruption du KERNAL, une fois au démarrage. */
void son_init(void);
void son_musique(unsigned char air);
void son_stop(void);
void son_effet(unsigned char fx);

#endif
