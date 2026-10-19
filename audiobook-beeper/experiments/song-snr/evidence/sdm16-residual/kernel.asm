; Full-input residual quantizer, standalone feasibility proof only.
; IX=u: exact biased signed IMA predictor in0..65535; it must remain unchanged.
; The self-modified immediate stores R in0..1023. HL,IY,A/F and SP are dead
; on entry after a hypothetical selector dispatch; no stack operations follow.
; BC port,D16,IX,alternate registers and AF' are preserved. Return IYL=q0..64,
; HL=Rnew,SP=IX, with only the two residual-immediate bytes changed in RAM.
; q=floor((u+R)/1024),Rnew=(u+R)mod1024. The17th carry is significant at
; positive fullscale: q64 is real and needs a65th level or an explicit clip.
; This PDM-prequantizer model differs from current modelA/B. No audio is scored.
 ORG 0x8000
residual: LD HL,0
 LD SP,IX
 ADD HL,SP
 ; Extract sum bits16..10 before AND destroys the addition's carry. RRCA's
 ; unwanted wrapped bit9 is removed by AND127; all paths take identical time.
 LD A,H
 RRA
 RRCA
 AND 127
 LD IYL,A
 ; Store the exact remainder for the next sample. This is self-modified data,
 ; not an ordinary stack or an input-dependent branch/paging operation.
 LD A,H
 AND 3
 LD H,A
 LD (residual+1),HL
complete: NOP
