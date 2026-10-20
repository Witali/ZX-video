/* Portable C99 WAV/DHAF file adapter. Codec arithmetic lives in the library. */
#include "dha_codec.h"
#include <errno.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint32_t rate, data_bytes;
    uint16_t channels;
    uint64_t samples;
    fpos_t data_position;
} wav_info;

typedef struct {
    FILE *file;
    const char *path;
    int created;
} destination;

typedef struct {
    uint64_t samples, groups, frames, dha_frames, pcm_frames;
    uint64_t packet_bytes, payload_bits;
} stream_stats;

static int error(const char *format, ...)
{
    va_list arguments;
    fputs("dha: ", stderr);
    va_start(arguments, format);
    vfprintf(stderr, format, arguments);
    va_end(arguments);
    fputc('\n', stderr);
    return 0;
}

static int codec_error(const char *operation, int status)
{
    return error("%s: %s (%d)", operation, dha_error_string(status), status);
}

static uint16_t get16(const uint8_t *p)
{
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t get32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void put16(uint8_t *p, uint16_t value)
{
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
}

static void put32(uint8_t *p, uint32_t value)
{
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
    p[2] = (uint8_t)(value >> 16);
    p[3] = (uint8_t)(value >> 24);
}

static int read_exact(FILE *file, void *output, size_t bytes)
{
    return bytes == 0 || fread(output, 1, bytes, file) == bytes;
}

static int write_exact(FILE *file, const void *input, size_t bytes)
{
    return bytes == 0 || fwrite(input, 1, bytes, file) == bytes;
}

static int discard(FILE *file, uint32_t bytes)
{
    uint8_t buffer[4096];
    while (bytes != 0) {
        size_t count = bytes > sizeof buffer ? sizeof buffer : (size_t)bytes;
        if (!read_exact(file, buffer, count))
            return 0;
        bytes -= (uint32_t)count;
    }
    return 1;
}

static int begin_output(destination *output, const char *path, const char *input)
{
    FILE *existing;
    if (strcmp(path, input) == 0)
        return error("input and output paths must differ");
    errno = 0;
    existing = fopen(path, "rb");
    if (existing != NULL) {
        fclose(existing);
        return error("output already exists: %s", path);
    }
    if (errno != ENOENT)
        return error("cannot establish that output is absent: %s", path);
    output->file = fopen(path, "wb");
    if (output->file == NULL)
        return error("cannot create output: %s", path);
    output->path = path;
    output->created = 1;
    return 1;
}

static int finish_output(destination *output, int success)
{
    if (output->file != NULL) {
        if (fclose(output->file) != 0) {
            error("cannot finish output: %s", output->path);
            success = 0;
        }
        output->file = NULL;
    }
    if (!success && output->created && remove(output->path) != 0)
        error("cannot remove incomplete output: %s", output->path);
    return success;
}

static int read_wav(FILE *file, wav_info *info)
{
    uint8_t header[16];
    uint32_t remaining;
    uint16_t block_align = 0;
    int have_format = 0, have_data = 0;
    memset(info, 0, sizeof *info);
    if (!read_exact(file, header, 12) || memcmp(header, "RIFF", 4) != 0 ||
        memcmp(header + 8, "WAVE", 4) != 0)
        return error("input must be a little-endian RIFF/WAVE file");
    remaining = get32(header + 4);
    if (remaining < 4)
        return error("invalid RIFF size");
    remaining -= 4;
    while (remaining != 0) {
        uint32_t size, padding;
        if (remaining < 8 || !read_exact(file, header, 8))
            return error("truncated WAV chunk header");
        remaining -= 8;
        size = get32(header + 4);
        padding = size & 1u;
        if (size > remaining || padding > remaining - size)
            return error("WAV chunk exceeds RIFF bounds");
        if (memcmp(header, "fmt ", 4) == 0) {
            uint32_t byte_rate;
            if (have_format || size < 16 || !read_exact(file, header, 16))
                return error("invalid or repeated WAV fmt chunk");
            have_format = 1;
            info->channels = get16(header + 2);
            info->rate = get32(header + 4);
            byte_rate = get32(header + 8);
            block_align = get16(header + 12);
            if (get16(header) != 1 || get16(header + 14) != 16 ||
                info->channels < 1 || info->channels > 2 ||
                info->rate < 1 || info->rate > 192000 ||
                block_align != 2u * info->channels ||
                byte_rate != info->rate * block_align)
                return error("WAV requires PCM16, one or two channels, rate 1..192000, and consistent alignment");
            if (!discard(file, size - 16))
                return error("truncated WAV fmt chunk");
        } else if (memcmp(header, "data", 4) == 0) {
            if (have_data)
                return error("multiple WAV data chunks are unsupported");
            have_data = 1;
            info->data_bytes = size;
            if (fgetpos(file, &info->data_position) != 0 || !discard(file, size))
                return error("WAV data is truncated or input is not seekable");
        } else if (!discard(file, size)) {
            return error("truncated WAV ancillary chunk");
        }
        if (padding && !read_exact(file, header, 1))
            return error("truncated WAV chunk padding");
        remaining -= size + padding;
    }
    if (!have_format || !have_data || info->data_bytes % block_align != 0)
        return error("WAV needs one fmt chunk and one aligned data chunk");
    if (fgetc(file) != EOF || ferror(file))
        return error("bytes outside the WAV RIFF boundary or input read error");
    info->samples = info->data_bytes / block_align;
    if (fsetpos(file, &info->data_position) != 0)
        return error("cannot seek to WAV data");
    return 1;
}

static int write_wav_header(FILE *file, const dha_stream_info *info)
{
    uint8_t header[44] = {0};
    uint64_t bytes;
    uint16_t align = (uint16_t)(2u * info->channels);
    if (info->total_samples == DHA_UNKNOWN_SAMPLES ||
        info->total_samples > (UINT32_MAX - 36u) / align)
        return error("decoded length is unknown or exceeds standard RIFF/WAV capacity");
    bytes = info->total_samples * align;
    memcpy(header, "RIFF", 4);
    put32(header + 4, (uint32_t)bytes + 36u);
    memcpy(header + 8, "WAVEfmt ", 8);
    put32(header + 16, 16);
    put16(header + 20, 1);
    put16(header + 22, info->channels);
    put32(header + 24, info->sample_rate);
    put32(header + 28, info->sample_rate * align);
    put16(header + 32, align);
    put16(header + 34, 16);
    memcpy(header + 36, "data", 4);
    put32(header + 40, (uint32_t)bytes);
    if (!write_exact(file, header, sizeof header))
        return error("cannot write WAV header");
    return 1;
}

static int read_stream_header(FILE *file, dha_stream_info *info)
{
    uint8_t header[DHA_FILE_HEADER_BYTES];
    int status;
    if (!read_exact(file, header, sizeof header))
        return error("truncated DHAF file header");
    status = dha_header_read(info, header, sizeof header);
    if (status != DHA_OK)
        return codec_error("DHAF header", status);
    if (info->channels < 1 || info->channels > 2 || info->sample_rate < 1 ||
        info->sample_rate > 192000 || info->frame_samples < 1 ||
        info->frame_samples > DHA_MAX_FRAME_SAMPLES)
        return error("unsupported DHAF stream profile");
    return 1;
}

static int read_packet(FILE *file, uint8_t *packet, size_t *bytes)
{
    size_t prefix = fread(packet, 1, 8, file);
    uint32_t count;
    if (prefix == 0 && !ferror(file))
        return DHA_DONE;
    if (prefix != 8)
        return DHA_E_TRUNCATED;
    count = get32(packet + 4);
    if (count < DHA_FRAME_HEADER_BYTES || count > DHA_MAX_FRAME_BYTES)
        return DHA_E_FORMAT;
    if (!read_exact(file, packet + 8, (size_t)count - 8))
        return DHA_E_TRUNCATED;
    *bytes = count;
    return DHA_OK;
}

static int write_group(FILE *file, int16_t pcm[2][DHA_MAX_FRAME_SAMPLES],
                       uint16_t samples, uint16_t channels)
{
    uint8_t interleaved[4u * DHA_MAX_FRAME_SAMPLES];
    size_t at = 0;
    uint16_t i, channel;
    for (i = 0; i < samples; ++i)
        for (channel = 0; channel < channels; ++channel) {
            put16(interleaved + at, (uint16_t)pcm[channel][i]);
            at += 2;
        }
    if (!write_exact(file, interleaved, at))
        return error("cannot write WAV samples");
    return 1;
}

static int walk_stream(FILE *file, const dha_stream_info *info, FILE *wav, stream_stats *stats)
{
    uint8_t packet[DHA_MAX_FRAME_BYTES];
    int16_t pcm[2][DHA_MAX_FRAME_SAMPLES];
    uint64_t group = 0;
    int short_final = 0;
    memset(stats, 0, sizeof *stats);
    for (;;) {
        size_t bytes = 0;
        uint16_t expected = 0, channel;
        int status = read_packet(file, packet, &bytes);
        if (status == DHA_DONE) {
            if (info->total_samples != DHA_UNKNOWN_SAMPLES && stats->samples != info->total_samples)
                return error("DHAF ended before its declared sample count");
            return 1;
        }
        if (status != DHA_OK)
            return codec_error("DHAF packet", status);
        if (group > UINT32_MAX || short_final ||
            (info->total_samples != DHA_UNKNOWN_SAMPLES && stats->samples == info->total_samples))
            return error("trailing frame after the final DHAF sample group");
        if (info->total_samples != DHA_UNKNOWN_SAMPLES) {
            uint64_t remaining = info->total_samples - stats->samples;
            expected = (uint16_t)(remaining < info->frame_samples ? remaining : info->frame_samples);
        }
        for (channel = 0; channel < info->channels; ++channel) {
            dha_frame_info frame;
            size_t written = 0;
            if (channel != 0) {
                status = read_packet(file, packet, &bytes);
                if (status != DHA_OK)
                    return error("missing or truncated DHAF channel frame");
            }
            status = dha_frame_read(info, packet, bytes, &frame);
            if (status != DHA_OK)
                return codec_error("DHAF frame", status);
            if (frame.sequence != (uint32_t)group || frame.channel != channel)
                return error("DHAF sequence/channel order is invalid");
            if (channel == 0 && info->total_samples == DHA_UNKNOWN_SAMPLES)
                expected = frame.samples;
            if (expected == 0 || expected > info->frame_samples || frame.samples != expected)
                return error("DHAF channel counts or final frame length are inconsistent");
            status = dha_decode_frame(info, packet, bytes, pcm[channel], DHA_MAX_FRAME_SAMPLES,
                                      &written, NULL);
            if (status != DHA_OK)
                return codec_error("DHAF frame decode", status);
            if (written != expected)
                return error("DHAF decoder sample count differs from its header");
            ++stats->frames;
            if (frame.kind == DHA_FRAME_PCM16)
                ++stats->pcm_frames;
            else if (frame.kind == DHA_FRAME_DHA)
                ++stats->dha_frames;
            else
                return error("unsupported DHAF frame kind");
            stats->packet_bytes += bytes;
            stats->payload_bits += frame.payload_bits;
        }
        if (UINT64_MAX - stats->samples < expected)
            return error("DHAF sample count overflow");
        stats->samples += expected;
        ++stats->groups;
        short_final = expected < info->frame_samples;
        if (wav != NULL && !write_group(wav, pcm, expected, info->channels))
            return 0;
        ++group;
    }
}

static void print_info(const dha_stream_info *info, const stream_stats *stats)
{
    uint64_t raw_bytes = stats->samples * info->channels * 2u;
    printf("format: DHAF %d.%d\n", DHA_VERSION_MAJOR, DHA_VERSION_MINOR);
    printf("sample_rate: %" PRIu32 "\nchannels: %u\nframe_samples: %u\n",
           info->sample_rate, (unsigned)info->channels, (unsigned)info->frame_samples);
    if (info->total_samples == DHA_UNKNOWN_SAMPLES)
        puts("declared_samples_per_channel: unknown");
    else
        printf("declared_samples_per_channel: %" PRIu64 "\n", info->total_samples);
    printf("validated_samples_per_channel: %" PRIu64 "\nframe_groups: %" PRIu64
           "\nchannel_frames: %" PRIu64 "\ndha_frames: %" PRIu64
           "\npcm16_fallback_frames: %" PRIu64 "\n",
           stats->samples, stats->groups, stats->frames, stats->dha_frames, stats->pcm_frames);
    printf("file_bytes: %" PRIu64 "\npayload_bits: %" PRIu64
           "\noriginal_pcm16_bytes: %" PRIu64 "\n",
           (uint64_t)DHA_FILE_HEADER_BYTES + stats->packet_bytes, stats->payload_bits, raw_bytes);
}

static int encode(const char *input, const char *path, uint16_t frame_samples, int fast)
{
    FILE *file = fopen(input, "rb");
    destination output = {NULL, NULL, 0};
    dha_stream_info info;
    dha_encoder_options options;
    wav_info wav;
    uint8_t header[DHA_FILE_HEADER_BYTES], packet[DHA_MAX_FRAME_BYTES];
    uint8_t interleaved[4u * DHA_MAX_FRAME_SAMPLES];
    int16_t pcm[2][DHA_MAX_FRAME_SAMPLES];
    uint64_t done = 0, sequence = 0;
    size_t written;
    int success = 0, status;
    if (file == NULL)
        return error("cannot open input: %s", input);
    if (!read_wav(file, &wav))
        goto finished;
    status = dha_stream_default(&info, wav.rate, wav.channels, frame_samples, wav.samples);
    if (status != DHA_OK) {
        codec_error("default codec stream", status);
        goto finished;
    }
    status = dha_header_write(&info, header, sizeof header, &written);
    if (status != DHA_OK || written != sizeof header) {
        codec_error("DHAF header write", status);
        goto finished;
    }
    dha_encoder_default(&options);
    if (fast) {
        options.beam_width = 8;
        options.gain_candidates = 2;
        options.lookahead = 0;
    }
    if (!begin_output(&output, path, input) || !write_exact(output.file, header, sizeof header)) {
        if (output.file != NULL)
            error("cannot write DHAF header");
        goto finished;
    }
    while (done < wav.samples) {
        uint64_t remaining = wav.samples - done;
        uint16_t count = (uint16_t)(remaining < frame_samples ? remaining : frame_samples);
        uint16_t i, channel;
        size_t bytes = (size_t)count * wav.channels * 2u, at = 0;
        if (sequence > UINT32_MAX || !read_exact(file, interleaved, bytes)) {
            error("truncated WAV samples or DHAF sequence overflow");
            goto finished;
        }
        for (i = 0; i < count; ++i)
            for (channel = 0; channel < wav.channels; ++channel) {
                uint16_t value = get16(interleaved + at);
                pcm[channel][i] = value <= 32767u ? (int16_t)value : (int16_t)((int32_t)value - 65536);
                at += 2;
            }
        for (channel = 0; channel < wav.channels; ++channel) {
            status = dha_encode_frame(&info, &options, pcm[channel], count, (uint8_t)channel,
                                      (uint32_t)sequence, packet, sizeof packet, &written, NULL);
            if (status != DHA_OK) {
                codec_error("encode frame", status);
                goto finished;
            }
            if (written < DHA_FRAME_HEADER_BYTES || written > sizeof packet ||
                !write_exact(output.file, packet, written)) {
                error("cannot write DHAF frame");
                goto finished;
            }
        }
        done += count;
        ++sequence;
    }
    success = 1;
finished:
    if (fclose(file) != 0) {
        error("cannot close input");
        success = 0;
    }
    return finish_output(&output, success);
}

static int decode_or_info(const char *input, const char *path)
{
    FILE *file = fopen(input, "rb");
    destination output = {NULL, NULL, 0};
    dha_stream_info info;
    stream_stats stats;
    int success = 0;
    if (file == NULL)
        return error("cannot open input: %s", input);
    if (!read_stream_header(file, &info))
        goto finished;
    if (path != NULL) {
        if (info.total_samples == DHA_UNKNOWN_SAMPLES) {
            error("WAV decode requires a known DHAF sample total; use info to validate an unknown-length stream");
            goto finished;
        }
        if (!begin_output(&output, path, input) || !write_wav_header(output.file, &info))
            goto finished;
    }
    if (!walk_stream(file, &info, output.file, &stats))
        goto finished;
    if (path == NULL)
        print_info(&info, &stats);
    success = 1;
finished:
    if (fclose(file) != 0) {
        error("cannot close input");
        success = 0;
    }
    return finish_output(&output, success);
}

static int frame_option(const char *text, uint16_t *value)
{
    unsigned long parsed;
    char *end;
    if (text[0] == '\0' || text[0] == '-' || text[0] == '+')
        return 0;
    errno = 0;
    parsed = strtoul(text, &end, 10);
    if (errno != 0 || *end != '\0' || parsed < 1 || parsed > DHA_MAX_FRAME_SAMPLES)
        return 0;
    *value = (uint16_t)parsed;
    return 1;
}

static int usage(void)
{
    fputs("Usage:\n  dha encode input.wav output.dhaf [--frame 1..4096] [--fast]\n"
          "  dha decode input.dhaf output.wav\n  dha info input.dhaf\n"
          "WAV: little-endian PCM16, mono/stereo, 1..192000 Hz; existing outputs are refused.\n", stderr);
    return 2;
}

int main(int argc, char **argv)
{
    if (argc >= 4 && strcmp(argv[1], "encode") == 0) {
        uint16_t frame = DHA_MAX_FRAME_SAMPLES;
        int fast = 0, seen_frame = 0, i;
        for (i = 4; i < argc; ++i) {
            if (strcmp(argv[i], "--fast") == 0 && !fast)
                fast = 1;
            else if (strcmp(argv[i], "--frame") == 0 && !seen_frame && i + 1 < argc) {
                if (!frame_option(argv[++i], &frame))
                    return usage();
                seen_frame = 1;
            } else
                return usage();
        }
        return encode(argv[2], argv[3], frame, fast) ? 0 : 1;
    }
    if (argc == 4 && strcmp(argv[1], "decode") == 0)
        return decode_or_info(argv[2], argv[3]) ? 0 : 1;
    if (argc == 3 && strcmp(argv[1], "info") == 0)
        return decode_or_info(argv[2], NULL) ? 0 : 1;
    return usage();
}
