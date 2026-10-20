#ifndef DHA_CODEC_H
#define DHA_CODEC_H
#include <stddef.h>
#include <stdint.h>
#if defined(_WIN32) && defined(DHA_SHARED)
# if defined(DHA_BUILDING)
#  define DHA_API __declspec(dllexport)
# else
#  define DHA_API __declspec(dllimport)
# endif
#else
# define DHA_API
#endif
#ifdef __cplusplus
extern "C" {
#endif

#define DHA_VERSION_MAJOR 1
#define DHA_VERSION_MINOR 0
#define DHA_FILE_HEADER_BYTES 1572u
#define DHA_FRAME_HEADER_BYTES 32u
#define DHA_MAX_FRAME_SAMPLES 4096u
#define DHA_MAX_FRAME_BYTES (DHA_FRAME_HEADER_BYTES + 2u * DHA_MAX_FRAME_SAMPLES)
#define DHA_UNKNOWN_SAMPLES UINT64_MAX

enum { DHA_OK=0, DHA_DONE=1, DHA_E_ARGUMENT=-1, DHA_E_BUFFER=-2,
       DHA_E_TRUNCATED=-3, DHA_E_FORMAT=-4, DHA_E_CRC=-5,
       DHA_E_PROFILE=-6, DHA_E_MEMORY=-7, DHA_E_UNSUPPORTED=-8 };
enum { DHA_FRAME_PCM16=0, DHA_FRAME_DHA=1 };

/* Tables are immutable after header validation and must outlive decoders.
   ANS entries are two bytes: (symbol<<4)|suffix_bits, base. */
typedef struct {
    /* Stored clock metadata, not an instruction to resample audio. */
    uint32_t sample_rate;
    /* Frame sample counts are per channel, never interleaved stereo values. */
    uint16_t channels, frame_samples;
    uint64_t total_samples; /* Sample frames PER CHANNEL; UINT64_MAX if unknown. */
    int8_t model[1024];
    uint8_t ans[512];
} dha_stream_info;

typedef struct { int16_t q; int8_t d1,d2,d3; } dha_predictor_state;
typedef struct {
    uint32_t sequence, packet_bytes, payload_bits;
    uint16_t samples;
    uint8_t channel, kind, ans_state;
    /* State before the first sample, based on reconstructed history. */
    dha_predictor_state initial;
} dha_frame_info;

/* The decoder allocates no memory. Buffers and info remain caller-owned.
   Finish every frame: errors can be detected at its last sample. */
typedef struct {
    const dha_stream_info *info;
    const uint8_t *payload;
    dha_frame_info frame;
    dha_predictor_state state;
    uint32_t bit_position;
    uint16_t position;
    uint8_t ans_state, gain;
    int error;
} dha_decoder;

typedef struct { uint8_t accumulator; } dha_pdm_state;
typedef struct {
    /* 1..128 retained histories per sample, 1..30 shortlisted gains, 0..2
       future samples for beam ranking, and Boolean PCM fallback policy. */
    uint16_t beam_width;
    uint8_t gain_candidates, lookahead, allow_pcm_fallback;
    /* Nonnegative finite weight for approximate entropy cost in the search;
       it is not a requested bit rate or a guaranteed error/quality bound. */
    double rate_penalty;
} dha_encoder_options;

/** Return a static, non-owned English description of a status code.
 * Unknown codes return "unknown error"; the caller must not free the string. */
DHA_API const char *dha_error_string(int status);
/** Populate caller-owned info with the default predictor and ANS tables.
 * rate is in Hz; channels is 1 or 2; frame_samples is 1..4096 per channel.
 * total_samples is a per-channel count or DHA_UNKNOWN_SAMPLES. The function
 * fills info before validating it, so invalid settings still modify info.
 * Return DHA_OK, DHA_E_ARGUMENT for NULL info, or a validation error. */
DHA_API int dha_stream_default(dha_stream_info *info, uint32_t rate, uint16_t channels,
                               uint16_t frame_samples, uint64_t total_samples);
/** Check stream limits, predictor constraints and complete ANS inverse ranges.
 * Does not modify info or allocate memory. Return DHA_OK for usable tables;
 * malformed settings return DHA_E_FORMAT, and NULL info DHA_E_ARGUMENT. */
DHA_API int dha_stream_validate(const dha_stream_info *info);
/** Serialize a validated stream header, including its tables and CRC32.
 * capacity and *written count bytes. written is required and is set to zero
 * before validation; success writes DHA_FILE_HEADER_BYTES. Buffers are owned
 * by the caller. Return DHA_E_BUFFER when capacity is insufficient. */
DHA_API int dha_header_write(const dha_stream_info *info, uint8_t *output,
                             size_t capacity, size_t *written);
/** Read the first DHA_FILE_HEADER_BYTES from input and validate CRC and tables.
 * bytes may include following packets; this call consumes no transport state.
 * Commit to info only on DHA_OK, leaving it unchanged on any error. Neither
 * input nor the resulting info refers to allocated library-owned storage. */
DHA_API int dha_header_read(dha_stream_info *info, const uint8_t *input, size_t bytes);
/** Validate one complete packet's header, lengths, padding and CRC32.
 * bytes must equal the declared packet length. On success copy metadata into
 * frame; on failure leave frame unchanged. This does not decode predictive
 * samples or validate file-level channel/sequence ordering and total length;
 * the decoder and the transport adapter perform those checks, respectively. */
DHA_API int dha_frame_read(const dha_stream_info *info, const uint8_t *packet,
                           size_t bytes, dha_frame_info *frame);
/** Bind an allocation-free incremental decoder to one complete packet.
 * info and packet remain caller-owned, immutable and alive through decoding.
 * The call clears decoder, validates the packet, and records sticky errors.
 * Each frame starts from its own stored predictor and ANS state. */
DHA_API int dha_decoder_init(dha_decoder *decoder, const dha_stream_info *info,
                             const uint8_t *packet, size_t bytes);
/** Decode one sample: DHA_OK writes *pcm; DHA_DONE produces no sample.
 * A negative status becomes sticky until reinitialization. The final sample
 * is checked for exact bit consumption and terminal ANS state before output;
 * an earlier successful sample alone does not certify a complete frame.
 * DHA uses the exact unsigned8 R2R rounding (((q+257)/2)-128)*256;
 * PCM fallback preserves all PCM16 bits. No floating point or allocation. */
DHA_API int dha_decoder_next(dha_decoder *decoder, int16_t *pcm);
/** Validate and decode a complete packet into caller-owned PCM16 storage.
 * capacity and *written count samples, not bytes. written is required and
 * starts at zero; frame is optional. A validation pass precedes the output
 * pass, so output and optional frame remain unchanged on error when inputs
 * stay immutable. Keep output separate from info and packet storage.
 * Success returns DHA_OK and writes exactly the packet's sample count. */
DHA_API int dha_decode_frame(const dha_stream_info *info, const uint8_t *packet,
                             size_t bytes, int16_t *output, size_t capacity,
                             size_t *written, dha_frame_info *frame);
/** Emit one first-order PDM bit for an unsigned PCM8 target, updating state.
 * Initialize accumulator=0 once and retain it across frames and repeats.
 * Return the carry of accumulator+pcm8; NULL state returns zero. The caller
 * schedules output: four calls with the same PCM8 at equal intervals give
 * 100 kHz PDM for 25 kHz PCM without storing expanded bits or resampling PCM.
 * This primitive produces no device I/O and performs no reconstruction filter. */
DHA_API uint8_t dha_pdm_next(dha_pdm_state *state, uint8_t pcm8);

/* Encoder functions live in the optional encoder compilation unit. */
/** Fill per-call search options: beam64, 8 gains, lookahead2, penalty82,
 * PCM fallback enabled. NULL is a no-op. Larger search budgets cost more
 * encoder time; these options never increase the decoder's search work. */
DHA_API void dha_encoder_default(dha_encoder_options *options);
/** Search a continuous predictive trajectory without packet framing or PCM
 * fallback. initial is the reconstructed state BEFORE pcm[0]; zero-initialize
 * it for a ROM whose compiled first sample begins from zero history. samples
 * is 1..4096. Supply symbols[samples], gains[ceil(samples/256)], q[samples]
 * and final_state, all caller-owned and separate from the inputs. q contains
 * exact signed predictor outputs, before R2R/PDM rounding. Success returns
 * DHA_OK and commits final_state; failure may partially modify the arrays but
 * leaves final_state unchanged. NULL options selects defaults; the fallback
 * flag is validated but ignored. This host-only call allocates search scratch.
 * To continue, pass final_state as the next initial state. Every nonfinal
 * chunk must contain a multiple of256 samples so gain blocks stay aligned.
 * No filtering, resampling, fade, level adjustment or PCM fallback occurs. */
DHA_API int dha_encode_trajectory(const dha_stream_info *info,
                                  const dha_encoder_options *options,
                                  const dha_predictor_state *initial,
                                  const int16_t *pcm, uint16_t samples,
                                  uint8_t *symbols, uint8_t *gains, int16_t *q,
                                  dha_predictor_state *final_state);
/** Encode contiguous mono PCM16 samples for one channel and sequence group.
 * samples is 1..info->frame_samples; stereo callers submit each channel
 * separately. NULL options selects defaults. The host encoder allocates and
 * frees search workspace; it does not change sample rate or write files.
 * It searches a lossy predictive path, then may select original PCM16 when
 * prediction is infeasible or not smaller and allow_pcm_fallback is enabled.
 * capacity and *written are byte counts; written is required and starts at zero.
 * On success optional frame reports the actual kind and packet metadata;
 * output contents are unspecified on error. Inputs remain caller-owned. */
DHA_API int dha_encode_frame(const dha_stream_info *info, const dha_encoder_options *options,
                             const int16_t *pcm, uint16_t samples, uint8_t channel,
                             uint32_t sequence, uint8_t *output, size_t capacity,
                             size_t *written, dha_frame_info *frame);
/** Package a preselected trajectory without searching or adding audio loss.
 * initial is the state BEFORE the first sample; symbols contains samples
 * labels 0..4 and gains contains ceil(samples/256) values in 1..30. Every
 * prediction and all three final differences must satisfy the DHA profile.
 * The packer validates the path, runs ANS backwards from terminal state0,
 * then writes gains and suffixes forward. It allocates temporary workspace.
 * channel/sequence identify this independent packet; capacity and *written
 * count bytes. Return DHA_OK on success, otherwise a negative status with
 * *written=0 when supplied; output contents on error are unspecified.
 * Repacking exact q is distinct from lossless compression of original audio. */
DHA_API int dha_pack_frame(const dha_stream_info *info, const dha_predictor_state *initial,
                           const uint8_t *symbols, const uint8_t *gains,
                           uint16_t samples, uint8_t channel, uint32_t sequence,
                           uint8_t *output, size_t capacity, size_t *written);

#ifdef __cplusplus
}
#endif
#endif
