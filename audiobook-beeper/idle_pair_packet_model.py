"""Opt-in zero-area-error word pair for the unchanged idle feedback cycle.

The pair is selected without source audio from every duty-224/duty-225 pair.
Only the two bin-32 words change; every feedback successor stays unchanged.
"""
import numpy as np

from neutral_packet_model import ORDINARY_PENTAGON_HOLDS, PHYSICAL_CPU_HZ, on_time_tstates


IDLE_PAIR_WORDS = (0x569A, 0x56AD)
IDLE_PAIR_STATES = (16, 17)


def validate_idle_pair_packet(model):
    """Return the frozen pair for an enabled model, otherwise None."""
    if model is None or 'idle_pair_words' not in model:
        return None
    if any(key in model for key in ('idle_cycle_word', 'neutral_packet_word', 'neutral_packet_successor')):
        raise ValueError('Idle pair cannot mix prior idle-cycle or neutral packet flags')
    pair = model['idle_pair_words']
    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
        raise ValueError('Idle pair requires a list or tuple of exactly two words')
    if any(type(word) is not int or not 0 <= word <= 65535 for word in pair):
        raise ValueError('Idle pair words must be builtin uint16 integers')
    pair = tuple(pair)
    if tuple(map(on_time_tstates, pair)) != (224, 225):
        raise ValueError('Idle pair requires ordered on-times 224 and 225 of 449 T states')
    if pair != IDLE_PAIR_WORDS:
        raise ValueError('Idle pair requires the previously frozen words 0x569A and 0x56AD')
    if model.get('family', 'integral') != 'integral':
        raise ValueError('Idle pair requires the integral PDM family')
    bins = model.get('pcm_bins', 64)
    if type(bins) is not int or bins != 64:
        raise ValueError('Idle pair requires 64 PCM bins')
    if type(model.get('pcm_quantization_bias')) is not int or model['pcm_quantization_bias'] != 512:
        raise ValueError('Idle pair requires centered PCM bias 512')
    for key, default, expected in (('pcm_origin', .5, 0), ('extent', 1., 1), ('beta', .5, .5)):
        value = model.get(key, default)
        if type(value) not in (int, float) or value != expected:
            raise ValueError(f'Idle pair requires {key}={expected}')
    try:
        holds = tuple(model.get('holds', ()))
        clip = tuple(model.get('q_clip', (0, 15)))
    except TypeError:
        raise ValueError('Idle timing and state bounds must be sequences') from None
    if holds != ORDINARY_PENTAGON_HOLDS:
        raise ValueError('Idle pair requires the exact counted 449-T Pentagon holds')
    if clip != (0, 15) or any(type(value) is not int for value in clip):
        raise ValueError('Idle pair requires the standard integer q_clip 0..15')
    return pair


def apply_idle_pair_packet(words, nxt, model):
    """Copy exactly two words while preserving the entire successor graph.

    Require the original bin-32 state cycle 16→17→16. An absent option is an
    identity operation; prior independent mechanisms remain unchanged.
    """
    pair = validate_idle_pair_packet(model)
    if pair is None:
        return words, nxt
    current, successors = np.asarray(words), np.asarray(nxt)
    if (current.shape != (64, 32) or successors.shape != (64, 32) or
            not np.issubdtype(current.dtype, np.integer) or
            not np.issubdtype(successors.dtype, np.integer) or
            np.any(current < 0) or np.any(current > 65535) or
            np.any(successors < 0) or np.any(successors > 31)):
        raise ValueError('Idle pair requires uint16 words and closed 64-bin/32-state tables')
    if int(successors[32, 16]) != 17 or int(successors[32, 17]) != 16:
        raise ValueError('Idle pair requires the original bin-32 successor cycle 16→17→16')
    copied = current.copy()
    copied[32, 16], copied[32, 17] = pair
    return copied, nxt


