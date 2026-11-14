; Lecteur de musique et de bruitages SID, appelé par l'interruption du KERNAL
; (60 fois par seconde, y compris pendant les commandes réseau).
;
; Les airs (écran titre, victoire, défaite) jouent sur les voix 1 à 3 ; les
; bruitages sur la voix 3, que l'air laisse alors de côté. Un bruitage demandé
; pendant qu'un autre joue attend la fin de celui-ci (le dernier demandé gagne) :
; la carte posée s'entend encore quand le pli est ramassé juste après.
; Données : c64/son_donnees.s (tools/musique.py).

        .export _son_init, _son_musique, _son_stop, _son_effet
        .import son_freq_lo, son_freq_hi, son_airs, son_effets

SID     = $D400
CINV    = $0314             ; vecteur d'interruption du KERNAL

; Page zéro libre sous le KERNAL (celle de cc65 est pleine)
ptr     = $FB               ; réservé à l'interruption
ptr_c   = $FD               ; réservé à son_musique (interruption masquée)

        .segment "BSS"
v_actif: .res 3
v_lo:   .res 3              ; position dans le flux
v_hi:   .res 3
v_deb_lo: .res 3            ; début du flux (boucle)
v_deb_hi: .res 3
v_dur:  .res 3              ; images restantes de la note en cours
v_note: .res 3
v_onde: .res 3              ; forme d'onde sans gate
v_arp1: .res 3
v_arp2: .res 3
v_arpc: .res 3              ; 0, 1, 2 : note jouée de l'arpège
v_pwl:  .res 3              ; largeur d'impulsion (12 bits) qui varie
v_pwh:  .res 3
v_pws:  .res 3              ; pas de sa variation par image (signé ; 0 : fixe)
v_vib:  .res 3              ; amplitude du vibrato (0 : sans)
lfo:    .res 1              ; compteur d'images du vibrato
vib_lo: .res 1              ; décalage de fréquence ajouté par frequence
vib_hi: .res 1
boucle: .res 1
fx_actif: .res 1
fx_file: .res 1             ; bruitage en attente + 1 (0 : aucun)
fx_lo:  .res 1
fx_hi:  .res 1
ancien: .res 2              ; ancien vecteur d'interruption
tmp:    .res 1
vx:     .res 1

        .segment "RODATA"
decal:  .byte 0, 7, 14      ; registres de chaque voix
PW_MIN  = $03               ; bornes de la largeur d'impulsion modulée (octet haut)
PW_MAX  = $08

        .segment "CODE"

; void son_init(void) : volume, puis branchement sur l'interruption.
_son_init:
        lda #0
        ldx #$18
@raz:   sta SID,x
        dex
        bpl @raz
        sta fx_actif
        sta fx_file
        sta v_actif
        sta v_actif+1
        sta v_actif+2
        lda #$0F
        sta SID+$18
        sei
        lda CINV
        sta ancien
        lda CINV+1
        sta ancien+1
        lda #<irq
        sta CINV
        lda #>irq
        sta CINV+1
        cli
        rts

; void son_effet(unsigned char n) : bruitage n (voix 3).
_son_effet:
        clc
        adc #1
        sta fx_file
        rts

; void son_stop(void) : coupe l'air en cours (pas le bruitage).
_son_stop:
        sei
        ldx #2
@v:     lda #0
        sta v_actif,x
        cpx #2
        bne @coupe
        lda fx_actif
        bne @suite
@coupe: ldy decal,x
        lda #0
        sta SID+4,y
@suite: dex
        bpl @v
        cli
        rts

; void son_musique(unsigned char n) : joue l'air n (remplace l'air en cours).
_son_musique:
        asl a
        tay
        sei
        lda son_airs,y
        sta ptr_c
        lda son_airs+1,y
        sta ptr_c+1
        ldy #0
        lda (ptr_c),y
        sta boucle
        iny
        ldx #0
