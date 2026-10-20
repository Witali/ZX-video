/* Reusable CPU adapter. The pinned original z80.h is unmodified; generated
 * slices retain its operations/timing. No GUI, audio, disk or Spectrum bus is
 * built into this layer. See vendor/z80_tester/provenance.json. */
#include "codec_cpu.h"
#define CHIPS_IMPL
#include "../vendor/z80_tester/z80.h"
#include "../vendor/z80_tester/q_flags.h"
#include <stdlib.h>
#include <string.h>

struct codec_cpu {
    z80_t cpu;
    uint64_t pins,ticks,writes,waits,fused;
    uint8_t rom[65536],permissions[65536],watch[65536],model,q;
    codec_cpu_bus bus;
    codec_cpu_before_t before;
    void *bus_context,*before_context;
    codec_cpu_guards guard;
    uint32_t guarded,cursor,high,lowest,error,error_address,error_value;
    uint64_t *branch_no,*branch_yes;
};
typedef codec_cpu board; /* Name used by derived generated slices. */

static uint64_t cpu_time(codec_cpu *b) { return b->ticks ? b->ticks-1 : 0; }
static void fail(codec_cpu *b,uint32_t error,uint16_t at,uint8_t value) {
    if (!b->error) { b->error=error;b->error_address=at;b->error_value=value; }
}
static uint8_t codec_flat_read(codec_cpu *b,uint16_t at) {
    if (b->guarded && !(b->permissions[at]&1)) {
        if (at>=b->guard.source && at<b->guard.source+b->guard.input_bytes) {
            if (at==b->cursor) ++b->cursor;
            else if (at+1!=b->cursor) fail(b,1,at,b->rom[at]);
        } else if (at<b->guard.output || at>=b->high) fail(b,2,at,b->rom[at]);
    }
    return b->rom[at];
}
static void codec_flat_write(codec_cpu *b,uint16_t at,uint8_t value) {
    if (b->guarded) {
        if (at>=b->guard.output && at<b->guard.output+b->guard.output_bytes) {
            if (at!=b->high || value!=b->guard.expected_output[at-b->guard.output]) fail(b,3,at,value);
            ++b->high;
        } else if (b->permissions[at]&2) {
            /* One installed mutable offset operand; count inside code once. */
        } else if (at>=b->guard.caller_stack-64 && at<b->guard.caller_stack) {
            if (at<b->lowest) b->lowest=at;
        } else fail(b,4,at,value);
    }
    b->rom[at]=value;
}
#define BOARD_MEMORY_WRITE(b,a,v) codec_flat_write(b,a,v)
#define BOARD_INPUT(b,pins) 255
static void board_emit(board *b,uint64_t at,uint16_t port,uint8_t value) {
    (void)at;(void)port;(void)value;(void)b; /* Flat-bus open port; external bus owns I/O. */
}
/* Q and repeat-stage corrections are the same bounded hooks as the source
 * z80-tester adapter. They cover undocumented flags; both execution modes use
 * them, including flags visible to an IRQ between repeating block iterations. */
