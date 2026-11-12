/* Ultimate Command Interface ($DF1C-$DF1F), cible réseau. */
#ifndef UCI_H
#define UCI_H

/* Vrai si l'interface répond (option « Command Interface » activée). */
unsigned char uci_present(void);

/* Ouvre une connexion TCP ; renvoie le numéro de socket, ou -1. */
int net_ouvrir(const char *hote, unsigned port);

/* Lecture non bloquante : nombre d'octets copiés (0 si rien). max <= 96. */
unsigned char net_lire(unsigned char sock, char *dst, unsigned char max);

/* Écriture ; renvoie 1 si l'Ultimate a accepté. */
unsigned char net_ecrire(unsigned char sock, const char *src, unsigned char n);

void net_fermer(unsigned char sock);

/* Dernier statut texte de l'Ultimate (ex. « 00,OK »), pour diagnostic. */
extern char uci_statut[];

#endif
