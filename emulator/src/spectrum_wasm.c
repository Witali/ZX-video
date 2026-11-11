/* Browser Spectrum 128 bus for the pinned z80-tester CPU. The host owns
 * clocked devices; RAM, ROM and Z80 machine cycles stay in this module. */
#define CHIPS_IMPL
#include "../vendor/z80_tester/z80.h"

#define EXPORT(name) __attribute__((export_name(#name)))
#define IMPORT(name) __attribute__((import_module("spectrum"), import_name(#name)))

IMPORT(in_port) uint8_t host_in(uint16_t port, uint32_t time);
IMPORT(out_port) void host_out(uint16_t port, uint8_t value, uint32_t time);
IMPORT(trdos) void host_trdos(bool enabled);
IMPORT(dispatch) uint32_t host_dispatch(uint32_t time);

enum { PAGE_SIZE = 0x4000, SCREEN_SIZE = 0x1b00 };
enum { ROM_48, ROM_TURBO, ROM_128, ROM_TRDOS };

typedef struct {
    z80_t cpu;
    uint64_t pins;
    uint32_t ticks, deadline;
    uint8_t ram[8][PAGE_SIZE], rom[4][PAGE_SIZE];
    uint8_t *pages[4];
    uint8_t paging, model, q, screen_dirty, nmi_ticks;
    bool trdos, turbo, int_level;
} board;

static board machine;

#include "z80_flag_hooks.h"

/* Freestanding build. z80_reset only needs zeroing the small CPU struct. */
void *memset(void *data, int value, size_t bytes) {
    uint8_t *p = data;
    for (size_t i = 0; i < bytes; ++i) p[i] = (uint8_t)value;
    return data;
}

static inline void map_rom(board *b) {
    unsigned page = b->paging & 0x10 ? (b->turbo ? ROM_TURBO : ROM_48) : ROM_128;
    b->pages[0] = b->rom[b->trdos ? ROM_TRDOS : page];
}

EXPORT(page) void spectrum_page(uint8_t value) {
    machine.paging = value;
    machine.pages[3] = machine.ram[value & 7];
    map_rom(&machine);
}

static inline uint8_t memory_read(board *b, uint16_t address) {
    return b->pages[address >> 14][address & (PAGE_SIZE - 1)];
}

/* TR-DOS ROM overlays the selected 48K ROM on M1 at 3Dxx, and disappears
 * on an M1 in RAM. The Beta Disk controller sees the same latch change. */
static inline uint8_t pin_read(board *b, uint64_t pins) {
    uint16_t address = Z80_GET_ADDR(pins);
    if (pins & Z80_M1) {
        bool trdos = b->trdos ? address < PAGE_SIZE :
            (b->paging & 0x10) && (address >> 8) == 0x3d;
        if (trdos != b->trdos) {
            b->trdos = trdos;
            map_rom(b);
            host_trdos(trdos);
        }
    }
    return memory_read(b, address);
}

static inline void memory_write(board *b, uint16_t address, uint8_t value) {
    unsigned slot = address >> 14;
    if (!slot) return;
    unsigned offset = address & (PAGE_SIZE - 1);
    b->pages[slot][offset] = value;
    if (offset < SCREEN_SIZE) {
        if (slot == 1) b->screen_dirty |= 1;
        if (slot == 3 && (b->paging & 5) == 5)
            b->screen_dirty |= 1 << ((b->paging >> 1) & 1);
    }
}

static inline void board_emit(board *b, uint32_t time, uint16_t port, uint8_t value) {
    (void)b;
    host_out(port, value, time);
}

static inline void board_finish_slice(board *b, uint64_t pins, uint32_t elapsed, uint16_t old) {
    board_update_q(b, old);
    b->cpu.pins = pins;
    b->ticks += elapsed;
    if ((pins & (Z80_MREQ | Z80_RD)) == (Z80_MREQ | Z80_RD)) {
        Z80_SET_DATA(pins, pin_read(b, pins));
    }
    b->pins = pins;
}

#include "spectrum_slices.h"

/* Original single-T path for interrupts and for the last cycles before an
 * event. Port strobes commit at this T-state before subsequent CPU work. */