static void board_update_q(board *b,uint16_t old) {
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
static void board_finish_slice(board *b,uint64_t pins,uint32_t elapsed,uint16_t old) {
    board_update_q(b,old);b->cpu.pins=pins;
    if ((pins&(Z80_MREQ|Z80_RD))==(Z80_MREQ|Z80_RD)) Z80_SET_DATA(pins,codec_flat_read(b,Z80_GET_ADDR(pins)));
    b->pins=pins;b->ticks+=elapsed;
}
#include "../vendor/z80_tester/fast_slices.h"

CODEC_CPU_API uint32_t codec_cpu_abi_version(void) { return 2; }
CODEC_CPU_API codec_cpu *codec_cpu_create(void) {
    codec_cpu *b=calloc(1,sizeof(*b));
    if (b) { memset(b->rom,0xa5,65536);b->pins=z80_init(&b->cpu); }
    return b;
}
CODEC_CPU_API void codec_cpu_destroy(codec_cpu *b) {
    if (b) { free(b->branch_no);free(b->branch_yes);free(b); }
}
CODEC_CPU_API uint8_t *codec_cpu_memory(codec_cpu *b) { return b->rom; }
CODEC_CPU_API uint64_t codec_cpu_pins(codec_cpu *b) { return b->pins; }
CODEC_CPU_API void codec_cpu_set_bus(codec_cpu *b,codec_cpu_bus bus,void *context) {
    b->bus=bus;b->bus_context=context;
    if (bus) b->guarded=0; /* Flat guards cannot observe external banked memory. */
}
CODEC_CPU_API void codec_cpu_set_before_t(codec_cpu *b,codec_cpu_before_t hook,void *context) {
    b->before=hook;b->before_context=context;
}
CODEC_CPU_API void codec_cpu_set_lines(codec_cpu *b,uint64_t mask,uint64_t value) {
    uint64_t allowed=Z80_INT|Z80_NMI|Z80_WAIT;
    mask&=allowed;b->pins=(b->pins&~mask)|(value&mask);
}
CODEC_CPU_API void codec_cpu_get_phase(codec_cpu *b,codec_cpu_phase *v) {
    v->cpu_tstates=cpu_time(b);v->wait_tstates=b->waits;v->pins=b->pins;
    v->step=b->cpu.step;v->pc=b->cpu.pc;v->bc=b->cpu.bc;v->de=b->cpu.de;
    v->hl=b->cpu.hl;v->sp=b->cpu.sp;v->addr=b->cpu.addr;v->wz=b->cpu.wz;v->opcode=b->cpu.opcode;
    v->i=b->cpu.i;v->r=b->cpu.r;v->af=b->cpu.af;
}
CODEC_CPU_API uint64_t codec_cpu_tick(codec_cpu *b,uint64_t pins) {
    uint64_t previous=pins;
    if (b->before && b->ticks) {
        codec_cpu_phase phase;codec_cpu_get_phase(b,&phase);
        b->waits+=b->before(b->before_context,&phase,&pins);
    }
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
    board_update_q(b,old);++b->ticks;
    if (b->bus) pins=b->bus(b->bus_context,pins,cpu_time(b)+b->waits);
    else if (pins&Z80_MREQ) {
        if (pins&Z80_RD) { Z80_SET_DATA(pins,codec_flat_read(b,Z80_GET_ADDR(pins))); }
        else if ((pins&Z80_WR) && !(previous&Z80_WR)) {
            ++b->writes;codec_flat_write(b,Z80_GET_ADDR(pins),Z80_GET_DATA(pins));
        }
    } else if ((pins&Z80_IORQ) && (pins&(Z80_M1|Z80_RD))) Z80_SET_DATA(pins,255);
    b->pins=pins;return pins;
}
CODEC_CPU_API uint32_t codec_cpu_set_registers(codec_cpu *b,const codec_cpu_registers *v) {
    if (!v || v->halt || v->q>255) { b->error=5;return 0; }
    b->pins=z80_reset(&b->cpu);b->ticks=b->writes=b->waits=b->fused=0;b->q=0;
    b->error=b->error_address=b->error_value=0;
    b->cpu.af=v->af;b->cpu.bc=v->bc;b->cpu.de=v->de;b->cpu.hl=v->hl;
    b->cpu.sp=v->sp;b->cpu.ix=v->ix;b->cpu.iy=v->iy;
    b->cpu.af2=v->af2;b->cpu.bc2=v->bc2;b->cpu.de2=v->de2;b->cpu.hl2=v->hl2;
    b->cpu.wz=v->wz;b->cpu.i=v->i;b->cpu.r=v->r;
    b->cpu.iff1=!!v->iff1;b->cpu.iff2=!!v->iff2;b->cpu.im=v->im;
    b->pins=z80_prefetch(&b->cpu,(uint16_t)v->pc);
    codec_cpu_tick(b,b->pins);b->q=v->q; /* Initial observed fetch has time 0. */
    return 1;
}
CODEC_CPU_API void codec_cpu_get_registers(codec_cpu *b,codec_cpu_registers *v) {
    v->pc=z80_opdone(&b->cpu) ? (uint16_t)(b->cpu.pc-1) : b->cpu.pc;
    v->af=b->cpu.af;v->bc=b->cpu.bc;v->de=b->cpu.de;v->hl=b->cpu.hl;
    v->sp=b->cpu.sp;v->ix=b->cpu.ix;v->iy=b->cpu.iy;
    v->af2=b->cpu.af2;v->bc2=b->cpu.bc2;v->de2=b->cpu.de2;v->hl2=b->cpu.hl2;
    v->wz=b->cpu.wz;v->i=b->cpu.i;v->r=b->cpu.r;
    v->iff1=b->cpu.iff1;v->iff2=b->cpu.iff2;v->im=b->cpu.im;
    v->halt=!!(b->pins&Z80_HALT);v->q=b->q;
}
CODEC_CPU_API uint32_t codec_cpu_set_guards(codec_cpu *b,const codec_cpu_guards *g,const uint8_t *permissions) {
    if (!g || !permissions || b->bus || g->source>65535 || g->input_bytes>65536-g->source ||
        g->output>65535 || g->output_bytes>65536-g->output || g->caller_stack<64 || g->caller_stack>65535 ||
        (g->output_bytes && !g->expected_output)) return 0;
    b->guard=*g;memcpy(b->permissions,permissions,65536);b->guarded=1;
    b->cursor=g->source;b->high=g->output;b->lowest=g->caller_stack-2;
    b->error=b->error_address=b->error_value=0;return 1;
}
CODEC_CPU_API void codec_cpu_disable_guards(codec_cpu *b) { b->guarded=0; }
CODEC_CPU_API void codec_cpu_get_status(codec_cpu *b,codec_cpu_status *v) {
    v->cpu_tstates=cpu_time(b);v->wait_tstates=b->waits;v->error=b->error;
    v->error_address=b->error_address;v->error_value=b->error_value;
    v->input_cursor=b->cursor;v->output_cursor=b->high;
    v->stack_bytes=b->guarded ? b->guard.caller_stack-b->lowest : 0;v->memory_writes=b->writes;
}
CODEC_CPU_API void codec_cpu_watch_branch(codec_cpu *b,uint32_t at,uint32_t enabled) {
    if (at>65535) return;
    if (enabled && !b->branch_no) {
        b->branch_no=calloc(65536,sizeof(uint64_t));b->branch_yes=calloc(65536,sizeof(uint64_t));
        if (!b->branch_no || !b->branch_yes) { free(b->branch_no);free(b->branch_yes);b->branch_no=b->branch_yes=NULL;return; }
    }
    b->watch[at]=!!enabled;
}
CODEC_CPU_API void codec_cpu_branch_counts(codec_cpu *b,uint32_t at,uint64_t *no,uint64_t *yes) {
    *no=(at<65536 && b->branch_no) ? b->branch_no[at] : 0;
    *yes=(at<65536 && b->branch_yes) ? b->branch_yes[at] : 0;
}
static void observe(codec_cpu *b) {
    if (!b->bus && z80_opdone(&b->cpu)) {
        uint16_t at=b->cpu.pc-1;
        if (b->watch[at]) {
            uint8_t op=b->rom[at],index;
            if ((op&0xc7)==0xc2 && op<=0xda) index=(op>>3)&3;
            else if (op==0x20 || op==0x28 || op==0x30 || op==0x38) index=(op-0x20)>>3;
            else return;
            bool taken=index<2 ? !!(b->cpu.f&Z80_ZF) : !!(b->cpu.f&Z80_CF);
            if (!(index&1)) taken=!taken;
            if (taken) ++b->branch_yes[at];else ++b->branch_no[at];
        }
    }
}
static void advance(codec_cpu *b,uint64_t remaining,uint32_t fast) {
    observe(b);
    if (fast && !b->bus && !b->before && remaining>=32 && !b->cpu.int_bits &&
        !(b->pins&(Z80_INT|Z80_NMI|Z80_WAIT)) &&
        (b->cpu.step<Z80_INT_IM0_STEP || b->cpu.step>=Z80_DDFD_M1_T2)) {
        ++b->fused;board_fast_slice(b);
    } else codec_cpu_tick(b,b->pins);
}
CODEC_CPU_API uint64_t codec_cpu_fused_slices(codec_cpu *b) { return b->fused; }
CODEC_CPU_API uint32_t codec_cpu_step_instruction(codec_cpu *b,uint64_t budget,uint32_t fast) {
    uint64_t start=cpu_time(b);
    do {
        if (b->error) return 2;
        uint64_t used=cpu_time(b)-start;
        if (used>=budget) return 1;
        advance(b,budget-used,fast);
    } while (!z80_opdone(&b->cpu));
    return b->error ? 2 : 0;
}
CODEC_CPU_API uint32_t codec_cpu_run_to_pc(codec_cpu *b,uint32_t stop,uint64_t budget,uint32_t fast) {
    uint64_t start=cpu_time(b);
    while (!b->error) {
        if (z80_opdone(&b->cpu) && (uint16_t)(b->cpu.pc-1)==stop) return 0;
        uint64_t used=cpu_time(b)-start;
        if (used>=budget) return 1;
        advance(b,budget-used,fast);
    }
    return 2;
}
