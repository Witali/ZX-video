/* Exact host mirror of the native seven-uniform-hold full-input carry kernel.
 * No floating point, clipping, table state, input gain, dither or order change.
 * One byte stores each seven chronological decisions, earliest in bit6.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    FILE *input, *words, *states;
    unsigned long parsed;
    uint32_t accumulator, initial;
    uint64_t samples = 0, ones = 0;
    int low, high, floor6;
    char *end = NULL;
    if (argc != 7 || (strcmp(argv[1], "full16") && strcmp(argv[1], "floor6"))) {
        fprintf(stderr, "usage: kernel full16|floor6 pcm16le words7u8 accum16le initial\n");
        return 2;
    }
    parsed = strtoul(argv[6], &end, 10);
    if (!end || *end || parsed > 65535UL) return 3;
    initial = accumulator = (uint32_t)parsed;
    floor6 = !strcmp(argv[1], "floor6");
    input = fopen(argv[2], "rb"); words = fopen(argv[3], "wb"); states = fopen(argv[4], "wb");
    if (!input || !words || !states) { fprintf(stderr, "file open failed\n"); return 4; }
    /* argv[5] is a reserved literal descriptor, protecting the binary contract
       from accidental command-line shifts while exposing the model explicitly. */
    if (strcmp(argv[5], "uniform7x64")) return 5;
    while ((low = fgetc(input)) != EOF) {
        uint32_t unsigned_pcm, word = 0;
        int slot;
        high = fgetc(input);
        if (high == EOF) { fprintf(stderr, "odd PCM16 input length\n"); return 6; }
        /* Flipping the sign bit biases the signed16 two's-complement value:
           -32768->0, zero->32768, +32767->65535. No half-LSB offset. */
        unsigned_pcm = ((uint32_t)low | ((uint32_t)high << 8)) ^ 0x8000U;
        if (floor6) unsigned_pcm &= 0xFC00U;
        for (slot = 0; slot < 7; ++slot) {
            uint32_t sum = accumulator + unsigned_pcm;
            uint32_t bit = sum >> 16;
            accumulator = sum & 0xFFFFU;
            word = (word << 1) | bit;
            ones += bit;
        }
        fputc((int)word, words);
        fputc((int)(accumulator & 255U), states);
        fputc((int)(accumulator >> 8), states);
        ++samples;
    }
    if (ferror(input) || ferror(words) || ferror(states) || !samples) return 7;
    fclose(input); fclose(words); fclose(states);
    printf("{\"samples\":%llu,\"decisions\":%llu,\"ones\":%llu,\"initial_accumulator\":%u,\"final_accumulator\":%u,\"mode\":\"%s\"}\n",
           (unsigned long long)samples, (unsigned long long)(7 * samples),
           (unsigned long long)ones, (unsigned)initial, (unsigned)accumulator, argv[1]);
    return 0;
}
