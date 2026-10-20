/* Headless Spectrum128 bus, independently implemented from hardware facts.
 * Primary references inspected 2026-10-20:
 * https://raw.githubusercontent.com/fuse-emulator/fuse/master/machines/spec128.c
 *   fixed5/2 and paged RAM, ROM/screen selection, odd-bank contention, lock.
 * https://raw.githubusercontent.com/fuse-emulator/libspectrum/master/timings.c
 *   Ferranti7C: 228T*311=70908T,36T INT, first pixel14362T.
 * https://raw.githubusercontent.com/fuse-emulator/fuse/master/spectrum.c
 *   contention begins one T before the first pixel, 65432100 for128T/192lines.
 * https://raw.githubusercontent.com/fuse-emulator/fuse/master/peripherals/ula.c
 *   early I/O C:1/N:1; even late C:3; odd late C:1*3 or N:3.
 * https://raw.githubusercontent.com/speccytools/fuse/master/periph.c
 *   7FFD partial decode0x8002=0; OUT effect between early and late I/O stages.
 * https://spectrumforeveryone.com/wp-content/uploads/2017/11/ZX-Spectrum-128-Service-Manual.pdf
 *   pp6-7: paging bits, reset mapping and corrected physical contention banks.
 * No Fuse or libspectrum implementation code is incorporated here.
 * Scope excludes display/audio rendering, disk, keyboard/EAR and floating bus.
 */
#include "spectrum128.h"
#include "codec_cpu.h"
#include <stdlib.h>
#include <string.h>

struct spectrum128 {
    uint8_t ram[8][SPECTRUM128_BANK_BYTES];
    uint8_t rom[2][SPECTRUM128_BANK_BYTES];
    spectrum128_state state;
    uint64_t clock_origin, previous_pins;
};

static void update_clock(spectrum128 *bus) {
    bus->state.frame_tstate = (uint32_t)(bus->state.master_tstates % SPECTRUM128_FRAME_TSTATES);
    bus->state.frame_number = bus->state.master_tstates / SPECTRUM128_FRAME_TSTATES;
    bus->state.int_active = bus->state.frame_tstate < SPECTRUM128_INT_TSTATES;
}

SPECTRUM128_API uint32_t spectrum128_abi_version(void) {
    return 1;
}

SPECTRUM128_API spectrum128 *spectrum128_create(int contention_enabled) {
    spectrum128 *bus = (spectrum128 *)calloc(1, sizeof(*bus));
    if (bus) {
        memset(bus->rom, 255, sizeof(bus->rom));
        bus->state.contention_enabled = !!contention_enabled;
        spectrum128_reset(bus);
    }
    return bus;
}

SPECTRUM128_API void spectrum128_destroy(spectrum128 *bus) {
    free(bus);
}

SPECTRUM128_API void spectrum128_reset(spectrum128 *bus) {
    uint32_t contention = bus->state.contention_enabled;
    memset(&bus->state, 0, sizeof(bus->state));
    bus->state.contention_enabled = contention;
    bus->state.screen_bank = 5;
    bus->clock_origin = bus->previous_pins = 0;
    update_clock(bus);
}

SPECTRUM128_API void spectrum128_get_state(const spectrum128 *bus, spectrum128_state *state) {
    *state = bus->state;
}

SPECTRUM128_API void spectrum128_set_contention(spectrum128 *bus, int enabled) {
    bus->state.contention_enabled = !!enabled;
}

SPECTRUM128_API int spectrum128_set_phase(spectrum128 *bus, uint32_t phase) {
    if (phase >= SPECTRUM128_FRAME_TSTATES) return 0;
    bus->state.cpu_tstates = bus->state.ula_wait_tstates = 0;
    bus->state.master_tstates = phase;
    bus->clock_origin = phase;
    bus->previous_pins = 0;
    update_clock(bus);
    return 1;
}

SPECTRUM128_API void spectrum128_advance(spectrum128 *bus, uint32_t cpu_tstates, uint32_t wait_tstates) {
    bus->state.cpu_tstates += cpu_tstates;
    bus->state.ula_wait_tstates += wait_tstates;
    bus->state.master_tstates += (uint64_t)cpu_tstates + wait_tstates;
    update_clock(bus);
}

