#ifndef SPECTRUM_AUDIO_H
#define SPECTRUM_AUDIO_H

#include <stdint.h>

/* Absolute Z80 T-states on the 70,908-T, 50-Hz Spectrum clock. */
void spectrum_audio_reset(uint64_t time);
void spectrum_audio_advance(uint64_t time);
void spectrum_audio_out(uint16_t port, uint8_t value, uint64_t time);
uint8_t spectrum_audio_in(uint16_t port);

#endif
