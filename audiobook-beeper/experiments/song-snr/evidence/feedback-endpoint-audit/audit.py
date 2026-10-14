"""Replay packet feedback endpoints exactly; this is a source-free diagnosis.

The real player follows the stored successor table. It does not calculate
these fractions. This audit asks whether forced pulse words still have the
endpoint interpretation used to generate that table, and cannot establish
audio quality or a causal explanation for measured regressions by itself.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'audiobook-beeper'))

from probe_feedback_packets import integral_table


HOLDS = (36, 28, 28, 31, 24, 26, 22, 46, 22, 26, 22, 30, 31, 27, 34, 16)
EPSILON = Fraction(1, 10**12)


def exact_packet(level, state, word=None):
    """Generate or force 16 bits using the original integral recurrence.

    q is the duration-weighted accumulated error; recent is the previous
    residual. Endpoint rounding exactly reproduces the documented positive
    epsilon, floor and clipping of the zero-origin table. Forced words may
    depart from its individual decision rule even when endpoints agree.
    """
    target = Fraction(level, 64)
    q = Fraction(state // 2 - 8, 8)
    recent = Fraction(-1 if state % 2 == 0 else 1, 2)
    generated = 0
    peak = Fraction(0)
    departures = 0
    for position, hold in enumerate(HOLDS):
        weight = Fraction(16 * hold, sum(HOLDS))
        value = target + q / weight + recent / 2
        natural_bit = int(value + EPSILON >= Fraction(1, 2))
        bit = natural_bit if word is None else (word >> (15 - position)) & 1
        departures += bit != natural_bit
        recent = value - bit
        q += weight * (target - bit)
        peak = max(peak, abs(recent))
        generated = (generated << 1) | bit
    qcode = min(15, max(0, (8 * q + Fraction(17, 2) + EPSILON).__floor__()))
    rcode = min(1, max(0, (recent + 1 + EPSILON).__floor__()))
    return dict(word=generated, successor=2 * qcode + rcode, q=q,
                recent=recent, peak=peak, individual_decision_departures=departures)


def rational(value):
    return dict(numerator=value.numerator, denominator=value.denominator,
                decimal=float(value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('report.json'))
    args = parser.parse_args()
    words, successors, _ = integral_table(64, 2, holds=HOLDS, beta=.5,
                                         extent=1., pcm_origin=0)
    # Check the full original table before interpreting modified words.
    for level in range(64):
        for state in range(32):
            replay = exact_packet(level, state)
            assert replay['word'] == int(words[level, state]), (level, state, 'word')
            assert replay['successor'] == int(successors[level, state]), (level, state, 'successor')
    assert [int(words[32, state]) for state in (16, 17)] == [0x6AD5, 0x952A]
    cases = []
    for name, pair in [('original', (0x6AD5, 0x952A)),
                       ('one_word_idle', (0x56AD, 0x56AD)),
                       ('zero_mean_pair', (0x569A, 0x56AD))]:
        for state, word in zip((16, 17), pair):
            replay = exact_packet(32, state, word)
            retained = int(successors[32, state])
            on = sum(hold for pos, hold in enumerate(HOLDS) if word >> (15-pos) & 1)
            cases.append(dict(mechanism=name, initial_state=state,
                              word=word, hex_word=f'0x{word:04X}', on_tstates=on,
                              retained_successor=retained, derived_successor=replay['successor'],
                              derived_endpoint_matches_retained_successor=replay['successor']==retained,
                              final_q=rational(replay['q']), final_recent=rational(replay['recent']),
                              maximum_internal_absolute_recent=rational(replay['peak']),
                              individual_decision_departures=replay['individual_decision_departures']))
    domains = []
    for state, duty in ((16, 224), (17, 225)):
        eligible = []
        for word in range(65536):
            if sum(hold for pos, hold in enumerate(HOLDS) if word >> (15-pos) & 1) != duty:
                continue
            replay = exact_packet(32, state, word)
            eligible.append((word, replay['successor']))
        allowed = [word for word, nxt in eligible if nxt == int(successors[32, state])]
        domains.append(dict(initial_state=state, required_on_tstates=duty,
                            words_with_required_duty=len(eligible),
                            required_endpoint_successor=int(successors[32, state]),
                            endpoint_consistent_words=len(allowed), allowed_words=allowed))
    source_files = ['probe_feedback_packets.py', 'idle_cycle_packet_model.py', 'idle_pair_packet_model.py']
    hashes = {name: hashlib.sha256((ROOT/'audiobook-beeper'/name).read_bytes()).hexdigest()
              for name in source_files}
    hashes['audit.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report = dict(date='2026-10-14', source_audio_opened=False, complete=True,
                  exact_arithmetic='Fraction; epsilon exactly 1/10^12; floor and clipping reproduced',
                  all_original_word_and_successor_cells_verified=2048,
                  holds=list(HOLDS), beta=.5, extent=1., pcm_origin=0, level=32,
                  cases=cases, endpoint_consistent_duty_domains=domains,
                  source_sha256=hashes,
                  finding='Forced 0x56AD at state17 ends with positive recent error and derives state17, whereas both measured override mechanisms retain successor16. Original packets reproduce their endpoints exactly.',
                  next_hypothesis='Constrain a separately frozen source-free duty-balanced pair selector to endpoint-consistent successors before any new source comparison.',
                  limits='Conceptual recurrence diagnosis only: hardware stores and follows the original successor graph exactly. Endpoint consistency is neither proof of perceptual improvement nor equivalence to the original individual bit decisions. No source, filter, clock, measured outputs or candidate flags are changed.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(original_cells_verified=2048,
                          cases=[{k: row[k] for k in ('mechanism','initial_state','hex_word','retained_successor','derived_successor')} for row in cases],
                          domain_sizes=[row['endpoint_consistent_words'] for row in domains]), indent=2))


if __name__ == '__main__':
    main()
