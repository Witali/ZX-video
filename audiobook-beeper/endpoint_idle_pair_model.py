"""Source-free idle pair with exact conceptual feedback endpoint consistency.

Only bin-32/state-16 and bin-32/state-17 words change. The endpoint condition
matches the original successor labels; it does not require each forced bit
to obey the original greedy bit rule, or prove audio quality/stability.
"""
from fractions import Fraction
from math import floor

import numpy as np

from idle_pair_packet_model import select_idle_pair
from neutral_packet_model import ORDINARY_PENTAGON_HOLDS, on_time_tstates


ENDPOINT_IDLE_PAIR_WORDS = (0x670D, 0x969C)
ENDPOINT_IDLE_PAIR_STATES = (16, 17)
ENDPOINT_EPSILON = Fraction(1, 10**12)


def derive_idle_endpoint(word, state):
    """Replay one forced word exactly from the table's state representative.

    Duration weights are 16*hold/449. Bin 32 on the zero-origin 64-bin grid
    has x=1/2; states 16 and 17 both represent q=0 and recent=−1/2,+1/2.
    Round and clip exactly as integral_table, including epsilon 1/10^12.
    """
    if type(word) is not int or not 0 <= word <= 65535:
        raise ValueError('Endpoint word must be a builtin uint16 integer')
    if type(state) is not int or state not in ENDPOINT_IDLE_PAIR_STATES:
        raise ValueError('Endpoint replay requires idle state 16 or 17')
    q = Fraction(state // 2 - 8, 8)
    recent = Fraction(-1, 2) if state == 16 else Fraction(1, 2)
    peak_q, peak_recent = abs(q), abs(recent)
    mismatches = []
    for slot, (shift, hold) in enumerate(zip(range(15, -1, -1), ORDINARY_PENTAGON_HOLDS)):
        weight = Fraction(16 * hold, 449)
        u = Fraction(1, 2) + q / weight + recent / 2
        bit = (word >> shift) & 1
        if bit != int(u >= Fraction(1, 2) - ENDPOINT_EPSILON):
            mismatches.append(slot)
        recent = u - bit
        q += weight * (Fraction(1, 2) - bit)
        peak_q, peak_recent = max(peak_q, abs(q)), max(peak_recent, abs(recent))
    qcode = min(15, max(0, floor(q * 8 + Fraction(17, 2) + ENDPOINT_EPSILON)))
    rcode = min(1, max(0, floor(recent + 1 + ENDPOINT_EPSILON)))
    return dict(q=q, recent=recent, qcode=qcode, rcode=rcode, successor=qcode * 2 + rcode,
                peak_absolute_q=peak_q, peak_absolute_recent=peak_recent,
                greedy_bit_rule_mismatch_slots=mismatches)


def validate_endpoint_idle_pair(model):
    """Return the frozen endpoint-consistent pair, or None when absent."""
    if model is None or 'endpoint_idle_pair_words' not in model:
        return None
    previous = ('idle_pair_words', 'idle_cycle_word', 'neutral_packet_word', 'neutral_packet_successor')
    if any(key in model for key in previous):
        raise ValueError('Endpoint idle pair cannot mix prior packet flags')
    pair = model['endpoint_idle_pair_words']
    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
        raise ValueError('Endpoint idle pair requires a list or tuple of exactly two words')
    if any(type(word) is not int or not 0 <= word <= 65535 for word in pair):
        raise ValueError('Endpoint idle pair words must be builtin uint16 integers')
    pair = tuple(pair)
    if tuple(map(on_time_tstates, pair)) != (224, 225):
        raise ValueError('Endpoint idle pair requires ordered duties 224/225 of 449 T states')
    if pair != ENDPOINT_IDLE_PAIR_WORDS:
        raise ValueError('Endpoint idle pair requires frozen words 0x670D and 0x969C')
    if tuple(derive_idle_endpoint(word, state)['successor']
             for word, state in zip(pair, ENDPOINT_IDLE_PAIR_STATES)) != (17, 16):
        raise ValueError('Endpoint idle pair must derive the original successor cycle 17/16')
    if model.get('family', 'integral') != 'integral':
        raise ValueError('Endpoint idle pair requires the integral PDM family')
    bins = model.get('pcm_bins', 64)
    if type(bins) is not int or bins != 64:
        raise ValueError('Endpoint idle pair requires 64 PCM bins')
    if type(model.get('pcm_quantization_bias')) is not int or model['pcm_quantization_bias'] != 512:
        raise ValueError('Endpoint idle pair requires centered PCM bias 512')
    for key, default, expected in (('pcm_origin', .5, 0), ('extent', 1., 1), ('beta', .5, .5)):
        value = model.get(key, default)
        if type(value) not in (int, float) or value != expected:
            raise ValueError(f'Endpoint idle pair requires {key}={expected}')
    try:
        holds, clip = tuple(model.get('holds', ())), tuple(model.get('q_clip', (0, 15)))
    except TypeError:
        raise ValueError('Endpoint timing and state bounds must be sequences') from None
    if holds != ORDINARY_PENTAGON_HOLDS:
        raise ValueError('Endpoint idle pair requires the exact 449-T Pentagon holds')
    if clip != (0, 15) or any(type(value) is not int for value in clip):
        raise ValueError('Endpoint idle pair requires the standard integer q_clip 0..15')
    return pair


def apply_endpoint_idle_pair(words, nxt, model):
    """Copy two words; preserve all successors and other 2046 words."""
    pair = validate_endpoint_idle_pair(model)
    if pair is None:
        return words, nxt
    current, successors = np.asarray(words), np.asarray(nxt)
    if (current.shape != (64, 32) or successors.shape != (64, 32) or
            not np.issubdtype(current.dtype, np.integer) or
            not np.issubdtype(successors.dtype, np.integer) or
            np.any(current < 0) or np.any(current > 65535) or
            np.any(successors < 0) or np.any(successors > 31)):
        raise ValueError('Endpoint idle pair requires uint16 words and closed 64-bin/32-state tables')
    if int(successors[32, 16]) != 17 or int(successors[32, 17]) != 16:
        raise ValueError('Endpoint idle pair requires original bin-32 successor cycle 16→17→16')
    copied = current.copy()
    copied[32, 16], copied[32, 17] = pair
    return copied, nxt


def select_endpoint_idle_pair():
    """Filter exact endpoint labels, then rank the unchanged analytic scores.

    Reuse the previous complete pair quadratic computation and its exact
    complement-plus-swap score sharing. Endpoint constraints depend only on
    counted timing and state representatives; no source audio participates.
    """
    previous_report, previous = select_idle_pair()
    all_first, all_second = previous['first_words'], previous['second_words']
    first_endpoints = [derive_idle_endpoint(int(word), 16) for word in all_first]
    second_endpoints = [derive_idle_endpoint(int(word), 17) for word in all_second]
    first_keep = np.asarray([i for i, item in enumerate(first_endpoints) if item['successor'] == 17], dtype=np.int64)
    second_keep = np.asarray([i for i, item in enumerate(second_endpoints) if item['successor'] == 16], dtype=np.int64)
    first, second = all_first[first_keep], all_second[second_keep]
    if set(map(int, second)) != {65535 - int(word) for word in first}:
        raise RuntimeError('Endpoint candidate set is not closed under complement-plus-swap')
    indices = np.ix_(first_keep, second_keep)
    variance, moments, means = (previous[key][indices] for key in
                               ('variance', 'second_moment', 'midpoint_weighted_mean'))
    pair_ids = previous['pair_ids'][indices]
    ranking = np.lexsort((pair_ids.ravel(), variance.ravel()))
    row, column = np.unravel_index(ranking[0], variance.shape)
    selected = int(first[row]), int(second[column])
    if selected != ENDPOINT_IDLE_PAIR_WORDS:
        raise RuntimeError('Endpoint selector no longer reproduces the frozen pair')
    partner_ids = ((65535 - second)[None, :] << 16) + (65535 - first)[:, None]
    canonical = pair_ids <= partner_ids
    selected_id, selected_partner = int(pair_ids[row, column]), int(partner_ids[row, column])
    next_distinct = next(int(item) for item in ranking
                         if int(pair_ids.ravel()[item]) not in (selected_id, selected_partner))
    top = []
    for item in ranking[:20]:
        i, j = np.unravel_index(item, variance.shape)
        top.append(dict(words=[int(first[i]), int(second[j])],
                        hex_words=[f'0x{int(first[i]):04X}', f'0x{int(second[j]):04X}'],
                        pair_id=int(pair_ids[i, j]), variance=float(variance[i, j]),
                        rms=float(np.sqrt(variance[i, j])), second_moment=float(moments[i, j]),
                        midpoint_weighted_mean=float(means[i, j])))
    endpoint_distances = [abs(item['recent'] + ENDPOINT_EPSILON)
                          for item in first_endpoints + second_endpoints]
    report = dict(
        date='2026-10-14', source_audio_opened=False, all_words_enumerated=65536,
        duty224_words_before_filter=len(all_first), duty225_words_before_filter=len(all_second),
        state16_endpoint17_words=len(first), state17_endpoint16_words=len(second),
        rejected_state16_words=len(all_first) - len(first), rejected_state17_words=len(all_second) - len(second),
        pairs_enumerated=int(variance.size), original_unfiltered_pairs=previous_report['pairs_enumerated'],
        complement_swap_candidate_closure=True,
        complement_swap_fixed_pairs=int(np.count_nonzero(pair_ids == partner_ids)),
        complement_swap_orbits=int(np.count_nonzero(canonical)),
        endpoint_arithmetic='Exact Fraction recurrence, weights16*hold/449, x1/2,beta1/2,q0,recent±1/2',
        endpoint_epsilon=str(ENDPOINT_EPSILON),
        endpoint_quantization='qcode=clip(floor(8*q+8.5+epsilon),0,15); rcode=clip(floor(recent+1+epsilon),0,1)',
        endpoint_boundary_minimum_absolute_distance=str(min(endpoint_distances)),
        endpoint_boundary_minimum_absolute_distance_float=float(min(endpoint_distances)),
        selected_words=list(selected), selected_hex_words=[f'0x{word:04X}' for word in selected],
        selected_pair_id=selected_id, complement_swap_words=[65535-selected[1], 65535-selected[0]],
        selected_on_tstates=[224, 225], derived_successors=[17, 16],
        packet_period_tstates=449, pair_period_tstates=898, pair_on_tstates=449,
        mean_duty=.5, signed_pair_area_error_tstates=0,
        physical_cpu_hz=previous_report['physical_cpu_hz'], reference_cpu_hz=previous_report['reference_cpu_hz'],
        physical_pair_period_seconds=previous_report['physical_pair_period_seconds'],
        integer_holds=previous_report['integer_holds'], reference_holds=previous_report['reference_holds'],
        selected_estimated_variance=float(variance[row, column]),
        selected_estimated_rms=float(np.sqrt(variance[row, column])),
        selected_second_moment=float(moments[row, column]), selected_midpoint_weighted_mean=float(means[row, column]),
        next_distinct_variance_ratio=float(variance.ravel()[next_distinct] / variance[row, column]),
        solve_condition=previous_report['solve_condition'], solve_residual_max=previous_report['solve_residual_max'],
        spectral_radius_two_packets=previous_report['spectral_radius_two_packets'],
        objective=previous_report['objective'], formula=previous_report['formula'],
        scoring=previous_report['scoring'], tie_rule=previous_report['tie_rule'], filter=previous_report['filter'],
        constraints=dict(state16_on_tstates=224, state17_on_tstates=225, state16_derived_successor=17,
                         state17_derived_successor=16, changed_cells=[[32,16],[32,17]],
                         all_other_words_and_successors_preserved=True),
        top_candidates=top,
        scope='Endpoint labels are conceptually consistent but individual forced bits may violate the original greedy bit rule. Midpoint variance is an analytic ordinary-packet estimate; complete-source noise, AM/flutter/background and actual playback remain separate acceptance. No release or universal quality claim.'
    )
    arrays = dict(first_words=first, second_words=second, variance=variance, second_moment=moments,
                  midpoint_weighted_mean=means, pair_ids=pair_ids, ranking=ranking,
                  all_duty224_words=all_first, all_duty225_words=all_second,
                  duty224_derived_successors=np.asarray([item['successor'] for item in first_endpoints], dtype=np.int64),
                  duty225_derived_successors=np.asarray([item['successor'] for item in second_endpoints], dtype=np.int64),
                  duty224_endpoint_recent_exact=np.asarray([str(item['recent']) for item in first_endpoints]),
                  duty225_endpoint_recent_exact=np.asarray([str(item['recent']) for item in second_endpoints]),
                  state16_kept_indices=first_keep, state17_kept_indices=second_keep,
                  **{key: previous[key] for key in ('a', 'b', 'l', 'r', 'steady_word16_basis', 'steady_word17_basis')})
    return report, arrays
