; Décompression de l'écran titre (données de tools/titre.py, voir c64/titre.c) :
; un bit par case de 8x8 pixels (1 = feutre, case commune titre_feutre), les
; autres cases à la suite dans titre_autres, 10 octets chacune (8 de bitmap,
; matrice écran, RAM couleur). En assembleur : en C, cc65 mettait près d'une
; seconde de plus à afficher l'image.

        .export _titre_decompresser
        .import _titre_feutre, _titre_cases, _titre_autres
        .importzp ptr1, ptr2, ptr3, ptr4, tmp1

BITMAP  = $E000             ; RAM sous le KERNAL : le CPU y écrit, le VIC la lit
ECRAN   = $C000
COULEUR = $D800

        .segment "CODE"

; void titre_decompresser(void)
_titre_decompresser:
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
