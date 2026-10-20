#ifndef CODEC_SPECTRUM128_H
#define CODEC_SPECTRUM128_H

/* Original headless Spectrum 128 (Ferranti 7C ULA) bus for codec tests.
 * This is not the +2A/+3 or Pentagon model. No ROM images are distributed.
 * The CPU adapter must supply accurate cycle phases; pins alone do not expose
 * floooh's internal/no-MREQ addresses or all memory WAIT sampling points.
 */
#include <stdint.h>

#if defined(_WIN32)
#define SPECTRUM128_API __declspec(dllexport)
#else
#define SPECTRUM128_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

enum {
    SPECTRUM128_BANK_BYTES = 16384,
    SPECTRUM128_FRAME_TSTATES = 70908,
    SPECTRUM128_LINE_TSTATES = 228,
    SPECTRUM128_FRAME_LINES = 311,
    SPECTRUM128_INT_TSTATES = 36,
    SPECTRUM128_CONTENTION_START = 14361,
    SPECTRUM128_SCREEN_LINES = 192,
    SPECTRUM128_SCREEN_TSTATES = 128,
    SPECTRUM128_CPU_HZ = 3546900
};

typedef struct spectrum128 spectrum128;

typedef struct spectrum128_state {
    uint64_t cpu_tstates;
    uint64_t ula_wait_tstates;
    uint64_t master_tstates;
    uint64_t frame_number;
    uint64_t memory_reads;
    uint64_t memory_writes;
    uint64_t ignored_rom_writes;
    uint64_t paging_writes;
    uint64_t ignored_paging_writes;
    uint64_t unmodeled_port_reads;
    uint64_t unmodeled_port_writes;
    uint32_t frame_tstate;
    uint32_t paging_latch;
    uint32_t paged_bank;
    uint32_t rom_bank;
    uint32_t screen_bank;
    uint32_t paging_locked;
    uint32_t contention_enabled;
    uint32_t int_active;
    uint32_t ula_last;
    uint64_t irq_acknowledgements;
} spectrum128_state;

SPECTRUM128_API uint32_t spectrum128_abi_version(void);
SPECTRUM128_API spectrum128 *spectrum128_create(int contention_enabled);
SPECTRUM128_API void spectrum128_destroy(spectrum128 *bus);
/* Reset paging, clocks and observer counters, retaining ROM/RAM contents.
 * The chosen contention mode survives reset; power-on RAM is initialized to 0.
 */
SPECTRUM128_API void spectrum128_reset(spectrum128 *bus);
SPECTRUM128_API void spectrum128_get_state(const spectrum128 *bus, spectrum128_state *state);
SPECTRUM128_API void spectrum128_set_contention(spectrum128 *bus, int enabled);
/* Set the initial master phase, resetting the CPU/wait accounting only.
 * This setup operation does not represent executed CPU time.
 */
SPECTRUM128_API int spectrum128_set_phase(spectrum128 *bus, uint32_t frame_tstate);
SPECTRUM128_API void spectrum128_advance(spectrum128 *bus, uint32_t cpu_tstates, uint32_t wait_tstates);
SPECTRUM128_API int spectrum128_int_active(const spectrum128 *bus);

/* Setup/debug operations: bounded physical loads and logical peek do not
 * advance clocks or count CPU bus traffic. ROM writes require load_rom.
 */
SPECTRUM128_API int spectrum128_load_ram(spectrum128 *bus, uint32_t bank, uint32_t offset,
                                      const uint8_t *data, uint32_t size);
SPECTRUM128_API int spectrum128_load_rom(spectrum128 *bus, uint32_t bank, uint32_t offset,
                                      const uint8_t *data, uint32_t size);
SPECTRUM128_API int spectrum128_copy_ram(const spectrum128 *bus, uint32_t bank, uint32_t offset,
                                      uint8_t *data, uint32_t size);
SPECTRUM128_API uint8_t spectrum128_peek(const spectrum128 *bus, uint16_t address);
/* Return RAM bank 0..7, or ROM identity 8/9, for a logical address. */
SPECTRUM128_API uint32_t spectrum128_mapping(const spectrum128 *bus, uint16_t address);
SPECTRUM128_API uint8_t spectrum128_read(spectrum128 *bus, uint16_t address);
SPECTRUM128_API void spectrum128_write(spectrum128 *bus, uint16_t address, uint8_t value);
/* Address decoding is A15=0 and A1=0, including even aliases. A matching
 * even OUT updates both the paging latch and ULA latch. Bit5 locks until reset.
 */
SPECTRUM128_API int spectrum128_port_write(spectrum128 *bus, uint16_t port, uint8_t value);
/* Unimplemented input devices/floating-bus reads return FF and increment an
 * explicit unsupported counter. This includes 7FFD IN/writeback quirks; callers
 * must not qualify a program using IN as full Spectrum I/O through this bus.
 */
SPECTRUM128_API uint8_t spectrum128_port_read(spectrum128 *bus, uint16_t port);

/* Pure delay queries: no clock or observer changes. The phase is the start
 * of the cycle, relative to the assertion of the frame INT line.
 */
SPECTRUM128_API uint32_t spectrum128_delay_at(const spectrum128 *bus, uint16_t address,
                                           uint64_t master_tstate);
SPECTRUM128_API uint32_t spectrum128_delay(const spectrum128 *bus, uint16_t address);
/* Explicit cycle helpers advance pure CPU and ULA wait counters separately.
 * mem_cycle tests contention once then advances the caller's base3/4T.
 * internal_cycles tests each one-T no-MREQ cycle independently. io_cycle
 * advances the complete four-T I/O cycle, with its C/N stages below.
 * These helpers are independently verified bus primitives; a CPU instruction
 * run is contention-qualified only after all of its phase/address hooks pass.
 */
SPECTRUM128_API uint32_t spectrum128_mem_cycle(spectrum128 *bus, uint16_t address,
                                            uint32_t cpu_tstates);
SPECTRUM128_API uint32_t spectrum128_internal_cycles(spectrum128 *bus, uint16_t address,
                                                  uint32_t cpu_tstates);
SPECTRUM128_API uint32_t spectrum128_io_cycle(spectrum128 *bus, uint16_t port);
SPECTRUM128_API uint32_t spectrum128_port_write_cycle(spectrum128 *bus, uint16_t port,
                                                   uint8_t value);
/* Native codec_cpu_bus-compatible pin service: data, OUT, frame INT and clock.
 * Initial observed prefetch has physical_tstate0. It never infers contention
 * from pins, even if the standalone delay helpers are enabled. Use this for
 * the explicit no-contention benchmark mode. Accurate contention additionally
 * needs a verified before-T cycle/address hook, which must advance this bus's
 * wait counter before returning the same delay to codec_cpu.
 */
SPECTRUM128_API uint64_t spectrum128_cpu_bus(void *context, uint64_t pins,
                                           uint64_t physical_tstate);

#ifdef __cplusplus
}
#endif
#endif