@voix:  lda #0
        sta v_dur,x
        sta v_arp1,x
        sta v_arp2,x
        sta v_arpc,x
        lda (ptr_c),y       ; adresse du flux
        sta v_lo,x
        sta v_deb_lo,x
        iny
        lda (ptr_c),y
        sta v_hi,x
        sta v_deb_hi,x
        iny
        ora v_lo,x
        sta v_actif,x       ; 0 si voix muette
        lda (ptr_c),y
        sta v_onde,x
        iny
        sty tmp
        lda v_actif,x
        beq @saute          ; voix muette : registres laissés au bruitage
        cpx #2
        bne @regs
        lda fx_actif
        bne @saute
@regs:  stx vx
        lda decal,x
        tax                 ; x = décalage des registres le temps de les écrire
        lda #0
        sta SID+4,x         ; gate baissé
        sta SID+2,x
        ldy tmp
        lda (ptr_c),y
        sta SID+5,x         ; AD
        iny
        lda (ptr_c),y
        sta SID+6,x         ; SR
        iny
        lda (ptr_c),y
        sta SID+3,x         ; largeur d'impulsion
        ldx vx
@saute: ldy tmp
        iny
        iny
        lda (ptr_c),y       ; largeur d'impulsion de départ
        sta v_pwh,x
        lda #0
        sta v_pwl,x
        iny
        lda (ptr_c),y
        sta v_pws,x
        iny
        lda (ptr_c),y
        sta v_vib,x
        iny
        inx
        cpx #3
        beq @fini
        jmp @voix
@fini:
        cli
        rts

; ---- Interruption ---------------------------------------------------------

irq:
        cld
        inc lfo
        ldx #0
@v:     jsr voix
        jsr module
        inx
        cpx #3
        bne @v
        jsr effet
        jmp (ancien)

; Une image de la voix x.
voix:
        lda v_actif,x
        bne @actif
        rts
@actif: lda v_dur,x
        bne @joue
@lire:  lda v_lo,x
        sta ptr
        lda v_hi,x
        sta ptr+1
        ldy #0
        lda (ptr),y
        cmp #$FF
        bne @pas_fin
        lda boucle
        beq @fin
        lda v_deb_lo,x
        sta v_lo,x
        lda v_deb_hi,x
        sta v_hi,x
        jmp @lire
@fin:   lda #0
        sta v_actif,x
        jmp gate_bas
@pas_fin:
        cmp #$FD
        bne @note
        iny
        lda (ptr),y
        sta v_arp1,x
        iny
        lda (ptr),y
        sta v_arp2,x
        lda #3
        jsr avance
        jmp @lire
@note:  sta v_note,x
        iny
        lda (ptr),y
        sta v_dur,x
        lda #0
        sta v_arpc,x
        lda #2
        jsr avance
        lda v_note,x
        bne @son
        jsr gate_bas        ; silence
        jmp @compte
@son:   jsr frequence
        jsr libre
        bne @compte
        lda v_onde,x
        ora #1
        sta SID+4,y         ; gate levé : attaque
        jmp @compte
@joue:  lda v_note,x
        beq @compte
        lda v_arp1,x
        ora v_arp2,x
        beq @compte
        inc v_arpc,x        ; arpège : note suivante de l'accord
        lda v_arpc,x
        cmp #3
        bcc @arp
        lda #0
        sta v_arpc,x
@arp:   jsr frequence
@compte:
        dec v_dur,x
        lda v_dur,x
        cmp #1
        bne @rts
        jmp gate_bas        ; dernière image : gate baissé, la note suivante attaque
@rts:   rts

