/* Portable C99 DHA1 frame encoder and exact trajectory packer.
 *
 * The bounded gain shortlist / predictive beam / two-output lookahead search
 * is adapted from audio/music/sea-foam/recorded-difference-history/src/audio.c
 * (canonical-LF SHA256 e75142e6ce103e3e5e2d302e86aee083189cb45a61def156ccfdbb0e2c08125b).
 * Unlike that offline DLL entry point this unit owns no global state, starts
 * each frame from an explicit flat history, and uses the public stream's
 * actual ANS frequencies. Large search and packing workspaces are heap-owned.
 * The PC packet writes gain5 at block start and encodes EVERY symbol; this is
 * deliberately not the Z80 compiled-first / interleaved-prefetch ROM wire.
 */
#include "dha_internal.h"
#include <math.h>
#include <stdlib.h>

#define ENC_BEAM_MAX 128
#define ENC_BLOCK 256
#define ENC_LABELS 5
#define ENC_CAP_PCM16 (18*256)
#define ENC_INFINITY 1e100

typedef struct {
    /* cost covers committed samples; rank adds temporary lookahead cost.
     * h is newest-first q1..q4, not four previously emitted PCM16 values. */
    double cost, rank;
    int16_t h[4];
    uint16_t parent;
    uint8_t symbol;
} enc_node;

typedef struct {
    enc_node previous[ENC_BEAM_MAX], selected[ENC_BEAM_MAX];
    enc_node candidates[ENC_BEAM_MAX*ENC_LABELS];
    /* Trace rows have the requested beam width as their stride. Each retained
     * child records its slot in the previous row and its chosen label. */
    uint16_t parents[ENC_BLOCK*ENC_BEAM_MAX];
    uint8_t choices[ENC_BLOCK*ENC_BEAM_MAX];
} enc_scratch;

typedef struct {
    const dha_stream_info *info;
    double bits[ENC_LABELS], penalty;
} enc_config;

typedef struct { double cost; int gain; } enc_gain;

static const int enc_levels[ENC_LABELS] = {0, 1, -1, 2, -2};

/** Initialize caller-owned options: beam64, gain shortlist8, lookahead2,
 * rate penalty82 and enabled PCM16 fallback.
 * NULL is a no-op. No allocation occurs; the caller may adjust the resulting
 * fields before passing them to dha_encode_frame(). */
void dha_encoder_default(dha_encoder_options *options) {
    if (!options) return;
    memset(options, 0, sizeof(*options));
    options->beam_width=64;
    options->gain_candidates=8;
    options->lookahead=2;
    options->allow_pcm_fallback=1;
    options->rate_penalty=82.0;
}

/** Check a non-NULL options record without modifying it.
 * Return a boolean for supported bounds: beam1..128, gain shortlist1..30,
 * lookahead0..2, boolean PCM fallback, and a finite nonnegative rate penalty.
 * The public caller converts a false result to DHA_E_ARGUMENT. */
static int enc_options_valid(const dha_encoder_options *options) {
    return options->beam_width >= 1 && options->beam_width <= ENC_BEAM_MAX &&
        options->gain_candidates >= 1 && options->gain_candidates <= 30 &&
        options->lookahead <= 2 && options->allow_pcm_fallback <= 1 &&
        isfinite(options->rate_penalty) && options->rate_penalty >= 0.0;
}

/** Append the low `bits` bits of value in most-significant-bit-first order.
 * The caller supplies a zero-initialized buffer with sufficient capacity and
 * a mutable bit cursor. OR writes preserve untouched zero tail padding;
 * bits==0 is valid for ANS entries that consume no suffix. No bounds checking
 * or allocation is performed here. */
static void enc_put_bits(uint8_t *out, uint32_t *position, unsigned value, unsigned bits) {
    while (bits) {
        unsigned bit;
        --bits;
        bit=(value >> bits)&1u;
        out[*position >> 3] |= (uint8_t)(bit << (7u-(*position&7u)));
        ++*position;
    }
}

