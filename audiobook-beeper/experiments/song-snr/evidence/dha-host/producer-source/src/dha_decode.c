#include "dha_internal.h"

/* Record a negative decoding status and return it to the caller. The decoder
   owns this sticky error field; only a new dha_decoder_init clears it. */
static int fail(dha_decoder *decoder, int status) {
    decoder->error = status;
    return status;
}

/* Read count MSB-first payload bits into the caller's unsigned value. A zero
   count is a valid ANS suffix and produces zero. Check the entire request
   before advancing the cursor, so truncation consumes no partial suffix and
   leaves *value untouched; the resulting error is sticky in decoder. */
static int read_bits(dha_decoder *decoder, unsigned count, unsigned *value) {
    unsigned result = 0, i;
    /* Subtract only after checking the cursor to avoid unsigned underflow. */
    if (decoder->bit_position > decoder->frame.payload_bits ||
        count > decoder->frame.payload_bits - decoder->bit_position)
        return fail(decoder, DHA_E_TRUNCATED);
    for (i = 0; i < count; ++i) {
        uint32_t bit = decoder->bit_position++;
        /* Byte zero starts with its most significant bit, regardless of the
           host's byte order. No read may cross frame.payload_bits. */
        result = (result << 1) | ((decoder->payload[bit >> 3] >> (7u - (bit & 7u))) & 1u);
    }
    *value = result;
    return DHA_OK;
}

/* Initialize caller-owned, allocation-free decoding state for one complete
   packet. frame_read validates its exact length, CRC and canonical padding
   before any payload is borrowed. The packet and immutable info/tables must
   remain alive and unchanged through the final sample. Reinitialization
   discards the previous frame/error; a failed initialization records its
   status in decoder when that pointer is valid. */
int dha_decoder_init(dha_decoder *decoder, const dha_stream_info *info,
                     const uint8_t *packet, size_t bytes) {
    int status;
    if (!decoder) return DHA_E_ARGUMENT;
    memset(decoder, 0, sizeof(*decoder));
    if (!info || !packet) return fail(decoder, DHA_E_ARGUMENT);
    status = dha_frame_read(info, packet, bytes, &decoder->frame);
    if (status != DHA_OK) return fail(decoder, status);
    /* These are borrowed pointers, not copies or allocations. Initial q,
       differences and ANS state are independently supplied by this packet. */
    decoder->info = info;
    decoder->payload = packet + DHA_FRAME_HEADER_BYTES;
    decoder->state = decoder->frame.initial;
    decoder->ans_state = decoder->frame.ans_state;
    return DHA_OK;
}

/* Decode one mono/channel sample into caller-owned pcm and return DHA_OK.
   DHA_DONE produces no sample, including when pcm is NULL after completion.
   Negative errors remain sticky, and pcm is written only on success. Finish
   every frame: strict history and exact terminal-bit checks include its last
   sample. Parsing may advance bit_position/gain before a later error, but q,
   differences and ANS state are not committed until that sample is valid. */
