"""Cadrage et encodage des lignes du protocole (SPEC 7.1)."""

from __future__ import annotations

LONGUEUR_MAX = 64  # LF compris
TROP_LONG = object()  # marqueur renvoyé par Cadreur pour une ligne refusée


def nettoyer(brut: bytes) -> str:
    """Majuscules ; tout octet hors ASCII 32-95 devient « ? ».

    Les majuscules PETSCII du mode minuscules ($C1-$DA) valent A-Z, pour un
    client C64 qui n'aurait pas converti son texte en ASCII. Suivi d'un octet
    $80-$BF, un tel octet ouvre un caractère UTF-8 (é = $C3 $A9) : « ? ».
    """
    sortie = []
    for i, octet in enumerate(brut):
        if 97 <= octet <= 122:
            octet -= 32
        elif 0xC1 <= octet <= 0xDA and not (i + 1 < len(brut) and 0x80 <= brut[i + 1] <= 0xBF):
            octet -= 0x80
        sortie.append(chr(octet) if 32 <= octet <= 95 else "?")
    return "".join(sortie)


class Cadreur:
    """Découpe un flux d'octets en lignes nettoyées.

    Une ligne de plus de 64 octets (LF compris, CR éventuel non compté) est
    ignorée et signalée par TROP_LONG quand son LF arrive.
    """

    def __init__(self) -> None:
        self._tampon = bytearray()
        self._deborde = False

    def alimenter(self, octets: bytes) -> list:
        self._tampon += octets
        lignes: list = []
        while (fin := self._tampon.find(b"\n")) >= 0:
            brut = bytes(self._tampon[:fin])
            del self._tampon[: fin + 1]
            if brut.endswith(b"\r"):
                brut = brut[:-1]
            if self._deborde or len(brut) + 1 > LONGUEUR_MAX:
                self._deborde = False
                lignes.append(TROP_LONG)
            else:
                lignes.append(nettoyer(brut))
        # Sans LF, inutile de conserver plus qu'une ligne valide suivie d'un CR.
        if len(self._tampon) > LONGUEUR_MAX:
            self._tampon.clear()
            self._deborde = True
        return lignes