SPECTRUM128_API int spectrum128_int_active(const spectrum128 *bus) {
    return (int)bus->state.int_active;
}

static int valid_load(uint32_t bank, uint32_t offset, const void *data, uint32_t size, uint32_t banks) {
    return bank < banks && offset <= SPECTRUM128_BANK_BYTES &&
           size <= SPECTRUM128_BANK_BYTES-offset && (data || !size);
}

SPECTRUM128_API int spectrum128_load_ram(spectrum128 *bus, uint32_t bank, uint32_t offset,
                                      const uint8_t *data, uint32_t size) {
    if (!valid_load(bank, offset, data, size, 8)) return 0;
    if (size) memcpy(bus->ram[bank]+offset, data, size);
    return 1;
}

SPECTRUM128_API int spectrum128_load_rom(spectrum128 *bus, uint32_t bank, uint32_t offset,
                                      const uint8_t *data, uint32_t size) {
    if (!valid_load(bank, offset, data, size, 2)) return 0;
    if (size) memcpy(bus->rom[bank]+offset, data, size);
    return 1;
}

SPECTRUM128_API int spectrum128_copy_ram(const spectrum128 *bus, uint32_t bank, uint32_t offset,
                                      uint8_t *data, uint32_t size) {
    if (!valid_load(bank, offset, data, size, 8)) return 0;
    if (size) memcpy(data, bus->ram[bank]+offset, size);
    return 1;
}

SPECTRUM128_API uint32_t spectrum128_mapping(const spectrum128 *bus, uint16_t address) {
    switch (address >> 14) {
        case 0: return 8+bus->state.rom_bank;
        case 1: return 5;
        case 2: return 2;
        default: return bus->state.paged_bank;
    }
}

SPECTRUM128_API uint8_t spectrum128_peek(const spectrum128 *bus, uint16_t address) {
    uint32_t bank = spectrum128_mapping(bus, address);
    uint32_t offset = address & 0x3fff;
    return bank < 8 ? bus->ram[bank][offset] : bus->rom[bank-8][offset];
}

SPECTRUM128_API uint8_t spectrum128_read(spectrum128 *bus, uint16_t address) {
    ++bus->state.memory_reads;
    return spectrum128_peek(bus, address);
}

SPECTRUM128_API void spectrum128_write(spectrum128 *bus, uint16_t address, uint8_t value) {
    uint32_t bank = spectrum128_mapping(bus, address);
    ++bus->state.memory_writes;
    if (bank < 8) bus->ram[bank][address & 0x3fff] = value;
    else ++bus->state.ignored_rom_writes;
}

SPECTRUM128_API int spectrum128_port_write(spectrum128 *bus, uint16_t port, uint8_t value) {
    int handled = 0;
    if (!(port & 1)) {
        bus->state.ula_last = value;
        handled = 1;
    }
    if (!(port & 0x8002)) {
        if (bus->state.paging_locked) {
            ++bus->state.ignored_paging_writes;
        } else {
            bus->state.paging_latch = value;
            bus->state.paged_bank = value & 7;
            bus->state.screen_bank = value & 8 ? 7 : 5;
            bus->state.rom_bank = (value >> 4) & 1;
            bus->state.paging_locked = !!(value & 0x20);
            ++bus->state.paging_writes;
        }
        handled = 1;
    }
    if (!handled) ++bus->state.unmodeled_port_writes;
    return handled;
}

SPECTRUM128_API uint8_t spectrum128_port_read(spectrum128 *bus, uint16_t port) {
    (void)port;
    ++bus->state.unmodeled_port_reads;
    return 255;
}

static int contended(const spectrum128 *bus, uint16_t address) {
    uint32_t bank = spectrum128_mapping(bus, address);
    return bank < 8 && (bank & 1);
}

SPECTRUM128_API uint32_t spectrum128_delay_at(const spectrum128 *bus, uint16_t address, uint64_t time) {
    uint32_t phase, offset, column;
    if (!bus->state.contention_enabled || !contended(bus, address)) return 0;
    phase = (uint32_t)(time % SPECTRUM128_FRAME_TSTATES);
    if (phase < SPECTRUM128_CONTENTION_START) return 0;
    offset = phase-SPECTRUM128_CONTENTION_START;
    if (offset/SPECTRUM128_LINE_TSTATES >= SPECTRUM128_SCREEN_LINES) return 0;
    column = offset % SPECTRUM128_LINE_TSTATES;
    if (column >= SPECTRUM128_SCREEN_TSTATES) return 0;
    column &= 7;
    return column < 6 ? 6-column : 0;
}