/** Build the reverse of the immutable stream's forward ANS decoder table.
 * The caller owns inverse[5*256] and counts[5]; both are overwritten, possibly
 * partially on DHA_E_FORMAT. Each inverse[symbol*256+next] stores the unique
 * old state whose entry emits that symbol and reaches next with some suffix.
 * Every next state must be covered exactly once for each label; overlaps,
 * holes, out-of-range symbols and suffix lengths above6 are rejected.
 * counts records decoder-state counts per label, not covered-range lengths.
 * Bases need not be aligned: forward decoding computes base+read_suffix.
 * Return DHA_OK on complete coverage. This helper does not allocate memory. */
static int enc_inverse(const dha_stream_info *info, uint16_t *inverse,
                       unsigned counts[ENC_LABELS]) {
    unsigned old, symbol, n, base, suffix, k;
    for (k=0; k<ENC_LABELS*256u; ++k) inverse[k]=UINT16_MAX;
    memset(counts, 0, ENC_LABELS*sizeof(*counts));
    for (old=0; old<256u; ++old) {
        symbol=info->ans[2u*old] >> 4;
        n=info->ans[2u*old]&15u;
        base=info->ans[2u*old+1u];
        if (symbol >= ENC_LABELS || n > 6 || base+(1u << n)>256u) return DHA_E_FORMAT;
        ++counts[symbol];
        for (suffix=0; suffix<(1u << n); ++suffix) {
            k=symbol*256u+base+suffix;
            if (inverse[k] != UINT16_MAX) return DHA_E_FORMAT;
            inverse[k]=(uint16_t)old;
        }
    }
    for (k=0; k<ENC_LABELS*256u; ++k)
        if (inverse[k] == UINT16_MAX) return DHA_E_FORMAT;
    return DHA_OK;
}

/** Package an existing valid trajectory without searching or resampling.
 * info and initial are borrowed read-only. symbols has `samples` labels;
 * gains has ceil(samples/256) gains, each shared by its block. The initial
 * predictor state is copied and advanced through every label, including the
 * first and last, so invalid predictions or new differences are rejected.
 * channel and sequence are caller-selected frame metadata; ordering frames
 * across channels belongs to the enclosing file/transport implementation.
 * output is caller-owned storage of capacity bytes. On success return DHA_OK
 * and set *written to the complete packet size; on error leave *written zero
 * when that pointer is supplied. Scratch allocation belongs to this function
 * and is freed on every path. Failures include invalid arguments, malformed
 * tables, an invalid trajectory, allocation failure or insufficient capacity.
 * No original PCM is supplied, so this validates the codec profile rather
 * than the search encoder's PCM error cap or compression efficiency. */