static inline void tick(board *b) {
    uint64_t previous = b->pins;
    uint64_t pins = previous & ~(Z80_INT | Z80_NMI);
    if (b->int_level) pins |= Z80_INT;
    if (b->nmi_ticks) { pins |= Z80_NMI; --b->nmi_ticks; }
    pins = board_tick_core(b, pins);
    ++b->ticks;
    if (pins & Z80_MREQ) {
        if (pins & Z80_RD) {
            Z80_SET_DATA(pins, pin_read(b, pins));
        } else if ((pins & Z80_WR) && !(previous & Z80_WR)) {
            memory_write(b, Z80_GET_ADDR(pins), Z80_GET_DATA(pins));
        }
    } else if (pins & Z80_IORQ) {
        if (pins & Z80_M1) {
            Z80_SET_DATA(pins, 255);
        } else if (pins & Z80_RD) {
            Z80_SET_DATA(pins, host_in(Z80_GET_ADDR(pins), b->ticks));
        } else if ((pins & Z80_WR) && !(previous & Z80_WR)) {
            host_out(Z80_GET_ADDR(pins), Z80_GET_DATA(pins), b->ticks);
        }
    }
    b->pins = pins;
}

EXPORT(reset) void spectrum_reset(unsigned mode) {
    board *b = &machine;
    b->pins = z80_reset(&b->cpu);
    b->q = b->nmi_ticks = b->int_level = false;
    b->trdos = mode == 2;
    b->turbo = mode == 3;
    b->pages[1] = b->ram[5];
    b->pages[2] = b->ram[2];
    b->screen_dirty = 3;
    spectrum_page(mode == 0 ? 0 : mode == 1 ? 0x30 : 0x10);
    host_trdos(b->trdos);
}

EXPORT(int_line) void spectrum_int(bool level) { machine.int_level = level; }
EXPORT(nmi) void spectrum_nmi(void) { machine.nmi_ticks = 8; }
EXPORT(rom_ptr) uint8_t *spectrum_rom(void) { return machine.rom[0]; }
EXPORT(read) uint8_t spectrum_read(uint16_t address) { return memory_read(&machine, address); }
EXPORT(write) void spectrum_write(uint16_t address, uint8_t value) { memory_write(&machine, address, value); }
EXPORT(ticks) uint32_t spectrum_ticks(void) { return machine.ticks; }
EXPORT(set_ticks) void spectrum_set_ticks(uint32_t ticks) { machine.ticks = ticks; }
EXPORT(pc) uint16_t spectrum_pc(void) { return machine.cpu.pc - z80_opdone(&machine.cpu); }

EXPORT(screen) uint8_t *spectrum_screen(unsigned bank) {
    unsigned bit = bank == 5 ? 1 : 2;
    if (!(machine.screen_dirty & bit)) return 0;
    machine.screen_dirty &= ~bit;
    return machine.ram[bank];
}

EXPORT(tighten_deadline) void spectrum_tighten_deadline(uint32_t deadline) {
    if (deadline < machine.deadline) machine.deadline = deadline;
}

/* A host wake uses relative T-states. Stop at every device deadline, even
 * inside an instruction. A fused slice ends at any I/O strobe, allowing the
 * callback to tighten the limit before any further emulated time elapses. */
EXPORT(run) uint32_t spectrum_run(uint32_t limit, bool fast) {
    board *b = &machine;
    b->deadline = b->ticks;
    while (b->ticks < limit) {
        if (b->ticks >= b->deadline) b->deadline = host_dispatch(b->ticks);
        uint32_t remaining = b->deadline - b->ticks;
        if (fast && remaining >= 32 && !b->int_level && !b->nmi_ticks && !b->cpu.int_bits &&
            (b->cpu.step < Z80_INT_IM0_STEP || b->cpu.step >= Z80_DDFD_M1_T2)) {
            board_fast_slice(b);
        } else {
            tick(b);
        }
    }
    return b->ticks;
}

EXPORT(step) void spectrum_step(void) {
    do { tick(&machine); } while (!z80_opdone(&machine.cpu));
}
