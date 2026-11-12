/* À inclure en premier dans chaque fichier C.
 *
 * Pour la cible c64, cc65 convertit les littéraux en PETSCII : 'A' deviendrait
 * $C1 (majuscule du mode minuscules). Le client tourne en mode
 * majuscules/graphiques, où A-Z valent $41-$5A, comme en ASCII : on demande donc
 * l'identité pour $40-$5F. Littéraux, clavier (GETIN) et réseau parlent alors le
 * même code et rien n'est converti à l'émission ni à la réception.
 *
 * Attention : "\n" vaut 13 (CR) pour la cible c64 ; le LF du protocole s'écrit 10.
 */
#ifndef ASCII_H
#define ASCII_H

#pragma charmap (0x40, 0x40)
#pragma charmap (0x41, 0x41)
#pragma charmap (0x42, 0x42)
#pragma charmap (0x43, 0x43)
#pragma charmap (0x44, 0x44)
#pragma charmap (0x45, 0x45)
#pragma charmap (0x46, 0x46)
#pragma charmap (0x47, 0x47)
#pragma charmap (0x48, 0x48)
#pragma charmap (0x49, 0x49)
#pragma charmap (0x4A, 0x4A)
#pragma charmap (0x4B, 0x4B)
#pragma charmap (0x4C, 0x4C)
#pragma charmap (0x4D, 0x4D)
#pragma charmap (0x4E, 0x4E)
#pragma charmap (0x4F, 0x4F)
#pragma charmap (0x50, 0x50)
#pragma charmap (0x51, 0x51)
#pragma charmap (0x52, 0x52)
#pragma charmap (0x53, 0x53)
#pragma charmap (0x54, 0x54)
#pragma charmap (0x55, 0x55)
#pragma charmap (0x56, 0x56)
#pragma charmap (0x57, 0x57)
#pragma charmap (0x58, 0x58)
#pragma charmap (0x59, 0x59)
#pragma charmap (0x5A, 0x5A)
#pragma charmap (0x5B, 0x5B)
#pragma charmap (0x5C, 0x5C)
#pragma charmap (0x5D, 0x5D)
#pragma charmap (0x5E, 0x5E)
#pragma charmap (0x5F, 0x5F)

#define LF 10

#endif