int dha_pack_frame(const dha_stream_info *info, const dha_predictor_state *initial,
                   const uint8_t *symbols, const uint8_t *gains,
                   uint16_t samples, uint8_t channel, uint32_t sequence,
                   uint8_t *output, size_t capacity, size_t *written) {
    uint16_t *inverse=NULL;
    uint8_t *storage=NULL, *lengths, *suffixes, *payload;
    size_t maximum_payload;
    uint32_t position=0;
    unsigned counts[ENC_LABELS], state=0, i;
    dha_predictor_state current;
    dha_frame_info frame;
    int status, prediction, q;
    if (written) *written=0;
    if (!info || !initial || !symbols || !gains || !output || !written)
        return DHA_E_ARGUMENT;
    status=dha_stream_validate(info);
    if (status != DHA_OK) return status;
    if (!samples || samples > info->frame_samples || channel >= info->channels)
        return DHA_E_ARGUMENT;
    /* Validate every old prediction and newly generated state, including the
     * final sample. There is no implicit reset or omitted first symbol. */
    current=*initial;
    for (i=0; i<samples; ++i) {
        unsigned symbol=symbols[i], gain=gains[i/ENC_BLOCK];
        if (symbol >= ENC_LABELS || gain < 1 || gain > 30) return DHA_E_PROFILE;
        status=dha_predict(info, &current, &prediction);
        if (status != DHA_OK) return status;
        q=prediction+enc_levels[symbol]*(int)gain;
        status=dha_advance(&current, q);
        if (status != DHA_OK) return status;
    }
    /* One allocation holds each sample's suffix length/value and a zeroed
     * payload. The upper bound includes up to6 suffix bits per sample and
     * one gain5 field per block; header bytes are written separately. */
    maximum_payload=(6u*(size_t)samples+5u*((samples+255u)/256u)+7u)/8u;
    inverse=(uint16_t*)malloc(ENC_LABELS*256u*sizeof(*inverse));
    storage=(uint8_t*)calloc(2u*(size_t)samples+maximum_payload, 1);
    if (!inverse || !storage) { status=DHA_E_MEMORY; goto done; }
    lengths=storage;
    suffixes=lengths+samples;
    payload=suffixes+samples;
    status=enc_inverse(info, inverse, counts);
    if (status != DHA_OK) goto done;
    /* Decode runs forward from its header state. Encoding runs backward from
     * terminal state0: invert each requested label, save the suffix leading
     * to the already known next state, then continue with the recovered old
     * state. The final recovered state becomes the packet's starting state. */
    for (i=samples; i>0; --i) {
        unsigned old=inverse[(unsigned)symbols[i-1u]*256u+state];
        unsigned n=info->ans[2u*old]&15u, base=info->ans[2u*old+1u];
        lengths[i-1u]=(uint8_t)n;
        suffixes[i-1u]=(uint8_t)(state-base);
        state=old;
    }
    memset(&frame, 0, sizeof(frame));
    frame.sequence=sequence;
    frame.samples=samples;
    frame.channel=channel;
    frame.kind=DHA_FRAME_DHA;
    frame.ans_state=(uint8_t)state;
    frame.initial=*initial;
    /* Emit the saved suffixes in playback order. A gain starts every block,
     * followed immediately by that block's sample suffixes; even the first
     * sample has a suffix, unlike the Z80 ROM's compiled-first wire layout. */
    for (i=0; i<samples; ++i) {
        if (!(i&255u)) enc_put_bits(payload, &position, gains[i/ENC_BLOCK], 5);
        enc_put_bits(payload, &position, suffixes[i], lengths[i]);
    }
    frame.payload_bits=position;
    frame.packet_bytes=DHA_FRAME_HEADER_BYTES+(position+7u)/8u;
    status=dha_write_packet(info, &frame, payload, (position+7u)/8u,
                            output, capacity, written);
done:
    /* Both pointers are NULL-safe here, including partial allocation failure. */
    free(storage);
    free(inverse);
    return status;
}

/** Predict from four borrowed full q histories using the shared table kernel.
 * Convert h[0..3] to the compact q/d1/d2/d3 state only after checking that the
 * differences fit signed8. Return nonzero for a valid prediction; prediction
 * is usable only on that return. Neither the history nor the tables change. */
static int enc_predict_history(const enc_config *config, const int16_t h[4], int *prediction) {
    dha_predictor_state state;
    int d1=(int)h[0]-h[1], d2=(int)h[0]-2*(int)h[1]+h[2];
    int d3=(int)h[0]-3*(int)h[1]+3*(int)h[2]-h[3];
    if (d1 < -128 || d1 > 127 || d2 < -128 || d2 > 127 || d3 < -128 || d3 > 127)
        return 0;
    state.q=h[0]; state.d1=(int8_t)d1; state.d2=(int8_t)d2; state.d3=(int8_t)d3;
    return dha_predict(config->info, &state, prediction) == DHA_OK;
}

/** Validate one candidate q and return its physical PCM error in q units.
 * h and target describe the current history and one input PCM16 sample.
 * Reject noncanonical q, any new signed8 difference, or a PCM16 error larger
 * than18*256. Success writes *error=(rounded_R2R_PCM16-target)/128 and returns
 * nonzero; failure leaves *error unchanged. This also checks the last sample
 * of a frame, for which no later prediction would expose an invalid state. */
