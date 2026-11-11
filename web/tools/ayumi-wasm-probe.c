/* Standalone comparison with the pinned upstream Ayumi C implementation.
 * This harness is never linked into the player. */
#include <stddef.h>
#include "ayumi.h"

static struct ayumi chip;
static double stereo[512 * 2];

void *memset(void *dst, int value, size_t count) {
    unsigned char *out = dst;
    for (size_t i = 0; i < count; i++) out[i] = (unsigned char)value;
    return dst;
}

void *memcpy(void *dst, const void *src, size_t count) {
    unsigned char *out = dst;
    const unsigned char *in = src;
    for (size_t i = 0; i < count; i++) out[i] = in[i];
    return dst;
}

double sqrt(double value) { return __builtin_sqrt(value); }

__attribute__((export_name("reset"))) void reset(void) {
    ayumi_configure(&chip, 0, 1773400, 44100);
    for (int i = 0; i < 3; i++) {
        ayumi_set_pan(&chip, i, i == 0 ? .1 : i == 1 ? .5 : .9, 0);
        ayumi_set_tone(&chip, i, 65 + 120 * i);
        ayumi_set_volume(&chip, i, 12 - i);
        ayumi_set_mixer(&chip, i, 0, 0, i == 2);
    }
    ayumi_set_noise(&chip, 11);
    ayumi_set_envelope(&chip, 54);
    ayumi_set_envelope_shape(&chip, 14);
}

__attribute__((export_name("buffer"))) double *buffer(void) { return stereo; }

__attribute__((export_name("render"))) void render(int offset, int count) {
    for (int i = offset; i < offset + count; i++) {
        ayumi_process(&chip);
        ayumi_remove_dc(&chip);
        stereo[2 * i] = chip.left;
        stereo[2 * i + 1] = chip.right;
    }
}