int dha_decoder_next(dha_decoder *decoder, int16_t *pcm) {
    static const int levels[5] = {0, 1, -1, 2, -2};
    int value, prediction, q, d1, d2, d3, status;
    unsigned packed, symbol, bits, base, suffix, gain;
    uint8_t next_state;
    if (!decoder) return DHA_E_ARGUMENT;
    /* Do not resume a partially parsed failing sample or overwrite the
       original error. The success count, rather than bit count, marks DONE. */
    if (decoder->error < 0) return decoder->error;
    if (!decoder->info || !decoder->payload) return fail(decoder, DHA_E_ARGUMENT);
    if (decoder->position >= decoder->frame.samples) return DHA_DONE;
    if (!pcm) return fail(decoder, DHA_E_ARGUMENT);
    if (decoder->frame.kind == DHA_FRAME_PCM16) {
        /* frame_read proved a two-byte word exists for every sample. Decode
           its sign explicitly so raw PCM16 is preserved on either endian host. */
        unsigned word = dha_get16(decoder->payload + 2u * decoder->position);
        value = word < 32768u ? (int)word : (int)word - 65536;
        decoder->bit_position += 16u;
    } else if (decoder->frame.kind == DHA_FRAME_DHA) {
        /* Every frame starts a gain block; a short final block still has its
           own five-bit G. Values zero and31 are not valid PC packet gains. */
        if ((decoder->position & 255u) == 0) {
            status = read_bits(decoder, 5, &gain);
            if (status != DHA_OK) return status;
            if (gain < 1 || gain > 30) return fail(decoder, DHA_E_FORMAT);
            decoder->gain = (uint8_t)gain;
        }
        packed = decoder->info->ans[2u * decoder->ans_state];
        symbol = packed >> 4;
        bits = packed & 15u;
        base = decoder->info->ans[2u * decoder->ans_state + 1u];
        /* Tables were validated at initialization and must remain immutable.
           Keep the local range guard before a shift or next-state conversion. */
        if (symbol > 4 || bits > 6 || base + (1u << bits) > 256u)
            return fail(decoder, DHA_E_FORMAT);
        status = read_bits(decoder, bits, &suffix);
        if (status != DHA_OK) return status;
        /* The full suffix exists before a new ANS state can be committed.
           This format adds base+suffix; base need not be suffix-aligned. */
        next_state = (uint8_t)(base + suffix);
        status = dha_predict(decoder->info, &decoder->state, &prediction);
        if (status != DHA_OK) return fail(decoder, status);
        q = prediction + levels[symbol] * decoder->gain;
        if (prediction < -256 || prediction > 254 || q < -256 || q > 254)
            return fail(decoder, DHA_E_PROFILE);
        /* Decode recursively from q and differences, independently of the
           encoder's candidate histories. Check the final update as well. */
        d1 = q - decoder->state.q;
        d2 = d1 - decoder->state.d1;
        d3 = d2 - decoder->state.d2;
        if (d1 < -128 || d1 > 127 || d2 < -128 || d2 > 127 || d3 < -128 || d3 > 127)
            return fail(decoder, DHA_E_PROFILE);
        /* Byte padding was checked by frame_read. Also reject a valid decoded
           prefix with leftover meaningful bits, or a nonzero final ANS state. */
        if (decoder->position + 1u == decoder->frame.samples &&
            (next_state != 0 || decoder->bit_position != decoder->frame.payload_bits))
            return fail(decoder, DHA_E_FORMAT);
        decoder->state.q = (int16_t)q;
        decoder->state.d1 = (int8_t)d1;
        decoder->state.d2 = (int8_t)d2;
        decoder->state.d3 = (int8_t)d3;
        decoder->ans_state = next_state;
        /* q+257 is positive over the canonical q range. Integer division thus
           implements the exact upward half-step R2R rounding, then maps the
           unsigned8 target to signed PCM16 with its low eight bits zero. */
        value = (((q + 257) / 2) - 128) * 256;
    } else {
        return fail(decoder, DHA_E_FORMAT);
    }
    /* Apply exact meaningful-bit exhaustion to both raw PCM and DHA. Position
       and the caller's output are committed only after this final check. */
    if (decoder->position + 1u == decoder->frame.samples &&
        decoder->bit_position != decoder->frame.payload_bits)
        return fail(decoder, DHA_E_FORMAT);
    ++decoder->position;
    *pcm = (int16_t)value;
    return DHA_OK;
}

/* Decode a whole packet without allocation, using two constant-size decoder
   states and one scratch sample. Capacity counts int16_t samples, not bytes.
   A non-NULL written is set to zero before validation; output and optional
   frame remain untouched on a decoding/capacity error. Keep packet and info
   immutable and separate from output during both passes. On success, publish
   the frame metadata and exact output sample count only after all samples. */
int dha_decode_frame(const dha_stream_info *info, const uint8_t *packet,
                     size_t bytes, int16_t *output, size_t capacity,
                     size_t *written, dha_frame_info *frame) {
    dha_decoder initial, check;
    int16_t sample;
    size_t i;
    int status;
    if (!written) return DHA_E_ARGUMENT;
    *written = 0;
    status = dha_decoder_init(&initial, info, packet, bytes);
    if (status != DHA_OK) return status;
    if (capacity < initial.frame.samples) return DHA_E_BUFFER;
    if (!output) return DHA_E_ARGUMENT;
    /* First finish validation with one scalar scratch value. A late terminal
       or state error must not leave partially decoded convenience output. */
    check = initial;
    for (i = 0; i < initial.frame.samples; ++i) {
        status = dha_decoder_next(&check, &sample);
        if (status != DHA_OK) return status;
    }
    /* The unchanged packet/tables now have a known-valid complete trajectory.
       Replaying the original state fills the caller's buffer transactionally
       without a temporary frame-sized allocation. */
    for (i = 0; i < initial.frame.samples; ++i) {
        status = dha_decoder_next(&initial, &output[i]);
        if (status != DHA_OK) return status;
    }
    if (frame) *frame = initial.frame;
    *written = i;
    return DHA_OK;
}

/* Advance one first-order PDM pulse from an unsigned8 PCM target. The caller
   owns state, initializes accumulator=0 once, and keeps it across frames and
   playlist loops. Return the carry as bit0/1, or zero for a NULL state. For
   native25k PCM and100k PDM, call four times with the same pcm8, scheduling
   those calls uniformly; this helper itself provides no clock or buffering. */
uint8_t dha_pdm_next(dha_pdm_state *state, uint8_t pcm8) {
    unsigned sum;
    if (!state) return 0;
    /* The sum fits nine bits. Retain its low byte as the continuous phase;
       the high bit is the density pulse, not a PCM sample's least-significant bit. */
    sum = (unsigned)state->accumulator + pcm8;
    state->accumulator = (uint8_t)sum;
    return (uint8_t)(sum >> 8);
}