static int enc_error(const int16_t h[4], int16_t target, int q, double *error) {
    int d1=q-h[0], d2=q-2*(int)h[0]+h[1];
    int d3=q-3*(int)h[0]+3*(int)h[1]-h[2];
    int difference;
    if (q < -256 || q > 254 || d1 < -128 || d1 > 127 ||
        d2 < -128 || d2 > 127 || d3 < -128 || d3 > 127) return 0;
    difference=(((q+257)/2)-128)*256-(int)target;
    if (difference < -ENC_CAP_PCM16 || difference > ENC_CAP_PCM16) return 0;
    *error=difference/128.0;
    return 1;
}

/** Shift a four-value newest-first history and prepend an already valid q.
 * Both arrays are caller-owned. next may equal old: assignments run from the
 * oldest slot toward the newest so in-place updates do not destroy inputs. */
static void enc_update(int16_t next[4], const int16_t old[4], int q) {
    next[3]=old[2]; next[2]=old[1]; next[1]=old[0]; next[0]=(int16_t)q;
}

/** qsort comparator for borrowed beam candidates, without mutating either.
 * Lower lookahead rank wins; parent slot then residual label provide
 * deterministic tie breaking. The caller owns the candidate array it sorts. */
static int enc_compare(const void *left, const void *right) {
    const enc_node *a=(const enc_node*)left, *b=(const enc_node*)right;
    if (a->rank != b->rank) return a->rank < b->rank ? -1 : 1;
    if (a->parent != b->parent) return a->parent < b->parent ? -1 : 1;
    return (int)a->symbol-(int)b->symbol;
}

/** qsort comparator for gain trials: lower estimated cost, then lower gain.
 * Neither borrowed record is changed; this makes equal-cost gain ranking
 * deterministic before the more expensive beam evaluations. */
static int enc_compare_gain(const void *left, const void *right) {
    const enc_gain *a=(const enc_gain*)left, *b=(const enc_gain*)right;
    if (a->cost != b->cost) return a->cost < b->cost ? -1 : 1;
    return a->gain-b->gain;
}

/** Find the cheapest valid continuation for a small lookahead horizon.
 * config, reference and h are borrowed; gain stays fixed within the current
 * block. Return zero at an empty horizon, ENC_INFINITY if no continuation
 * below that search sentinel survives, or the minimum sum of
 * error^2+penalty*bits[label] over at most
 * depth future outputs. Histories are local copies, so this changes no caller
 * state. Public options limit depth to2; lookahead never crosses a gain-block
 * boundary or reads beyond count input samples. */
static double enc_future(const enc_config *config, const int16_t *reference,
                         int count, const int16_t h[4], int gain, int depth) {
    double best=ENC_INFINITY;
    int prediction, symbol;
    if (!count || !depth) return 0.0;
    if (!enc_predict_history(config, h, &prediction)) return ENC_INFINITY;
    for (symbol=0; symbol<ENC_LABELS; ++symbol) {
        int q=prediction+enc_levels[symbol]*gain;
        int16_t next[4]; double error, cost;
        if (!enc_error(h, reference[0], q, &error)) continue;
        enc_update(next, h, q);
        cost=error*error+config->penalty*config->bits[symbol]+
            enc_future(config, reference+1, count-1, next, gain, depth-1);
        if (cost < best) best=cost;
    }
    return best;
}

/** Estimate a gain's usefulness with a cheap deterministic greedy trajectory.
 * Input PCM and initial history are borrowed; the evolving history is local.
 * Each choice ranks its immediate error/rate cost plus one future output,
 * but only the chosen immediate cost is accumulated, avoiding double counting.
 * Return that accumulated cost or ENC_INFINITY on failure. This is only a
 * shortlist heuristic, not the beam's final output; the beam separately uses
 * the requested lookahead depth0..2. */