SPECTRUM128_API uint32_t spectrum128_delay(const spectrum128 *bus, uint16_t address) {
    return spectrum128_delay_at(bus, address, bus->state.master_tstates);
}

SPECTRUM128_API uint32_t spectrum128_mem_cycle(spectrum128 *bus, uint16_t address, uint32_t cpu_tstates) {
    uint32_t delay = spectrum128_delay(bus, address);
    spectrum128_advance(bus, cpu_tstates, delay);
    return delay;
}

SPECTRUM128_API uint32_t spectrum128_internal_cycles(spectrum128 *bus, uint16_t address, uint32_t cpu_tstates) {
    uint32_t n, total = 0;
    for (n = 0; n < cpu_tstates; ++n) total += spectrum128_mem_cycle(bus, address, 1);
    return total;
}

/* Each stage tests the current master phase after any earlier ULA hold.
 * I/O is C:1/N:1 followed by even C:3, or odd C:1,C:1,C:1/N:3.
 * Physical bank identity, rather than simply address C000+, controls C.
 */
static uint32_t io_early(spectrum128 *bus, uint16_t port) {
    return spectrum128_mem_cycle(bus, port, 1);
}

static uint32_t io_late(spectrum128 *bus, uint16_t port) {
    if (!(port & 1)) {
        /* Every even port is supplied by the ULA, independent of its high byte. */
        return spectrum128_mem_cycle(bus, 0x4000, 3);
    }
    return spectrum128_internal_cycles(bus, port, 3);
}

SPECTRUM128_API uint32_t spectrum128_io_cycle(spectrum128 *bus, uint16_t port) {
    uint32_t delay = io_early(bus, port);
    return delay + io_late(bus, port);
}

SPECTRUM128_API uint32_t spectrum128_port_write_cycle(spectrum128 *bus, uint16_t port, uint8_t value) {
    uint32_t delay = io_early(bus, port);
    spectrum128_port_write(bus, port, value);
    return delay + io_late(bus, port);
}

SPECTRUM128_API uint64_t spectrum128_cpu_bus(void *context, uint64_t pins, uint64_t physical_tstate) {
    spectrum128 *bus = (spectrum128 *)context;
    uint16_t address = (uint16_t)pins;
    uint64_t previous = bus->previous_pins;
    /* The CPU adapter's initial prefetch is observed at0, without charging
     * one extra T. Subsequent physical time includes explicit before-hook holds.
     */
    bus->state.master_tstates = bus->clock_origin + physical_tstate;
    bus->state.cpu_tstates = physical_tstate-bus->state.ula_wait_tstates;
    update_clock(bus);
    if (pins & CODEC_PIN_MREQ) {
        if (pins & CODEC_PIN_RD) pins = CODEC_PIN_DATA(pins, spectrum128_read(bus, address));
        else if ((pins & CODEC_PIN_WR) && !(previous & CODEC_PIN_WR))
            spectrum128_write(bus, address, (uint8_t)(pins >> 16));
    } else if (pins & CODEC_PIN_IORQ) {
        if (pins & CODEC_PIN_M1) {
            if ((previous & (CODEC_PIN_IORQ | CODEC_PIN_M1)) != (CODEC_PIN_IORQ | CODEC_PIN_M1))
                ++bus->state.irq_acknowledgements;
            pins = CODEC_PIN_DATA(pins, 255);
        }
        else if (pins & CODEC_PIN_RD) pins = CODEC_PIN_DATA(pins, spectrum128_port_read(bus, address));
        else if ((pins & CODEC_PIN_WR) && !(previous & CODEC_PIN_WR))
            spectrum128_port_write(bus, address, (uint8_t)(pins >> 16));
    }
    bus->previous_pins = pins;
    return bus->state.int_active ? pins | CODEC_PIN_INT : pins & ~CODEC_PIN_INT;
}
