/* Host-only adapter for the pinned libdragon LH5 encoder. */
#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#ifdef _MSC_VER
#define __attribute__(x)
#endif
#include "lzh5_compress_host.c"

int main(int argc, char **argv) {
    unsigned int crc, packed, decoded;
    if (argc != 3) return 2;
    FILE *in = fopen(argv[1], "rb"), *out = fopen(argv[2], "wb");
    if (!in || !out) return 3;
    fseek(in, 0, SEEK_END);
    long size = ftell(in);
    rewind(in);
    lzh5_init(LZHUFF5_METHOD_NUM);
    lzh5_encode(in, out, &crc, &packed, &decoded);
    int failed = ferror(in) || ferror(out) || unpackable || decoded != size;
    fclose(in);
    if (fclose(out)) failed = 1;
    if (failed) return 4;
    printf("%u %u %u\n", crc, packed, decoded);
    return 0;
}