static double enc_greedy(const enc_config *config, const int16_t *reference,
                         int count, const int16_t initial[4], int gain) {
    int16_t h[4]; double cost=0.0; int at;
    memcpy(h, initial, sizeof(h));
    for (at=0; at<count; ++at) {
        int prediction, symbol, best_q=0;
        double best=ENC_INFINITY, immediate_best=0.0;
        if (!enc_predict_history(config, h, &prediction)) return ENC_INFINITY;
        for (symbol=0; symbol<ENC_LABELS; ++symbol) {
            int q=prediction+enc_levels[symbol]*gain;
            int16_t next[4]; double error, immediate, rank;
            if (!enc_error(h, reference[at], q, &error)) continue;
            enc_update(next, h, q);
            immediate=error*error+config->penalty*config->bits[symbol];
            rank=immediate+enc_future(config, reference+at+1, count-at-1, next, gain, 1);
            if (rank < best) { best=rank; best_q=q; immediate_best=immediate; }
        }
        if (best >= ENC_INFINITY) return ENC_INFINITY;
        cost+=immediate_best;
        enc_update(h, h, best_q);
    }
    return cost;
}

/** Search one fixed-gain block with a bounded, history-deduplicated beam.
 * The caller supplies mutable scratch, output symbols[count] and final[4];
 * all input configuration, PCM and initial history remain read-only. Scratch
 * is reused across gain trials and may change even when the search fails.
 * Nodes retain committed cost separately from cost+future lookahead rank.
 * Return the winning committed cost and fill both outputs after a complete
 * block, or ENC_INFINITY without valid outputs if no candidates survive.
 * This finite beam is a search heuristic, not a proof of global optimality. */
static double enc_beam(const enc_config *config, enc_scratch *scratch,
                       const int16_t *reference, int count, const int16_t initial[4],
                       int gain, int width, int lookahead, uint8_t *symbols, int16_t final[4]) {
    int active=1, at, best;
    memset(scratch->previous, 0, sizeof(scratch->previous));
    memcpy(scratch->previous[0].h, initial, 4u*sizeof(int16_t));
    for (at=0; at<count; ++at) {
        int number=0, parent, symbol, i;
        for (parent=0; parent<active; ++parent) {
            const enc_node *old=&scratch->previous[parent];
            int prediction;
            if (!enc_predict_history(config, old->h, &prediction)) continue;
            for (symbol=0; symbol<ENC_LABELS; ++symbol) {
                enc_node next=*old;
                int q=prediction+enc_levels[symbol]*gain;
                double error;
                if (!enc_error(old->h, reference[at], q, &error)) continue;
                enc_update(next.h, old->h, q);
                /* Lookahead guides pruning only. It is not committed now,
                 * so later steps charge each actual output exactly once. */
                next.cost=old->cost+error*error+config->penalty*config->bits[symbol];
                next.rank=next.cost+enc_future(config, reference+at+1, count-at-1,
                                              next.h, gain, lookahead);
                if (next.rank >= ENC_INFINITY) continue;
                next.parent=(uint16_t)parent; next.symbol=(uint8_t)symbol;
                scratch->candidates[number++]=next;
            }
        }
        if (!number) return ENC_INFINITY;
        qsort(scratch->candidates, (size_t)number, sizeof(enc_node), enc_compare);
        active=0;
        for (i=0; i<number && active<width; ++i) {
            int duplicate=0, k;
            size_t cell;
            /* At this position and fixed gain, equal four-q histories have
             * the same possible future. Sorted rank therefore retains the
             * cheapest representative before the width limit is applied. */
            for (k=0; k<active; ++k)
                if (!memcmp(scratch->selected[k].h, scratch->candidates[i].h, 4u*sizeof(int16_t))) {
                    duplicate=1; break;
                }
            if (duplicate) continue;
            scratch->selected[active]=scratch->candidates[i];
            /* Record ancestry by selected slot, not by the candidate's
             * temporary position in the sorted array. */
            cell=(size_t)at*(size_t)width+(size_t)active;
            scratch->parents[cell]=scratch->candidates[i].parent;
            scratch->choices[cell]=scratch->candidates[i].symbol;
            ++active;
        }
        memcpy(scratch->previous, scratch->selected, (size_t)active*sizeof(enc_node));
    }
    best=0;
    for (at=1; at<active; ++at)
        if (scratch->previous[at].cost < scratch->previous[best].cost) best=at;
    memcpy(final, scratch->previous[best].h, 4u*sizeof(int16_t));
    {
        double cost=scratch->previous[best].cost;
        /* Walk the retained row slots backward to recover playback-order
         * labels. The full final history is already saved for the next block. */
        for (at=count-1; at>=0; --at) {
            size_t cell=(size_t)at*(size_t)width+(size_t)best;
            symbols[at]=scratch->choices[cell];
            best=scratch->parents[cell];
        }
        return cost;
    }
}

