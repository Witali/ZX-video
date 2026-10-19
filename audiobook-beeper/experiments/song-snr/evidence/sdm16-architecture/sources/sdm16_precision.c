/* Host-only causal precision control. No Spectrum timing or player claim.
 * All modes use beta=0.5 and the original 449-T table generation weights.
 * A: 64 input bins plus packet-end q16/r2 state quantization.
 * B: full decoded PCM16 input, exactly the same packet-end state mapping.
 * C: full PCM16 and continuous double q/recent, without packet quantization.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static const int holds[16] = {36,28,28,31,24,26,22,46,22,26,22,30,31,27,34,16};
typedef struct { double peak_q, peak_recent; size_t q_clips, r_clips; } Stats;

static uint16_t packet(int16_t pcm, int mode, unsigned seed,
                       double *q, double *recent, unsigned *successor, Stats *stats) {
    unsigned input = (unsigned)((int)pcm + 32768);
    double x = mode == 0 ? (double)(input >> 10) / 64.0 : (double)input / 65536.0;
    uint16_t word = 0;
    if (mode != 2) {
        *q = ((int)(seed / 2) - 8) / 8.0;
        *recent = seed % 2 ? 0.25 : -0.25;
    }
    for (unsigned slot = 0; slot < 16; ++slot) {
        double weight = holds[slot] / (449.0 / 16.0);
        /* Preserve scalar operation order and the original zero-origin
         * epsilon. Strict compiler flags disable fused reassociation. */
        double u = x + *q / weight + 0.5 * *recent;
        unsigned bit = u >= 0.5 - 1e-12;
        *recent = u - bit;
        *q += weight * (x - bit);
        word = (uint16_t)((word << 1) | bit);
        if (fabs(*q) > stats->peak_q) stats->peak_q = fabs(*q);
        if (fabs(*recent) > stats->peak_recent) stats->peak_recent = fabs(*recent);
    }
    if (mode == 2) {
        *successor = 255; /* Continuous state has no 32-state table identifier. */
    } else {
        int qcode = (int)floor(*q * 8.0 + 8.5 + 1e-12);
        int rcode = (int)floor((*recent / 0.5 + 1.0) + 1e-12);
        if (qcode < 0 || qcode > 15) ++stats->q_clips;
        if (rcode < 0 || rcode > 1) ++stats->r_clips;
        if (qcode < 0) qcode = 0;
        if (qcode > 15) qcode = 15;
        if (rcode < 0) rcode = 0;
        if (rcode > 1) rcode = 1;
        *successor = (unsigned)(qcode * 2 + rcode);
    }
    return word;
}

static int fail(const char *message) { fprintf(stderr, "%s\n", message); return 2; }

int main(int argc, char **argv) {
    int cells = argc == 6 && strcmp(argv[1], "cells") == 0;
    int stream = argc == 6 && strcmp(argv[1], "stream") == 0;
    if (!cells && !stream) return fail("Need cells|stream MODE INPUT OUTPUT STATES");
    int mode = strcmp(argv[2], "a") == 0 ? 0 : strcmp(argv[2], "b") == 0 ? 1 : strcmp(argv[2], "c") == 0 ? 2 : -1;
    if (mode < 0 || (cells && mode == 2)) return fail("Invalid mode; cells supports only a/b");
    FILE *input = fopen(argv[3], "rb"), *output = fopen(argv[4], "wb"), *states = fopen(argv[5], "wb");
    if (!input || !output || !states) return fail("Cannot open independent input/output/state files");
    size_t count = 0; unsigned state = 16; double q = 0.0, recent = -0.25; Stats stats = {0};
    for (;;) {
        int low = fgetc(input);
        if (low == EOF) break;
        int high = fgetc(input);
        if (high == EOF) return fail("Truncated PCM16 input");
        int16_t pcm = (int16_t)((unsigned)low | ((unsigned)high << 8));
        if (cells) {
            int seed = fgetc(input);
            if (seed < 0 || seed >= 32) return fail("Invalid or missing cell seed");
            state = (unsigned)seed;
        }
        uint16_t word = packet(pcm, mode, state, &q, &recent, &state, &stats);
        if (!isfinite(q) || !isfinite(recent)) return fail("Nonfinite modulator state");
        if (fputc(word >> 8, output) == EOF || fputc(word & 255, output) == EOF || fputc(state, states) == EOF)
            return fail("Output write failed");
        ++count;
    }
    if (ferror(input) || fclose(input) || fclose(output) || fclose(states)) return fail("I/O completion failed");
    printf("{\"samples\":%zu,\"mode\":\"%s\",\"q_clip_events\":%zu,\"recent_clip_events\":%zu,\"peak_absolute_q\":%.17g,\"peak_absolute_recent\":%.17g,\"final_q\":%.17g,\"final_recent\":%.17g,\"final_state\":%u}\n",
        count, argv[2], stats.q_clips, stats.r_clips, stats.peak_q, stats.peak_recent, q, recent, state);
    return 0;
}
