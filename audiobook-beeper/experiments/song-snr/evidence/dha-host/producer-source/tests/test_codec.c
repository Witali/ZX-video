#include "../include/dha_codec.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(condition) do { if (!(condition)) { \
    fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #condition); return 1; \
} } while (0)
#define CHECK_OK(expression) CHECK((expression) == DHA_OK)

static void test_put16(uint8_t *p, uint16_t value) {
    p[0] = (uint8_t)value; p[1] = (uint8_t)(value >> 8);
}

static void test_put32(uint8_t *p, uint32_t value) {
    unsigned i;
    for (i = 0; i < 4; ++i) p[i] = (uint8_t)(value >> (8u*i));
}

static uint32_t test_crc(uint32_t crc, const uint8_t *p, size_t bytes) {
    size_t i;
    unsigned bit;
    for (i = 0; i < bytes; ++i) {
        crc ^= p[i];
        for (bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ ((crc & 1u) ? UINT32_C(0xedb88320) : 0u);
    }
    return crc;
}

/* Independent wire fixture constructor; deliberately does not validate its
   fields, so malformed CRC-valid packets reach the public reader/decoder. */
static int test_write_packet(const dha_stream_info *info, const dha_frame_info *frame,
                              const uint8_t *payload, size_t bytes, uint8_t *output,
                              size_t capacity, size_t *written) {
    uint32_t crc;
    (void)info;
    *written = 0;
    if (bytes > capacity || DHA_FRAME_HEADER_BYTES > capacity-bytes) return DHA_E_BUFFER;
    memset(output, 0, DHA_FRAME_HEADER_BYTES);
    memcpy(output, "DHF1", 4);
    test_put32(output+4, (uint32_t)(DHA_FRAME_HEADER_BYTES+bytes));
    test_put32(output+8, frame->sequence);
    test_put16(output+12, frame->samples);
    output[14] = frame->channel; output[15] = frame->kind;
    test_put16(output+16, (uint16_t)frame->initial.q);
    output[18] = (uint8_t)frame->initial.d1;
    output[19] = (uint8_t)frame->initial.d2;
    output[20] = (uint8_t)frame->initial.d3;
    output[21] = frame->ans_state;
    test_put32(output+24, frame->payload_bits);
    memcpy(output+DHA_FRAME_HEADER_BYTES, payload, bytes);
    crc = test_crc(UINT32_MAX, output, 28);
    crc = test_crc(crc, payload, bytes) ^ UINT32_MAX;
    test_put32(output+28, crc);
    *written = DHA_FRAME_HEADER_BYTES+bytes;
    return DHA_OK;
}

static int flat_info(dha_stream_info *info, uint16_t channels) {
    int status = dha_stream_default(info, 25000, channels, 4096, DHA_UNKNOWN_SAMPLES);
    if (status != DHA_OK) return status;
    memset(info->model, 0, sizeof(info->model));
    return dha_stream_validate(info);
}

static int entry(const dha_stream_info *info, unsigned label, unsigned base) {
    unsigned i;
    for (i = 0; i < 256; ++i)
        if ((info->ans[2*i] >> 4) == label && info->ans[2*i+1] == base) return (int)i;
    return -1;
}

static int one_sample_packet(const dha_stream_info *info, const dha_predictor_state *initial,
                              unsigned label, unsigned gain, unsigned extra_bits,
                              uint8_t *packet, size_t *bytes) {
    dha_frame_info frame;
    uint8_t payload[3] = {0, 0, 0};
    int state = entry(info, label, 0);
    if (state < 0) return DHA_E_FORMAT;
    memset(&frame, 0, sizeof(frame));
    frame.kind = DHA_FRAME_DHA;
    frame.samples = 1;
    frame.initial = *initial;
    frame.ans_state = (uint8_t)state;
    frame.payload_bits = 5u + (info->ans[2*(unsigned)state] & 15u) + extra_bits;
    payload[0] = (uint8_t)(gain << 3);
    return test_write_packet(info, &frame, payload, (frame.payload_bits+7u)/8u,
                            packet, DHA_MAX_FRAME_BYTES, bytes);
}

static int test_headers(void) {
    dha_stream_info info, decoded, bad;
    uint8_t header[DHA_FILE_HEADER_BYTES + 1];
    size_t written = 99;
    CHECK_OK(dha_stream_default(&info, 48000, 2, 257, 123456));
    CHECK_OK(dha_header_write(&info, header, sizeof(header), &written));
    CHECK(written == DHA_FILE_HEADER_BYTES);
    CHECK_OK(dha_header_read(&decoded, header, written));
    CHECK(decoded.sample_rate == 48000 && decoded.channels == 2);
    CHECK(decoded.frame_samples == 257 && decoded.total_samples == 123456);
    CHECK(memcmp(decoded.model, info.model, sizeof(info.model)) == 0);
    CHECK(memcmp(decoded.ans, info.ans, sizeof(info.ans)) == 0);
    CHECK(dha_header_read(&decoded, header, written-1) == DHA_E_TRUNCATED);
    header[written-1] ^= 1;
    CHECK(dha_header_read(&decoded, header, written) == DHA_E_CRC);
    header[written-1] ^= 1;
    header[0] ^= 1;
    CHECK(dha_header_read(&decoded, header, written) < 0);
    header[0] ^= 1;
    written = 99;
    CHECK(dha_header_write(&info, header, DHA_FILE_HEADER_BYTES-1, &written) == DHA_E_BUFFER);
    CHECK(written == 0);
    bad = info; bad.model[0] = -128;
    CHECK(dha_stream_validate(&bad) < 0);
    bad = info; bad.ans[0] = 0x50;
    CHECK(dha_stream_validate(&bad) < 0);
    bad = info; bad.ans[0] = 7;
    CHECK(dha_stream_validate(&bad) < 0); /* selected profile allows N<=6 */
    bad = info; bad.frame_samples = 1; bad.total_samples = (UINT64_C(1)<<32)+1;
    CHECK(dha_stream_validate(&bad) == DHA_E_FORMAT);
    bad = info; bad.ans[1] = 255;
    CHECK(dha_stream_validate(&bad) < 0);
    CHECK(dha_stream_default(&bad, 0, 1, 256, 0) < 0);
    CHECK(dha_stream_default(&bad, 25000, 0, 256, 0) < 0);
    CHECK(dha_stream_default(&bad, 25000, 1, 0, 0) < 0);
    CHECK(dha_stream_default(&bad, 25000, 1, 4097, 0) < 0);
    return 0;
}

static int test_packed_lengths(void) {
    static const uint16_t lengths[] = {1, 2, 255, 256, 257, 4096};
    static const uint8_t pattern[] = {1, 2, 2, 1};
    static const int levels[] = {0, 1, -1, 2, -2};
    dha_stream_info info;
    uint8_t symbols[4096], gains[16], packet[DHA_MAX_FRAME_BYTES];
    int16_t expected[4096], decoded[4098], value;
    dha_predictor_state initial = {0, 0, 0, 0};
    size_t k, i, bytes, written;
    CHECK_OK(flat_info(&info, 2));
    for (k = 0; k < sizeof(lengths)/sizeof(lengths[0]); ++k) {
        uint16_t n = lengths[k];
        dha_frame_info frame;
        dha_decoder decoder;
        int q = 0;
        for (i = 0; i < (n+255u)/256u; ++i) gains[i] = (uint8_t)(1+i%3);
        for (i = 0; i < n; ++i) {
            symbols[i] = pattern[i%4];
            q += levels[symbols[i]] * gains[i/256];
            expected[i] = (int16_t)((((q+257)/2)-128)*256);
        }
        CHECK_OK(dha_pack_frame(&info, &initial, symbols, gains, n, 1, 42,
                                packet, sizeof(packet), &bytes));
        CHECK_OK(dha_frame_read(&info, packet, bytes, &frame));
        CHECK(frame.samples == n && frame.channel == 1 && frame.sequence == 42 && frame.kind == DHA_FRAME_DHA);
        for (i = 0; i < 4098; ++i) decoded[i] = 12345;
        written = 99;
        CHECK(dha_decode_frame(&info, packet, bytes, decoded, n-1u, &written, NULL) == DHA_E_BUFFER);
        CHECK(written == 0 && decoded[0] == 12345 && decoded[n] == 12345);
        CHECK_OK(dha_decode_frame(&info, packet, bytes, decoded, n, &written, &frame));
        CHECK(written == n && decoded[n] == 12345);
        CHECK(memcmp(expected, decoded, n*sizeof(expected[0])) == 0);
        CHECK_OK(dha_decoder_init(&decoder, &info, packet, bytes));
        for (i = 0; i < n; ++i) {
            CHECK_OK(dha_decoder_next(&decoder, &value));
            CHECK(value == expected[i]);
        }
        value = 11111;
        CHECK(dha_decoder_next(&decoder, &value) == DHA_DONE && value == 11111);
        CHECK(dha_decoder_next(&decoder, NULL) == DHA_DONE);
        CHECK(decoder.bit_position == frame.payload_bits && decoder.ans_state == 0);
        CHECK(dha_decoder_init(&decoder, &info, packet, bytes-1) < 0);
        CHECK(dha_decoder_next(&decoder, &value) < 0);
    }
    initial.q = 17;
    symbols[0] = 0; gains[0] = 1;
    CHECK_OK(dha_pack_frame(&info, &initial, symbols, gains, 1, 0, 0, packet, sizeof(packet), &bytes));
    CHECK_OK(dha_decode_frame(&info, packet, bytes, decoded, 1, &written, NULL));
    CHECK(decoded[0] == 2304 && written == 1);
    return 0;
}

static int test_raw_frames(void) {
    static const uint16_t lengths[] = {1, 2, 255, 256, 257, 4096};
    static const int16_t pattern[] = {INT16_MIN, INT16_MAX, -1, 0, 1, -12345, 23456};
    dha_stream_info info;
    dha_frame_info frame, decoded_frame;
    uint8_t payload[8192], packet[DHA_MAX_FRAME_BYTES+1];
    int16_t expected[4096], output[4097];
    size_t k, i, bytes, written;
    CHECK_OK(dha_stream_default(&info, 44100, 2, 4096, DHA_UNKNOWN_SAMPLES));
    for (k = 0; k < sizeof(lengths)/sizeof(lengths[0]); ++k) {
        memset(&frame, 0, sizeof(frame));
        frame.kind = DHA_FRAME_PCM16; frame.samples = lengths[k]; frame.channel = 1;
        frame.sequence = 0x12345678u; frame.payload_bits = (uint32_t)frame.samples*16u;
        for (i = 0; i < frame.samples; ++i) {
            expected[i] = pattern[i%7];
            test_put16(payload+2*i, (uint16_t)expected[i]);
        }
        CHECK_OK(test_write_packet(&info, &frame, payload, 2u*frame.samples, packet, sizeof(packet), &bytes));
        CHECK_OK(dha_decode_frame(&info, packet, bytes, output, 4096, &written, &decoded_frame));
        CHECK(written == frame.samples && decoded_frame.kind == DHA_FRAME_PCM16);
        CHECK(decoded_frame.sequence == frame.sequence && decoded_frame.channel == 1);
        CHECK(memcmp(expected, output, written*sizeof(output[0])) == 0);
        CHECK(dha_frame_read(&info, packet, bytes-1, &decoded_frame) < 0);
        packet[bytes] = 0;
        CHECK(dha_frame_read(&info, packet, bytes+1, &decoded_frame) < 0);
        packet[bytes-1] ^= 1;
        CHECK(dha_frame_read(&info, packet, bytes, &decoded_frame) == DHA_E_CRC);
        packet[bytes-1] ^= 1;
    }
    return 0;
}

static int must_fail_without_output(const dha_stream_info *info, const uint8_t *packet, size_t bytes) {
    dha_decoder decoder;
    int16_t value = 12345, output = 12345;
    size_t written = 99;
    int status = dha_decoder_init(&decoder, info, packet, bytes);
    if (status == DHA_OK) status = dha_decoder_next(&decoder, &value);
    CHECK(status < 0 && value == 12345);
    CHECK(dha_decoder_next(&decoder, &value) == status && value == 12345);
    CHECK(dha_decode_frame(info, packet, bytes, &output, 1, &written, NULL) < 0);
    CHECK(written == 0 && output == 12345);
    return 0;
}

static int test_malformed_dha(void) {
    dha_stream_info info;
    dha_frame_info frame;
    dha_predictor_state initial = {0, 0, 0, 0};
    uint8_t packet[DHA_MAX_FRAME_BYTES], payload[2] = {8, 0};
    size_t bytes;
    int old;
    CHECK_OK(flat_info(&info, 1));
    CHECK_OK(one_sample_packet(&info, &initial, 0, 0, 0, packet, &bytes));
    CHECK(must_fail_without_output(&info, packet, bytes) == 0);
    CHECK_OK(one_sample_packet(&info, &initial, 0, 31, 0, packet, &bytes));
    CHECK(must_fail_without_output(&info, packet, bytes) == 0);
    CHECK_OK(one_sample_packet(&info, &initial, 0, 1, 1, packet, &bytes));
    CHECK(must_fail_without_output(&info, packet, bytes) == 0); /* unused meaningful zero bit */
    old = entry(&info, 0, 1);
    CHECK(old >= 0 && (info.ans[2*(unsigned)old] & 15u) == 0);
    memset(&frame, 0, sizeof(frame));
    frame.kind = DHA_FRAME_DHA; frame.samples = 1; frame.payload_bits = 5; frame.ans_state = (uint8_t)old;
    CHECK_OK(test_write_packet(&info, &frame, payload, 1, packet, sizeof(packet), &bytes));
    CHECK(must_fail_without_output(&info, packet, bytes) == 0); /* terminal1 */
    initial.q = 254;
    CHECK_OK(one_sample_packet(&info, &initial, 1, 1, 0, packet, &bytes));
    CHECK(must_fail_without_output(&info, packet, bytes) == 0); /* q255 would clip */
    initial.q = 0; initial.d1 = 127; initial.d2 = 127;
    CHECK_OK(one_sample_packet(&info, &initial, 0, 1, 0, packet, &bytes));
    CHECK(must_fail_without_output(&info, packet, bytes) == 0); /* final d3=-254 */
    memset(&initial, 0, sizeof(initial));
    CHECK_OK(one_sample_packet(&info, &initial, 0, 1, 0, packet, &bytes));
    packet[bytes-1] |= 1; /* nonzero canonical padding, even with a repaired CRC */
    test_put32(packet+28, test_crc(test_crc(UINT32_MAX, packet, 28),
        packet+DHA_FRAME_HEADER_BYTES, bytes-DHA_FRAME_HEADER_BYTES) ^ UINT32_MAX);
    CHECK(dha_frame_read(&info, packet, bytes, &frame) == DHA_E_FORMAT);
    CHECK(dha_decoder_init(NULL, &info, packet, bytes) == DHA_E_ARGUMENT);
    CHECK(dha_decoder_next(NULL, NULL) == DHA_E_ARGUMENT);
    return 0;
}

static int test_non_aligned_book_and_late_error(void) {
    dha_stream_info info;
    dha_frame_info frame;
    dha_decoder decoder;
    dha_predictor_state initial = {0, 0, 0, 0};
    uint8_t packet[DHA_MAX_FRAME_BYTES], packed[DHA_MAX_FRAME_BYTES], payload[2] = {8, 0};
    uint8_t symbols[2] = {0, 0}, gains[1] = {1}, temporary[2];
    int first, second, zero, state, status;
    int16_t output[2], value;
    size_t bytes, packed_bytes, written;
    CHECK_OK(flat_info(&info, 1));
    first = entry(&info, 0, 95); second = entry(&info, 0, 96);
    CHECK(first >= 0 && second >= 0);
    CHECK((info.ans[2*(unsigned)first] & 15u) == 0 && (info.ans[2*(unsigned)second] & 15u) == 1);
    /* Move the one-cell/range boundary: {95},{96,97} -> {97},{95,96}.
       Complete inverse coverage remains, but base95 is not2-aligned. */
    info.ans[2*(unsigned)first+1] = 97;
    info.ans[2*(unsigned)second+1] = 95;
    zero = entry(&info, 0, 0);
    CHECK(zero >= 0 && (info.ans[2*(unsigned)zero] & 15u) == 0);
    if (zero != 95) {
        memcpy(temporary, info.ans+2u*95u, 2);
        memcpy(info.ans+2u*95u, info.ans+2u*(unsigned)zero, 2);
        memcpy(info.ans+2u*(unsigned)zero, temporary, 2);
    }
    state = entry(&info, 0, 95);
    CHECK(state >= 0 && (info.ans[2*(unsigned)state] & 15u) == 1);
    CHECK_OK(dha_stream_validate(&info));
    memset(&frame, 0, sizeof(frame));
    frame.kind = DHA_FRAME_DHA; frame.samples = 2; frame.payload_bits = 6; frame.ans_state = (uint8_t)state;
    CHECK_OK(test_write_packet(&info, &frame, payload, 1, packet, sizeof(packet), &bytes));
    CHECK_OK(dha_decode_frame(&info, packet, bytes, output, 2, &written, NULL));
    CHECK(written == 2 && output[0] == 0 && output[1] == 0);
    CHECK_OK(dha_pack_frame(&info, &initial, symbols, gains, 2, 0, 0, packed, sizeof(packed), &packed_bytes));
    CHECK(packed_bytes == bytes && memcmp(packed, packet, bytes) == 0);

    CHECK_OK(flat_info(&info, 1));
    zero = entry(&info, 0, 0);
    CHECK(zero >= 0 && (info.ans[2*(unsigned)zero] & 15u) == 0);
    CHECK((info.ans[0] >> 4) == 0 && info.ans[1] != 0);
    frame.ans_state = (uint8_t)zero;
    frame.payload_bits = 5u+(info.ans[0] & 15u);
    CHECK_OK(test_write_packet(&info, &frame, payload, (frame.payload_bits+7u)/8u, packet, sizeof(packet), &bytes));
    CHECK_OK(dha_decoder_init(&decoder, &info, packet, bytes));
    CHECK_OK(dha_decoder_next(&decoder, &value));
    CHECK(value == 0);
    value = 12345;
    status = dha_decoder_next(&decoder, &value);
    CHECK(status == DHA_E_FORMAT && value == 12345);
    CHECK(dha_decoder_next(&decoder, &value) == status);
    output[0] = output[1] = 12345; written = 99;
    CHECK(dha_decode_frame(&info, packet, bytes, output, 2, &written, NULL) == status);
    CHECK(written == 0 && output[0] == 12345 && output[1] == 12345);
    return 0;
}

static int test_pdm(void) {
    unsigned phase, input, sum = 0, high = 0, i;
    dha_pdm_state state = {0};
    CHECK(dha_pdm_next(&state, 128) == 0 && state.accumulator == 128);
    CHECK(dha_pdm_next(&state, 128) == 1 && state.accumulator == 0); /* next frame, same state */
    for (phase = 0; phase < 256; ++phase) for (input = 0; input < 256; ++input) {
        unsigned value = phase+input;
        state.accumulator = (uint8_t)phase;
        CHECK(dha_pdm_next(&state, (uint8_t)input) == value/256u);
        CHECK(state.accumulator == (uint8_t)value);
    }
    state.accumulator = 0;
    for (i = 0; i < 1000; ++i) {
        uint8_t value = (uint8_t)(i*73u+19u);
        sum += value; high += dha_pdm_next(&state, value);
    }
    CHECK(256u*high == sum-state.accumulator);
    return 0;
}

static int test_encoder_integration(void) {
    static const uint16_t tiny[] = {1, 2, 255, 256, 257};
    dha_stream_info info;
    dha_encoder_options options;
    dha_frame_info frame;
    dha_decoder decoder;
    int16_t pcm[4096], output[4096], next;
    uint8_t packet[DHA_MAX_FRAME_BYTES];
    uint32_t noise = 0x12345678u;
    unsigned fixture, i;
    size_t bytes, written;
    CHECK_OK(dha_stream_default(&info, 25000, 2, 4096, 4096));
    dha_encoder_default(&options);
    options.beam_width = 8; options.gain_candidates = 3; options.lookahead = 1;
    options.allow_pcm_fallback = 1;
    memset(pcm, 0, sizeof(pcm));
    for (i = 0; i < sizeof(tiny)/sizeof(tiny[0]); ++i) {
        CHECK_OK(dha_encode_frame(&info, &options, pcm, tiny[i], 0, i,
                                  packet, sizeof(packet), &bytes, &frame));
        CHECK_OK(dha_decode_frame(&info, packet, bytes, output, tiny[i], &written, NULL));
        CHECK(written == tiny[i] && frame.samples == tiny[i]);
    }
    for (fixture = 0; fixture < 5; ++fixture) {
        for (i = 0; i < 4096; ++i) {
            double t = (double)i/25000.0;
            if (fixture == 0) pcm[i] = 0;
            else if (fixture == 1) pcm[i] = (int16_t)(9000.0*sin(2.0*3.141592653589793*440.0*t));
            else if (fixture == 2) pcm[i] = (int16_t)((6000.0*sin(2.0*3.141592653589793*170.0*t)+
                2500.0*sin(2.0*3.141592653589793*340.0*t))*(0.55+0.45*sin(2.0*3.141592653589793*7.0*t)));
            else if (fixture == 3) pcm[i] = (i&1u) ? INT16_MAX : INT16_MIN;
            else {noise = noise*1664525u+1013904223u; pcm[i] = (int16_t)(noise >> 16);}
        }
        CHECK_OK(dha_encode_frame(&info, &options, pcm, 4096, 1, fixture,
                                  packet, sizeof(packet), &bytes, &frame));
        CHECK(frame.samples == 4096 && frame.channel == 1 && frame.sequence == fixture);
        if (fixture == 0) CHECK(frame.kind == DHA_FRAME_DHA);
        if (fixture >= 3) CHECK(frame.kind == DHA_FRAME_PCM16);
        CHECK_OK(dha_decode_frame(&info, packet, bytes, output, 4096, &written, NULL));
        CHECK(written == 4096);
        if (frame.kind == DHA_FRAME_PCM16) CHECK(memcmp(pcm, output, sizeof(pcm)) == 0);
        CHECK_OK(dha_decoder_init(&decoder, &info, packet, bytes));
        for (i = 0; i < 4096; ++i) {CHECK_OK(dha_decoder_next(&decoder, &next)); CHECK(next == output[i]);}
        CHECK(dha_decoder_next(&decoder, &next) == DHA_DONE);
    }
    /* Exercise the actual default64/8/two-output-lookahead path as well as
       the bounded fast settings used by the larger fixtures above. */
    dha_encoder_default(&options);
    for (i = 0; i < 256; ++i) pcm[i] = (int16_t)(6000.0*sin((double)i*0.042));
    CHECK_OK(dha_encode_frame(&info, &options, pcm, 256, 0, 0,
                              packet, sizeof(packet), &bytes, &frame));
    CHECK(frame.kind == DHA_FRAME_DHA);
    CHECK_OK(dha_decode_frame(&info, packet, bytes, output, 256, &written, NULL));
    CHECK(written == 256);
    packet[0] = 0xA5; written = 99;
    CHECK(dha_encode_frame(&info, &options, pcm, 1, 0, 0, packet, 0, &written, NULL) == DHA_E_BUFFER);
    CHECK(written == 0 && packet[0] == 0xA5);
    options.beam_width = 0; written = 99;
    CHECK(dha_encode_frame(&info, &options, pcm, 1, 0, 0, packet, sizeof(packet), &written, NULL) == DHA_E_ARGUMENT);
    CHECK(written == 0 && packet[0] == 0xA5);
    dha_encoder_default(&options); options.rate_penalty = -1;
    CHECK(dha_encode_frame(&info, &options, pcm, 1, 0, 0, packet, sizeof(packet), &written, NULL) == DHA_E_ARGUMENT);
    dha_encoder_default(&options); options.allow_pcm_fallback = 0;
    options.beam_width = 1; options.gain_candidates = 1; options.lookahead = 0;
    pcm[0] = INT16_MIN; pcm[1] = INT16_MAX; written = 99;
    CHECK(dha_encode_frame(&info, &options, pcm, 2, 0, 0, packet, sizeof(packet), &written, NULL) == DHA_E_PROFILE);
    CHECK(written == 0 && packet[0] == 0xA5);
    return 0;
}

int main(void) {
    CHECK(test_headers() == 0);
    CHECK(test_packed_lengths() == 0);
    CHECK(test_raw_frames() == 0);
    CHECK(test_malformed_dha() == 0);
    CHECK(test_non_aligned_book_and_late_error() == 0);
    CHECK(test_pdm() == 0);
    CHECK(test_encoder_integration() == 0);
    puts("DHA codec tests passed");
    return 0;
}
