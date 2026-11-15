; Décompression de l'écran titre (données de tools/titre.py, voir c64/titre.c) :
; un bit par case de 8x8 pixels (1 = feutre, case commune titre_feutre), les
; autres cases à la suite dans titre_autres, 10 octets chacune (8 de bitmap,
; matrice écran, RAM couleur). En assembleur : en C, cc65 mettait près d'une
; seconde de plus à afficher l'image.
;
; Segment ONCE, comme les données : un constructeur décompresse l'image au
; chargement, avant que crt0 remette les variables à zéro (zerobss) et appelle
; main ; ensuite, cette place sert aux variables. L'écran reste éteint jusqu'à
; titre() (c64/titre.c).

        .constructor titre_preparer
        .import _titre_feutre, _titre_cases, _titre_autres
        .importzp ptr1, ptr2, ptr3, ptr4, tmp1

BITMAP  = $E000             ; RAM sous le KERNAL : le CPU y écrit, le VIC la lit
ECRAN   = $C000
COULEUR = $D800

        .segment "ONCE"

titre_preparer:
        lda $D011           ; écran éteint pendant la copie
        and #$EF
        sta $D011
        lda $DD00           ; banque VIC 3 : $C000-$FFFF
        and #$FC
        sta $DD00
        lda #9              ; bordure brune (BRUN), comme en jeu
        sta $D020
        lda #5              ; fond vert (VERT) : le feutre de l'image
        sta $D021
        lda #<BITMAP
        sta ptr1
        lda #>BITMAP
        sta ptr1+1
        lda #<_titre_autres
        sta ptr2
        lda #>_titre_autres
        sta ptr2+1
        lda #<ECRAN
        sta ptr3
        lda #>ECRAN
        sta ptr3+1
        lda #<COULEUR
        sta ptr4
        lda #>COULEUR
        sta ptr4+1
        ldx #0              ; octet de titre_cases
        lda #$80
        sta tmp1            ; bit de la case
@case:  lda _titre_cases,x
        and tmp1
        beq @autre
        ldy #7              ; feutre
@f:     lda _titre_feutre,y
        sta (ptr1),y
        dey
        bpl @f
        ldy #0
        lda _titre_feutre+8
        sta (ptr3),y
        lda _titre_feutre+9
        sta (ptr4),y
        jmp @suite
@autre: ldy #7
@a:     lda (ptr2),y
        sta (ptr1),y
        dey
        bpl @a
        ldy #8
        lda (ptr2),y
        ldy #0
        sta (ptr3),y
        ldy #9
        lda (ptr2),y
        ldy #0
        sta (ptr4),y
        lda ptr2
        clc
        adc #10
        sta ptr2
        bcc @suite
        inc ptr2+1
@suite: lda ptr1            ; case suivante
        clc
        adc #8
        sta ptr1
        bcc :+
        inc ptr1+1
:       inc ptr3
        bne :+
        inc ptr3+1
:       inc ptr4
        bne :+
        inc ptr4+1
:       lsr tmp1
        bne :+
        lda #$80
        sta tmp1
        inx
:       lda ptr3
        cmp #<(ECRAN + 1000)
        bne @case
        lda ptr3+1
        cmp #>(ECRAN + 1000)
        bne @case
        rts
