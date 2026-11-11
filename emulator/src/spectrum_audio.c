/* The web player's single AY-3-8910 with ABC stereo and the ULA beeper.
 * The Z80 clock determines when an output sample observes a port write. */
#include "spectrum_audio.h"
#include "../vendor/ayumi/ayumi.h"
#include <stdbool.h>
#include <stddef.h>

enum { SAMPLE_HZ = 44100, CPU_HZ = 70908 * 50, AY_HZ = 1773400, BLOCK = 512 };

__attribute__((import_module("spectrum"), import_name("audio_block")))
void host_audio_block(const float *left, const float *right, unsigned count, double end_time);

static struct {
    struct ayumi chip;
    uint8_t registers[16], selected;
    bool beeper;
    uint64_t origin, rendered;
    float left[BLOCK], right[BLOCK];
} sound;

/* Freestanding wasm32 support for Ayumi's FIR history and pan configuration. */
void *memcpy(void *destination, const void *source, size_t count) {
    unsigned char *dst = destination;
    const unsigned char *src = source;
    for (size_t i = 0; i < count; ++i) dst[i] = src[i];
    return destination;
}

double sqrt(double value) { return __builtin_sqrt(value); }

void spectrum_audio_reset(uint64_t time) {
    ayumi_configure(&sound.chip, 0, AY_HZ, SAMPLE_HZ);
    ayumi_set_pan(&sound.chip, 0, .1, 0);
    ayumi_set_pan(&sound.chip, 1, .5, 0);
    ayumi_set_pan(&sound.chip, 2, .9, 0);
    ayumi_set_noise(&sound.chip, 0);
    ayumi_set_envelope_shape(&sound.chip, 0);
    for (unsigned i = 0; i < sizeof(sound.registers); ++i) sound.registers[i] = 0;
    sound.selected = 0;
    sound.beeper = false;
    sound.origin = time;
    sound.rendered = 0;
}

void spectrum_audio_advance(uint64_t time) {
    if (time < sound.origin) return;
    // Integer sample phase. Sample n is due at ceil(n * CPU_HZ / SAMPLE_HZ).
    const uint64_t target = (time - sound.origin) * SAMPLE_HZ / CPU_HZ;
    const double beeper = sound.beeper ? .35 : 0;
    while (sound.rendered < target) {
        const unsigned offset = sound.rendered % BLOCK;
        const unsigned available = BLOCK - offset;
        const uint64_t due = target - sound.rendered;
        const unsigned count = due < available ? (unsigned)due : available;
        for (unsigned i = offset; i < offset + count; ++i) {
            ayumi_process(&sound.chip);
            ayumi_remove_dc(&sound.chip);
            sound.left[i] = (float)(sound.chip.left * .7 + beeper);
            sound.right[i] = (float)(sound.chip.right * .7 + beeper);
        }
        sound.rendered += count;
        if (count == available) {
            const uint64_t end = sound.origin + (sound.rendered * CPU_HZ + SAMPLE_HZ - 1) / SAMPLE_HZ;
            host_audio_block(sound.left, sound.right, BLOCK, (double)end);
        }
    }
}

static void set_register(unsigned index, uint8_t value) {
    static const uint8_t masks[] = {
        255, 15, 255, 15, 255, 15, 31, 255, 31, 31, 31, 255, 255, 15, 255, 255
    };
    uint8_t *registers = sound.registers;
    struct ayumi *chip = &sound.chip;
    registers[index] = value & masks[index];
    if (index < 6) {
        const unsigned low = index & ~1u;
        ayumi_set_tone(chip, index >> 1, registers[low] | (registers[low + 1] << 8));
    } else if (index == 6) {
        ayumi_set_noise(chip, value);
    } else if (index == 7) {
        for (int channel = 0; channel < 3; ++channel) {
            ayumi_set_mixer(chip, channel, value >> channel, value >> (channel + 3),
                            chip->channels[channel].e_on);
        }
    } else if (index < 11) {
        const int channel = index - 8;
        ayumi_set_volume(chip, channel, value);
        chip->channels[channel].e_on = (value >> 4) & 1;
    } else if (index < 13) {
        ayumi_set_envelope(chip, registers[11] | (registers[12] << 8));
    } else if (index == 13) {
        ayumi_set_envelope_shape(chip, value);
    }
}

void spectrum_audio_out(uint16_t port, uint8_t value, uint64_t time) {
    const unsigned ay_port = port & 0xe002;
    const bool ay_data = ay_port == 0xa000;
    const bool level = (value & 16) != 0;
    const bool beeper_change = !(port & 1) && level != sound.beeper;
    // A sample at the same T as a CPU strobe sees the new value. Keep it
    // pending until all writes at this T are applied, including even aliases
    // that update the AY and beeper together.
    if (time && (beeper_change || (ay_data && sound.selected < 14)))
        spectrum_audio_advance(time - 1);
    if (beeper_change) sound.beeper = level;
    if (ay_data) set_register(sound.selected, value);
    if (ay_port == 0xe000 && value < 16) sound.selected = value;
}

uint8_t spectrum_audio_in(uint16_t port) {
    return (port & 0xe002) == 0xe000 ? sound.registers[sound.selected] : 255;
}
