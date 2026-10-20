/* Bounded original-model DHA quality control. The only search-option change
   is rate_penalty82 ->0. Input is the existing16k helper lattice, retaining
   every physical8k sample at an even position. All search/packet work uses
   the unchanged pinned C library; no ZX player is implemented here. */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "dha_codec.h"

static void fatal(const char *message) {
    fprintf(stderr, "%s\n", message);
    exit(1);
}

static FILE *open_file(const char *path, const char *mode) {
    FILE *file = fopen(path, mode);
    if (!file) fatal("Cannot open a required input/output file");
    return file;
}

static void write_bytes(FILE *file, const void *data, size_t bytes) {
    if (fwrite(data, 1, bytes, file) != bytes) fatal("Output write failed");
}

static void check(int status) {
    if (status != DHA_OK) fatal(dha_error_string(status));
}

int main(int argc, char **argv) {
    FILE *model_file, *source, *encoded, *decoded, *ledger;
    dha_stream_info info, parsed;
    dha_encoder_options options;
    uint8_t model[1024], raw_pcm[2*DHA_MAX_FRAME_SAMPLES];
    uint8_t header[DHA_FILE_HEADER_BYTES], packet[DHA_MAX_FRAME_BYTES];
    int16_t pcm[DHA_MAX_FRAME_SAMPLES], restored[DHA_MAX_FRAME_SAMPLES];
    uint64_t samples, done = 0, payload_bits = 0, file_bytes = DHA_FILE_HEADER_BYTES;
    uint32_t sequence = 0, dha_frames = 0, pcm_frames = 0;
    long source_bytes;
    size_t written;
    clock_t start = clock();
    if (argc != 6) {
        fprintf(stderr, "usage: dha_quality_host ORIGINAL-MODEL1024 CODED-INPUT.pcm16 OUTPUT.dhaf DECODED-CODED.pcm16 FRAME-LEDGER.jsonl\n");
        return 2;
    }
    model_file = open_file(argv[1], "rb");
    if (fread(model, 1, sizeof model, model_file) != sizeof model || fgetc(model_file) != EOF)
        fatal("Model must contain exactly1024 signed-byte entries");
    fclose(model_file);
    source = open_file(argv[2], "rb");
    if (fseek(source, 0, SEEK_END) || (source_bytes = ftell(source)) <= 0 || source_bytes % 2)
        fatal("Source must be nonempty little-endian PCM16");
    if (fseek(source, 0, SEEK_SET)) fatal("Cannot rewind source");
    samples = (uint64_t)source_bytes / 2;
    check(dha_stream_default(&info, 16000, 1, DHA_MAX_FRAME_SAMPLES, samples));
    /* The caller authenticates the original1024-byte model. The16k header
       describes only the helper lattice, not a new physical source rate. */
    memcpy(info.model, model, sizeof model);
    check(dha_stream_validate(&info));
    dha_encoder_default(&options);
    if (options.beam_width != 64 || options.gain_candidates != 8 || options.lookahead != 2 ||
        options.rate_penalty != 82 || options.allow_pcm_fallback != 1)
        fatal("Pinned library default options changed");
    options.rate_penalty = 0;
    check(dha_header_write(&info, header, sizeof header, &written));
    if (written != sizeof header) fatal("Header length mismatch");
    check(dha_header_read(&parsed, header, sizeof header));
    if (memcmp(parsed.model, model, sizeof model)) fatal("Header model mismatch");
    encoded = open_file(argv[3], "wb");
    decoded = open_file(argv[4], "wb");
    ledger = open_file(argv[5], "wb");
    write_bytes(encoded, header, sizeof header);
    while (done < samples) {
        uint16_t count = (uint16_t)(samples-done < DHA_MAX_FRAME_SAMPLES ? samples-done : DHA_MAX_FRAME_SAMPLES);
        dha_frame_info frame, restored_frame;
        size_t at, decoded_count;
        double seconds;
        if (fread(raw_pcm, 2, count, source) != count) fatal("Truncated PCM input");
        for (at = 0; at < count; ++at) {
            unsigned word = raw_pcm[2*at] | ((unsigned)raw_pcm[2*at+1] << 8);
            pcm[at] = (int16_t)(word < 32768 ? (int)word : (int)word - 65536);
        }
        check(dha_encode_frame(&info, &options, pcm, count, 0, sequence,
            packet, sizeof packet, &written, &frame));
        if (frame.samples != count || frame.sequence != sequence || frame.packet_bytes != written)
            fatal("Encoded frame metadata mismatch");
        check(dha_decode_frame(&parsed, packet, written, restored, DHA_MAX_FRAME_SAMPLES,
            &decoded_count, &restored_frame));
        if (decoded_count != count || restored_frame.kind != frame.kind) fatal("Decode length/kind mismatch");
        if (frame.kind == DHA_FRAME_PCM16 && memcmp(pcm, restored, count*sizeof *pcm))
            fatal("PCM16 fallback was not exact");
        for (at = 0; at < count; ++at) {
            unsigned word = (uint16_t)restored[at];
            raw_pcm[2*at] = (uint8_t)word;
            raw_pcm[2*at+1] = (uint8_t)(word >> 8);
        }
        write_bytes(encoded, packet, written);
        write_bytes(decoded, raw_pcm, 2*count);
        fflush(encoded); fflush(decoded);
        done += count; file_bytes += written; payload_bits += frame.payload_bits;
        if (frame.kind == DHA_FRAME_DHA) ++dha_frames; else ++pcm_frames;
        seconds = (double)(clock()-start)/CLOCKS_PER_SEC;
        fprintf(ledger, "{\"sequence\":%" PRIu32 ",\"kind\":%u,\"samples\":%u,\"packet_bytes\":%zu,\"payload_bits\":%" PRIu32 ",\"completed_samples\":%" PRIu64 ",\"elapsed_seconds\":%.6f}\n",
            sequence, (unsigned)frame.kind, (unsigned)count, written, frame.payload_bits, done, seconds);
        fflush(ledger);
        printf("{\"sequence\":%" PRIu32 ",\"completed_samples\":%" PRIu64 ",\"total_samples\":%" PRIu64 ",\"DHA_frames\":%" PRIu32 ",\"PCM16_frames\":%" PRIu32 ",\"elapsed_seconds\":%.6f}\n",
            sequence, done, samples, dha_frames, pcm_frames, seconds);
        fflush(stdout);
        ++sequence;
    }
    if (fgetc(source) != EOF || ferror(source)) fatal("Source length/read mismatch");
    fclose(source); fclose(encoded); fclose(decoded); fclose(ledger);
    printf("{\"complete\":true,\"samples\":%" PRIu64 ",\"frames\":%" PRIu32 ",\"DHA_frames\":%" PRIu32 ",\"PCM16_frames\":%" PRIu32 ",\"file_bytes\":%" PRIu64 ",\"payload_bits\":%" PRIu64 "}\n",
        samples, sequence, dha_frames, pcm_frames, file_bytes, payload_bits);
    return 0;
}
