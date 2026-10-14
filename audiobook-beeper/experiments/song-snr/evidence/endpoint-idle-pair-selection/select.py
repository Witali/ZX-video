"""Reproduce endpoint-filtered idle-pair selection without audio sources."""
import argparse
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(ROOT / 'audiobook-beeper'), str(ROOT / 'toolkit')]

import numpy as np
from endpoint_idle_pair_model import (ENDPOINT_IDLE_PAIR_WORDS, derive_idle_endpoint,
    apply_endpoint_idle_pair, select_endpoint_idle_pair)
from neutral_packet_model import ORDINARY_PENTAGON_HOLDS
from probe_feedback_packets import integral_table
from test_endpoint_idle_pair_model import closed_form_endpoint, direct_pair_metrics


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rational(value):
    return dict(numerator=value.numerator, denominator=value.denominator, decimal=float(value))


def endpoint_record(word, state):
    result = derive_idle_endpoint(word, state)
    q, recent, successor = closed_form_endpoint(word, state)
    assert (result['q'], result['recent'], result['successor']) == (q, recent, successor)
    return dict(word=word, hex_word=f'0x{word:04X}', initial_state=state,
                **{key: rational(value) if isinstance(value, Fraction) else value
                   for key, value in result.items()}, independent_closed_form_matches=True)


def catalogue(words, nxt):
    states = {16}
    while True:
        expanded = states | set(map(int, nxt[:, sorted(states)].ravel()))
        if expanded == states:
            break
        states = expanded
    used = words[:, sorted(states)]
    first, second = len(np.unique(used >> 8)), len(np.unique(used & 255))
    code = first * 42 + second * 64
    pointer = (0x8340 + code + 255) & ~255
    resident_end = pointer + 256 + 1024 + 1088
    return dict(closed_feedback_states=sorted(states), state_count=len(states), pcm_bins=64,
                first_patterns=first, second_patterns=second, unrolled_dictionary_bytes=code,
                protected_cache_state_fits=len(states) <= 18,
                table_pointer_estimate=pointer, resident_end_estimate=resident_end,
                compact_maximum_one_trd_worker_end_estimate=resident_end + 892,
                compact_worker_estimate_fits=resident_end + 892 < 0xbfff,
                scope='All-bin catalogue and layout arithmetic estimate; execution/layout proof is separate')


def deterministic_npz(arrays):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        for name in sorted(arrays):
            data = io.BytesIO()
            np.save(data, arrays[name], allow_pickle=False)
            entry = zipfile.ZipInfo(name + '.npy', date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data.getvalue(), compresslevel=9)
    return output.getvalue()