/** Choose a valid trajectory and gain for every block of one input frame.
 * info/options and PCM are borrowed, already validated by the public caller.
 * symbols[samples] and gains[ceil(samples/256)] are caller-owned scratch and
 * may be partially filled on failure. Reconstruct the four initial q values,
 * then carry each winning final history into the following block; only gain
 * changes at the boundary. The function owns and always frees the heap beam
 * workspace. Return DHA_OK, DHA_E_MEMORY, DHA_E_FORMAT for a missing label,
 * or DHA_E_PROFILE if the bounded search finds no surviving block trajectory.
 * The rate term uses -log2(label_state_count/256) from this stream's book;
 * it approximates ANS symbol cost, rather than exact finite suffix-bit cost. */
static int enc_search(const dha_stream_info *info, const dha_encoder_options *options,
                       const int16_t *pcm, uint16_t samples,
                       const dha_predictor_state *initial, uint8_t *symbols, uint8_t *gains) {
    enc_scratch *scratch;
    enc_config config;
    unsigned counts[ENC_LABELS]={0, 0, 0, 0, 0}, state;
    int16_t history[4];
    int first, status=DHA_OK;
    config.info=info; config.penalty=options->rate_penalty;
    /* Count decoder entries, not suffix ranges. The immutable file carries
     * this book, so custom valid tables also supply the search's rate prices. */
    for (state=0; state<256u; ++state) ++counts[info->ans[2u*state] >> 4];
    for (state=0; state<ENC_LABELS; ++state) {
        if (!counts[state]) return DHA_E_FORMAT;
        config.bits[state]=-log(counts[state]/256.0)/log(2.0);
    }
    /* Invert the finite-difference definitions: h0=q, h1=q-d1,
     * h2=q-2*d1+d2, h3=q-3*d1+3*d2-d3. */
    history[0]=initial->q;
    history[1]=(int16_t)((int)initial->q-initial->d1);
    history[2]=(int16_t)((int)initial->q-2*(int)initial->d1+initial->d2);
    history[3]=(int16_t)((int)initial->q-3*(int)initial->d1+3*(int)initial->d2-initial->d3);
    scratch=(enc_scratch*)malloc(sizeof(*scratch));
    if (!scratch) return DHA_E_MEMORY;
    for (first=0; first<samples; first+=ENC_BLOCK) {
        enc_gain ranked[30];
        uint8_t trial_symbols[ENC_BLOCK];
        int16_t trial_final[4], best_final[4];
        int count=samples-first < ENC_BLOCK ? samples-first : ENC_BLOCK;
        int gain, k, best_gain=0;
        double best=ENC_INFINITY;
        /* Rank all30 gains cheaply, then spend the beam on the shortlist.
         * If every shortlisted gain fails, keep trying the remaining gains
         * until at least one succeeds or all30 have been attempted. */
        for (gain=1; gain<=30; ++gain) {
            ranked[gain-1].gain=gain;
            ranked[gain-1].cost=enc_greedy(&config, pcm+first, count, history, gain);
        }
        qsort(ranked, 30, sizeof(enc_gain), enc_compare_gain);
        for (k=0; k<30; ++k) {
            double cost;
            if (k >= options->gain_candidates && best < ENC_INFINITY) break;
            gain=ranked[k].gain;
            cost=enc_beam(&config, scratch, pcm+first, count, history, gain,
                          options->beam_width, options->lookahead, trial_symbols, trial_final);
            if (cost < best) {
                best=cost; best_gain=gain;
                memcpy(symbols+first, trial_symbols, (size_t)count);
                memcpy(best_final, trial_final, sizeof(best_final));
            }
        }
        if (!best_gain) { status=DHA_E_PROFILE; break; }
        /* Commit only the best complete trial. No speculative history from
         * another gain can leak into the following256-sample block. */
        gains[first/ENC_BLOCK]=(uint8_t)best_gain;
        memcpy(history, best_final, sizeof(history));
    }
    free(scratch);
    return status;
}