; Mouvement à l'intérieur de la note de la voix x : largeur d'impulsion qui va
; et vient entre PW_MIN et PW_MAX (le son s'épaissit), et vibrato rapide qui
; imite le battement des anches d'un accordéon musette (0, +1, +2, +1, 0, -1,
; -2, -1 fois l'amplitude, une étape par image : 7,5 Hz).
module_fin:
        rts
module: lda v_actif,x
        beq module_fin
        lda v_note,x
        beq module_fin      ; silence
        jsr libre           ; y = décalage des registres
        bne module_fin
        lda v_pws,x
        beq @vib
        clc
        adc v_pwl,x
        sta v_pwl,x
        lda v_pws,x
        and #$80
        beq @pos
        lda #$FF
@pos:   adc v_pwh,x
        sta v_pwh,x
        lda v_pws,x
        bmi @bas
        lda v_pwh,x
        cmp #PW_MAX
        bcc @ecrit
        bcs @inv
@bas:   lda v_pwh,x
        cmp #PW_MIN
        bcs @ecrit
@inv:   lda #0              ; demi-tour
        sec
        sbc v_pws,x
        sta v_pws,x
@ecrit: lda v_pwl,x
        sta SID+2,y
        lda v_pwh,x
        sta SID+3,y
@vib:   lda v_vib,x
        beq @r
        sta vib_lo
        lda #0
        sta vib_hi
        lda lfo
        and #3
        beq @zero           ; étapes 0 et 4 : sans décalage
        cmp #2
        bne @signe
        asl vib_lo          ; étapes 2 et 6 : double
        rol vib_hi
@signe: lda lfo
        and #4
        beq @appl
        lda #0              ; étapes 4 à 7 : vers le bas
        sec
        sbc vib_lo
        sta vib_lo
        lda #0
        sbc vib_hi
        sta vib_hi
        jmp @appl
@zero:  sta vib_lo
@appl:  jsr frequence
        lda #0
        sta vib_lo
        sta vib_hi
@r:     rts

; a += position du flux de la voix x
avance: clc
        adc v_lo,x
        sta v_lo,x
        bcc @r
        inc v_hi,x
@r:     rts

; Z=1 si la voix x peut écrire ses registres (y = décalage), Z=0 si le
; bruitage occupe la voix 3.
libre:  ldy decal,x
        cpx #2
        bne @oui
        lda fx_actif
        rts
@oui:   lda #0
        rts

gate_bas:
        jsr libre
        bne @r
        lda v_onde,x
        sta SID+4,y
@r:     rts

; Écrit la fréquence de la note de la voix x (avec l'arpège en cours).
frequence:
        lda v_note,x
        ldy v_arpc,x
        beq @f
        clc
        cpy #1
        bne @a2
        adc v_arp1,x
        jmp @f
@a2:    adc v_arp2,x
@f:     sta tmp
        jsr libre
        bne @r
        sty ptr             ; ptr sert ici de registre temporaire
        ldy tmp
        lda son_freq_lo,y
        clc
        adc vib_lo          ; vibrato (0 hors de module)
        pha
        lda son_freq_hi,y
        adc vib_hi
        ldy ptr
        sta SID+1,y
        pla
        sta SID,y
@r:     rts

; Une image du bruitage (voix 3).
effet:
        lda fx_actif
        bne @image
        lda fx_file
        bne @debut
        rts
@debut: sec
        sbc #1
        asl a
        tay
        lda #0
        sta fx_file
        lda son_effets,y
        sta ptr
        lda son_effets+1,y
        sta ptr+1
        ldy #0
        sty SID+14+4        ; gate baissé
        lda (ptr),y
        sta SID+14+5        ; AD
        iny
        lda (ptr),y
        sta SID+14+6        ; SR
        lda #$08
        sta SID+14+3        ; impulsion 50 %
        lda #2
        clc
        adc ptr
        sta fx_lo
        lda #0
        adc ptr+1
        sta fx_hi
        lda #1
        sta fx_actif
@image: lda fx_lo
        sta ptr
        lda fx_hi
        sta ptr+1
        ldy #0
        lda (ptr),y
        cmp #$FF
        beq @fin
        tax                 ; forme d'onde
        iny
        lda (ptr),y
        sta SID+14
        iny
        lda (ptr),y
        sta SID+14+1
        stx SID+14+4
        lda fx_lo
        clc
        adc #3
        sta fx_lo
        bcc @r
        inc fx_hi
@r:     rts
@fin:   lda #0
        sta fx_actif
        rts
