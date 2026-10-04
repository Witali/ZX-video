/* Speex narrowband mode 3 only. See LICENSE.speex and README.md. */
#ifndef ZX_SPEEX_DECODER_H
#define ZX_SPEEX_DECODER_H
#include <stdint.h>
typedef int16_t s16;
typedef int32_t s32;
typedef uint16_t u16;
typedef uint8_t u8;
#ifdef __SDCC
#define EXPORT
#else
#define EXPORT __declspec(dllexport)
#endif
EXPORT void zx_speex_reset(void);
EXPORT int zx_speex_decode(const u8 *packet, s16 *output);
EXPORT void zx_speex_filter(const s16 *input, s16 *output);
extern s16 zx_lpc[10];
extern s32 zx_memory[10];
#endif