/** Search without resetting reconstructed history or choosing PCM fallback.
 * Selection is shared with the framed encoder; replay uses the actual table
 * predictor again so the returned q and final differences are the decoder's
 * values, rather than a separately rounded approximation of the input PCM.
 * Output arrays may be partial on failure, but the caller's continuation
 * state is assigned only after every selected sample validates successfully. */
int dha_encode_trajectory(const dha_stream_info *info, const dha_encoder_options *options,
                          const dha_predictor_state *initial,
                          const int16_t *pcm, uint16_t samples,
                          uint8_t *symbols, uint8_t *gains, int16_t *q,
                          dha_predictor_state *final_state) {
    dha_encoder_options defaults;
    dha_predictor_state current;
    unsigned i;
    int status, prediction;
    if (!info || !initial || !pcm || !symbols || !gains || !q || !final_state ||
        !samples || samples > DHA_MAX_FRAME_SAMPLES) return DHA_E_ARGUMENT;
    status=dha_stream_validate(info);
    if (status != DHA_OK) return status;
    if (!options) { dha_encoder_default(&defaults); options=&defaults; }
    if (!enc_options_valid(options)) return DHA_E_ARGUMENT;
    status=dha_predict(info, initial, &prediction);
    if (status != DHA_OK) return status;
    status=enc_search(info, options, pcm, samples, initial, symbols, gains);
    if (status != DHA_OK) return status;
    current=*initial;
    for (i=0; i<samples; ++i) {
        status=dha_predict(info, &current, &prediction);
        if (status != DHA_OK) return status;
        q[i]=(int16_t)(prediction+enc_levels[symbols[i]]*(int)gains[i/ENC_BLOCK]);
        status=dha_advance(&current, q[i]);
        if (status != DHA_OK) return status;
    }
    *final_state=current;
    return DHA_OK;
}

/** Encode one channel's contiguous PCM16 samples into an independent packet.
 * info, options and pcm are borrowed read-only; options==NULL selects defaults.
 * samples must fit the stream's configured frame size. channel and sequence
 * identify this packet, while the caller handles interchannel/group ordering.
 * Input rate is unchanged: this function performs no filtering or resampling.
 * It owns and frees its temporary symbols, gains, packet and search workspace.
 * On DHA_OK, output contains a complete CRC-protected packet, *written is its
 * byte count, and optional frame receives its metadata. Errors leave *written
 * zero when supplied and do not publish frame metadata. Errors distinguish
 * arguments, stream format, buffer capacity, allocation and search profile.
 * If enabled, PCM16 fallback preserves the exact input when search fails or
 * the predictive payload is no smaller than PCM16. With fallback disabled,
 * an infeasible search returns DHA_E_PROFILE, but valid DHA may expand. */
