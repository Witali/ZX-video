/* Shared z80-tester flag corrections. Include after defining board with
 * its z80_t cpu, CPU model and Q latch. The generator uses the same hooks. */
#include "../vendor/z80_tester/q_flags.h"

/* Q and repeat-stage corrections are the same bounded hooks as the source
 * z80-tester adapter. They cover undocumented flags; both execution modes use
 * them, including flags visible to an IRQ between repeating block iterations. */
static inline void board_update_q(board *b,uint16_t old) {
    uint16_t next=b->cpu.step;
    bool done=next==Z80_M1_T2 || next==Z80_NMI_STEP || next==Z80_INT_IM0_STEP ||
        next==Z80_INT_IM1_STEP || next==Z80_INT_IM2_STEP;
    if (done && old<sizeof(q_flags)) {
        uint8_t rule=q_flags[old];
        b->q=(rule==1 || (rule==2 && b->cpu.opcode<0x80)) ? b->cpu.f : 0;
    } else if ((done && old==Z80_DDFD_LDHLN_OVERLAPPED) || old==221 || old==253) b->q=0;
}
static inline void board_repeat_flags(z80_t *cpu,bool io) {
    uint8_t f=(cpu->f&~(Z80_YF|Z80_XF))|((cpu->pc>>8)&(Z80_YF|Z80_XF));
    if (io) {
        uint8_t parity=cpu->b;
        if (f&Z80_CF) {
            f&=~Z80_HF;
            if (cpu->dlatch&0x80) { parity=cpu->b-1;if (!(cpu->b&15)) f|=Z80_HF; }
            else { parity=cpu->b+1;if ((cpu->b&15)==15) f|=Z80_HF; }
        }
        f^=(_z80_szp_flags[parity&7]&Z80_PF)^Z80_PF;
    }
    cpu->f=f;
}
static inline uint64_t board_tick_core(board *b, uint64_t pins) {
    uint16_t old=b->cpu.step;
    uint8_t old_f=b->cpu.f,old_a=b->cpu.a,old_q=b->q;
    pins=z80_tick(&b->cpu,pins);
    switch (old) {
        case 1515:case 1528:case 1567:case 1580:board_repeat_flags(&b->cpu,false);break;
        case 1541:case 1554:case 1593:case 1606:board_repeat_flags(&b->cpu,true);break;
    }
    if (old==1392 && b->model) Z80_SET_DATA(pins,255);
    if (old==55 || old==63) b->cpu.f=(b->cpu.f&~(Z80_YF|Z80_XF))|(((old_q^old_f)|old_a)&(Z80_YF|Z80_XF));
    uint16_t next=b->cpu.step;
    bool accepted=next==Z80_INT_IM0_STEP || next==Z80_INT_IM1_STEP || next==Z80_INT_IM2_STEP;
    if (!b->model && (old==1282 || old==1311) && accepted) b->cpu.f&=~Z80_PF;
    board_update_q(b,old);
    return pins;
}
