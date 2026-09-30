/* Project wrapper around the unmodified upstream LZSA C library.
   Upstream source and its zlib/CC0 notices are retained in the pinned checkout. */
#include "lib.h"

__declspec(dllexport) size_t zxv_compress(unsigned char *src, size_t length, unsigned char *dst, size_t capacity) {
    return lzsa_compress_inmem(src, dst, length, capacity,
        LZSA_FLAG_FAVOR_RATIO | LZSA_FLAG_RAW_BLOCK, 2, 2);
}

__declspec(dllexport) size_t zxv_decompress(unsigned char *src, size_t length, unsigned char *dst, size_t capacity) {
    int version = 2;
    return lzsa_decompress_inmem(src, dst, length, capacity, LZSA_FLAG_RAW_BLOCK, &version);
}