def select_idle_pair():
    """Enumerate all 179776 duty-balanced pairs without source audio.

    A two-packet periodic solve gives the 32 pulse-midpoint outputs. Expanded
    weighted quadratic products score every pair without a 424×424×32
    tensor. A complement plus packet swap gives the same variance and raw
    second moment and negates the mean. Share the canonical score exactly,
    so floating roundoff cannot decide that mathematical tie.
    """
    from build_pdm import CPU_CLOCK
    from ima_waveform_encoder import WaveformModel

    holds = np.asarray(ORDINARY_PENTAGON_HOLDS, dtype=np.int64)
    all_words = np.arange(65536, dtype=np.int64)
    all_bits = ((all_words[:, None] >> np.arange(15, -1, -1)) & 1).astype(np.int64)
    on = all_bits @ holds
    first, second = all_words[on == 224], all_words[on == 225]
    bits0, bits1 = all_bits[first].astype(float) * 2 - 1, all_bits[second].astype(float) * 2 - 1
    reference_holds = holds * CPU_CLOCK / PHYSICAL_CPU_HZ
    analog = WaveformModel()
    a, b, l, r = analog.packet(reference_holds)
    periodic = np.eye(6) - a @ a
    h0 = np.linalg.solve(periodic, a @ b)
    h1 = np.linalg.solve(periodic, b)
    u = np.r_[l @ h0 + r, l @ (a @ h0 + b)]
    v = np.r_[l @ h1, l @ a @ h1 + r]
    p, q = bits0 @ u.T, bits1 @ v.T
    weights = np.r_[holds, holds] / 898
    mean = (p @ weights)[:, None] + (q @ weights)[None, :]
    second_moment = ((p * p) @ weights)[:, None] + ((q * q) @ weights)[None, :] + 2 * (p * weights) @ q.T
    variance = second_moment - mean * mean
    pair_ids = (first[:, None] << 16) + second[None, :]
    partner_ids = ((65535 - second)[None, :] << 16) + (65535 - first)[:, None]
    partner_rows = np.searchsorted(first, 65535 - second)
    partner_columns = np.searchsorted(second, 65535 - first)
    canonical = pair_ids <= partner_ids
    # Work from the unmodified matrices for each symmetry assignment.
    variance = np.where(canonical, variance, variance[partner_rows[None, :], partner_columns[:, None]])
    second_moment = np.where(canonical, second_moment,
                             second_moment[partner_rows[None, :], partner_columns[:, None]])
    mean = np.where(canonical, mean, -mean[partner_rows[None, :], partner_columns[:, None]])
    mean = np.where(pair_ids == partner_ids, 0., mean)
    ranking = np.lexsort((pair_ids.ravel(), variance.ravel()))
    row, column = np.unravel_index(ranking[0], variance.shape)
    selected = int(first[row]), int(second[column])
    if selected != IDLE_PAIR_WORDS:
        raise RuntimeError('Analytic selector no longer reproduces the frozen idle pair')
    selected_id = int(pair_ids[row, column])
    selected_partner = int(partner_ids[row, column])
    top = []
    for item in ranking[:20]:
        i, j = np.unravel_index(item, variance.shape)
        top.append(dict(words=[int(first[i]), int(second[j])],
                        hex_words=[f'0x{int(first[i]):04X}', f'0x{int(second[j]):04X}'],
                        pair_id=int(pair_ids[i, j]), variance=float(variance[i, j]),
                        rms=float(np.sqrt(variance[i, j])), second_moment=float(second_moment[i, j]),
                        midpoint_weighted_mean=float(mean[i, j])))
    next_distinct = next(int(item) for item in ranking
                         if int(pair_ids.ravel()[item]) not in (selected_id, selected_partner))
    report = dict(
        date='2026-10-14', source_audio_opened=False, all_words_enumerated=65536,
        duty224_words=len(first), duty225_words=len(second), pairs_enumerated=int(variance.size),
        complement_swap_fixed_pairs=int(np.count_nonzero(pair_ids == partner_ids)),
        complement_swap_orbits=int(np.count_nonzero(canonical)),
        selected_words=list(selected), selected_hex_words=[f'0x{word:04X}' for word in selected],
        selected_pair_id=selected_id, complement_swap_words=[65535-selected[1], 65535-selected[0]],
        selected_on_tstates=[224, 225], packet_period_tstates=449, pair_period_tstates=898,
        pair_on_tstates=449, mean_duty=.5, signed_pair_area_error_tstates=0,
        physical_cpu_hz=PHYSICAL_CPU_HZ, reference_cpu_hz=CPU_CLOCK,
        physical_pair_period_seconds=898 / PHYSICAL_CPU_HZ,
        integer_holds=holds.tolist(), reference_holds=reference_holds.tolist(),
        selected_estimated_variance=float(variance[row, column]),
        selected_estimated_rms=float(np.sqrt(variance[row, column])),
        selected_second_moment=float(second_moment[row, column]),
        selected_midpoint_weighted_mean=float(mean[row, column]),
        next_distinct_variance_ratio=float(variance.ravel()[next_distinct] / variance[row, column]),
        solve_condition=float(np.linalg.cond(periodic)),
        solve_residual_max=float(max(np.max(abs(periodic @ h0 - a @ b)), np.max(abs(periodic @ h1 - b)))),
        spectral_radius_two_packets=float(max(abs(np.linalg.eigvals(a @ a)))),
        objective='Duration-weighted variance over the 32 steady-state pulse midpoints of a two-packet pair',
        formula='s0=(I-A*A)^-1(A*B*w16+B*w17); y0=L*s0+R*w16; s1=A*s0+B*w16; y1=L*s1+R*w17',
        scoring='Expanded weighted quadratic products; variance=second_moment-midpoint_weighted_mean^2',
        tie_rule='Exact complement-plus-swap symmetry, then ascending pair_id=(word16<<16)|word17',
        filter='Existing 6-state analytic 70-Hz high-pass and two 4500-Hz Butterworth low-pass pairs; unchanged bandwidth',
        constraints=dict(state16_on_tstates=224, state17_on_tstates=225, total_on_tstates=449,
                         pair_period_tstates=898, exact_half_duty=True, feedback_successors=[17, 16],
                         changed_cells=[[32, 16], [32, 17]], all_other_words_and_successors_preserved=True),
        top_candidates=top,
        scope='Analytic ordinary-packet selection only. Midpoint quadrature is an estimate; page/bank excursions, complete-source FFmpeg metrics, AM/flutter/background and actual playback remain separate acceptance. No release or universal quality claim.'
    )
    arrays = dict(first_words=first, second_words=second, variance=variance, second_moment=second_moment,
                  midpoint_weighted_mean=mean, pair_ids=pair_ids, ranking=ranking,
                  a=a, b=b, l=l, r=r, steady_word16_basis=h0, steady_word17_basis=h1)
    return report, arrays