def prove_unchanged(path, commit):
    prior = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT).replace(b'\r\n', b'\n')
    current = (ROOT / path).read_bytes().replace(b'\r\n', b'\n')
    assert prior == current, path
    return dict(git_reference=commit, unchanged=True, normalized_lf_sha256=sha(current))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.tmp/endpoint-idle-pair-selection')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report, arrays = select_endpoint_idle_pair()
    assert report['source_audio_opened'] is False
    prior_evidence = ROOT / 'audiobook-beeper/experiments/song-snr/evidence'
    audit_path = prior_evidence / 'feedback-endpoint-audit/report.json'
    audit = json.loads(audit_path.read_text())
    for domain, key in zip(audit['endpoint_consistent_duty_domains'], ('first_words', 'second_words')):
        np.testing.assert_array_equal(arrays[key], domain['allowed_words'])
        assert domain['endpoint_consistent_words'] == 238
    prior_scores_path = prior_evidence / 'idle-pair-selection/all-pairs.npz'
    with np.load(prior_scores_path, allow_pickle=False) as prior:
        indices = np.ix_(arrays['state16_kept_indices'], arrays['state17_kept_indices'])
        for key in ('variance', 'second_moment', 'midpoint_weighted_mean', 'pair_ids'):
            np.testing.assert_array_equal(arrays[key], prior[key][indices])
    report['prior_endpoint_audit'] = dict(
        report=str(audit_path.relative_to(ROOT)).replace('\\', '/'), sha256=sha(audit_path.read_bytes()),
        both_allowed_word_lists_exact=True, allowed_word_counts=[238, 238],
        original_table_cells_verified_by_prior_audit=2048)
    report['prior_periodic_scores'] = dict(
        archive=str(prior_scores_path.relative_to(ROOT)).replace('\\', '/'), sha256=sha(prior_scores_path.read_bytes()),
        all_filtered_scores_moments_means_pair_ids_bit_identical=True,
        scope='Same saved ordinary-packet midpoint objective; no new bandwidth, clock or source-dependent parameters')
    model = dict(holds=list(ORDINARY_PENTAGON_HOLDS), beta=.5, extent=1., pcm_origin=0,
                 pcm_quantization_bias=512, endpoint_idle_pair_words=list(ENDPOINT_IDLE_PAIR_WORDS))
    words, nxt, _ = integral_table(64, 2, holds=model['holds'], beta=.5, extent=1., pcm_origin=0)
    before, next_before = words.copy(), nxt.copy()
    words.flags.writeable = nxt.flags.writeable = False
    changed, successor = apply_endpoint_idle_pair(words, nxt, model)
    assert np.argwhere(changed != before).tolist() == [[32,16],[32,17]]
    assert successor is nxt and np.array_equal(successor, next_before)
    assert np.array_equal(words, before) and not np.shares_memory(words, changed)
    same_words, same_next = apply_endpoint_idle_pair(words, nxt, None)
    assert same_words is words and same_next is nxt
    old_catalogue, new_catalogue = catalogue(before, next_before), catalogue(changed, successor)
    assert old_catalogue['closed_feedback_states'] == new_catalogue['closed_feedback_states']
    initial, final, output, mean, second_moment, variance = direct_pair_metrics(ENDPOINT_IDLE_PAIR_WORDS)
    assert np.max(abs(initial-final)) < 2e-13
    assert abs(variance-report['selected_estimated_variance']) < 1e-14
    report.update(
        starting_commit='6e06d009', selection_precedes_source_access=True, model=model,
        selected_exact_endpoints=[endpoint_record(word, state)
                                  for word, state in zip(ENDPOINT_IDLE_PAIR_WORDS, (16,17))],
        before_catalogue=old_catalogue, after_catalogue=new_catalogue,
        dictionary_delta_bytes=new_catalogue['unrolled_dictionary_bytes']-old_catalogue['unrolled_dictionary_bytes'],
        changed_word_entries=2, unchanged_word_entries=2046, changed_successor_entries=0,
        successor_object_preserved=True, immutable_inputs_unchanged=True, absent_option_identity=True,
        before_table_sha256=sha(before.astype('<u2').tobytes()+next_before.astype('<u2').tobytes()),
        after_table_sha256=sha(changed.astype('<u2').tobytes()+successor.astype('<u2').tobytes()),
        independent_sequential_propagation=dict(
            transitions=32, packet_matrices_used=False, initial_state=initial.tolist(), final_state=final.tolist(),
            periodic_state_max_residual=float(np.max(abs(initial-final))), midpoint_output=output.tolist(),
            midpoint_weighted_mean=mean, second_moment=second_moment, variance=variance,
            selected_variance_absolute_difference=abs(variance-report['selected_estimated_variance']))
    )
    packed = deterministic_npz(arrays)
    (out / 'all-pairs.npz').write_bytes(packed)
    with np.load(io.BytesIO(packed), allow_pickle=False) as saved:
        for key, value in arrays.items():
            np.testing.assert_array_equal(saved[key], value)
    report['full_enumeration'] = dict(
        file='all-pairs.npz', sha256=sha(packed), bytes=len(packed), pair_matrix_shape=[238,238], pairs=56644,
        ranking_rows=len(arrays['ranking']), all_duty_candidate_words=848,
        includes_all_exact_endpoint_recent_fractions_and_successors=True,
        includes_every_filtered_pair_score_and_ranking=True, includes_filter_matrices=True)
    names = (
        'audiobook-beeper/endpoint_idle_pair_model.py', 'audiobook-beeper/test_endpoint_idle_pair_model.py',
        'audiobook-beeper/experiments/song-snr/evidence/endpoint-idle-pair-selection/select.py',
        'audiobook-beeper/idle_pair_packet_model.py', 'audiobook-beeper/ima_waveform_encoder.py',
        'audiobook-beeper/neutral_packet_model.py', 'audiobook-beeper/probe_feedback_packets.py',
    )
    report['current_producer_sha256'] = {name: sha((ROOT / name).read_bytes()) for name in names}
    preserved = (
        'ima_waveform_encoder.py', 'ima_beam.py', 'experiments/song-snr/clock_control.py',
        'experiments/song-snr/general.py', 'native_waveform_encoder.c', 'native_waveform_encoder.py',
        'native_ima_encoder.c', 'native_ima_encoder.py', 'centered_waveform_reference.py',
        'neutral_packet_model.py', 'idle_cycle_packet_model.py', 'idle_pair_packet_model.py',
    )
    report['unchanged_prior_producers'] = {
        name: prove_unchanged('audiobook-beeper/'+name, '6e06d009') for name in preserved}
    report['original_python_reference'] = {
        name: prove_unchanged('audiobook-beeper/'+name, '13819086')
        for name in ('ima_waveform_encoder.py', 'ima_beam.py')}
    tests = subprocess.run([sys.executable, str(ROOT/'audiobook-beeper/test_endpoint_idle_pair_model.py'), '-v'],
                           cwd=ROOT, capture_output=True, text=True)
    log = tests.stdout + tests.stderr
    (out/'tests.log').write_text(log, encoding='utf-8')
    assert tests.returncode == 0, log
    report['tests'] = dict(passed=True, count=9, log='tests.log', log_sha256=sha((out/'tests.log').read_bytes()),
                          command='python audiobook-beeper/test_endpoint_idle_pair_model.py -v')
    report['reproducer'] = 'python audiobook-beeper/experiments/song-snr/evidence/endpoint-idle-pair-selection/select.py --output NEW_FOLDER'
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in (
        'selected_hex_words', 'pairs_enumerated', 'selected_estimated_variance',
        'solve_condition', 'after_catalogue', 'dictionary_delta_bytes', 'full_enumeration')}))


if __name__ == '__main__':
    main()
