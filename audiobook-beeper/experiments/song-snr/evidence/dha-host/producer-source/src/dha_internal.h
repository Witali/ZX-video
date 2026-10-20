#ifndef DHA_INTERNAL_H
#define DHA_INTERNAL_H
#include "dha_codec.h"
#include <string.h>
/* Read 2 little-endian bytes without alignment or native-struct assumptions;
   callers have already checked that the byte range exists. */
uint16_t dha_get16(const uint8_t *p);
/* Read 4 checked little-endian bytes; no bounds checking occurs here. */
uint32_t dha_get32(const uint8_t *p);
/* Read 8 checked little-endian bytes by combining two 32-bit words. */
uint64_t dha_get64(const uint8_t *p);
/* Store v in 2 writable little-endian bytes, independent of host endianness. */
void dha_put16(uint8_t *p,uint16_t v);
/* Store v in 4 writable little-endian bytes; caller owns and bounds p. */
void dha_put32(uint8_t *p,uint32_t v);
/* Store v in 8 writable little-endian bytes using two 32-bit stores. */
void dha_put64(uint8_t *p,uint64_t v);
/* Extend an internal CRC32 register over bytes; initialize with UINT32_MAX
   and XOR the final result with UINT32_MAX only after the last chunk. */
uint32_t dha_crc_update(uint32_t crc,const uint8_t *p,size_t bytes);
/* Compute the four-table prediction without modifying state. Return
   DHA_E_PROFILE for an out-of-range q or prediction; info must be validated. */
int dha_predict(const dha_stream_info *info,const dha_predictor_state *state,int *prediction);
/* Check q and its three new differences, then atomically replace state.
   An invalid update returns DHA_E_PROFILE without changing the old state. */
int dha_advance(dha_predictor_state *state,int q);
/* Serialize a frame header and payload, append CRC and validate packet shape.
   Byte counts are bounded by DHA_MAX_FRAME_BYTES. Payload may overlap the
   output payload region (memmove); success sets *written, errors leave it0.
   This checks packet structure, not a complete predictive decode. */
int dha_write_packet(const dha_stream_info *info,const dha_frame_info *frame,
                     const uint8_t *payload,size_t payload_bytes,uint8_t *out,
                     size_t capacity,size_t *written);
#endif