int dha_encode_frame(const dha_stream_info *info, const dha_encoder_options *options,
                     const int16_t *pcm, uint16_t samples, uint8_t channel,
                     uint32_t sequence, uint8_t *output, size_t capacity,
                     size_t *written, dha_frame_info *frame) {
    dha_encoder_options defaults;
    dha_predictor_state initial;
    dha_frame_info parsed;
    uint8_t *scratch=NULL, *symbols, *gains, *packet;
    size_t packet_bytes=0;
    unsigned i;
    int status, initial_q;
    if (written) *written=0;
    if (!info || !pcm || !output || !written) return DHA_E_ARGUMENT;
    status=dha_stream_validate(info);
    if (status != DHA_OK) return status;
    if (!samples || samples > info->frame_samples || channel >= info->channels) return DHA_E_ARGUMENT;
    if (!options) { dha_encoder_default(&defaults); options=&defaults; }
    if (!enc_options_valid(options)) return DHA_E_ARGUMENT;
    if (capacity < DHA_FRAME_HEADER_BYTES) return DHA_E_BUFFER;
    /* Build into private storage first. Only a successful final packet is
     * copied to the caller's output; search trials do not modify that buffer. */
    scratch=(uint8_t*)malloc((size_t)samples+(samples+255u)/256u+DHA_MAX_FRAME_BYTES);
    if (!scratch) return DHA_E_MEMORY;
    symbols=scratch; gains=symbols+samples; packet=gains+(samples+255u)/256u;
    /* Signed-safe nearest rounding, ties towards +infinity. A flat initial
     * history means q1=q2=q3=q4 and all three differences are exactly zero. */
    initial_q=((int)pcm[0]+32768+64)/128-256;
    if (initial_q < -256) initial_q=-256;
    if (initial_q > 254) initial_q=254;
    memset(&initial, 0, sizeof(initial)); initial.q=(int16_t)initial_q;
    status=enc_search(info, options, pcm, samples, &initial, symbols, gains);
    if (status == DHA_OK) {
        /* Entropy packing is separate from lossy trajectory selection. It
         * revalidates the full path and measures actual suffix bytes before
         * deciding whether a PCM16 fallback is preferable. */
        status=dha_pack_frame(info, &initial, symbols, gains, samples, channel, sequence,
                              packet, DHA_MAX_FRAME_BYTES, &packet_bytes);
        /* Both frame kinds have the same header size, so payload comparison
         * alone decides whether the predictive packet saves any bytes. */
        if (status == DHA_OK && options->allow_pcm_fallback &&
            packet_bytes-DHA_FRAME_HEADER_BYTES >= 2u*(size_t)samples)
            status=DHA_E_PROFILE;
    }
    if (status == DHA_E_PROFILE && options->allow_pcm_fallback) {
        /* Raw frames have no predictor/ANS dependency: zero their initial
         * state and write the original signed words explicitly little-endian.
         * Format, memory and argument failures are not hidden by fallback. */
        memset(&parsed, 0, sizeof(parsed));
        parsed.kind=DHA_FRAME_PCM16; parsed.channel=channel; parsed.samples=samples;
        parsed.sequence=sequence; parsed.payload_bits=16u*samples;
        parsed.packet_bytes=DHA_FRAME_HEADER_BYTES+2u*samples;
        for (i=0; i<samples; ++i) dha_put16(packet+2u*i, (uint16_t)pcm[i]);
        status=dha_write_packet(info, &parsed, packet, 2u*samples, output, capacity, written);
        if (status == DHA_OK && frame) *frame=parsed;
    } else if (status == DHA_OK) {
        if (capacity < packet_bytes) status=DHA_E_BUFFER;
        else {
            /* Parse the finished private packet to return the same metadata
             * a decoder observes, then publish packet bytes and success count. */
            status=dha_frame_read(info, packet, packet_bytes, &parsed);
            if (status == DHA_OK) {
                memmove(output, packet, packet_bytes);
                *written=packet_bytes;
                if (frame) *frame=parsed;
            }
        }
    }
    free(scratch);
    return status;
}
