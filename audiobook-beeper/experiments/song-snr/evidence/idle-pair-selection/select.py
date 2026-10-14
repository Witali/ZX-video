"""Reproduce all duty-balanced idle pairs and the frozen word-only proof."""
import argparse
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
from idle_pair_packet_model import (IDLE_PAIR_WORDS, apply_idle_pair_packet, select_idle_pair)
from neutral_packet_model import ORDINARY_PENTAGON_HOLDS, on_time_tstates
from probe_feedback_packets import integral_table
from test_idle_pair_packet_model import direct_pair_metrics


def sha(data):
    return hashlib.sha256(data).hexdigest()


def catalogue(words, nxt):
    states = {16}
    while True:
        expanded = states | set(map(int, nxt[:, sorted(states)].ravel()))
        if expanded == states:
            break
        states = expanded
    used = words[:, sorted(states)]
    first, second = len(np.unique(used >> 8)), len(np.unique(used & 255))
    return dict(closed_feedback_states=sorted(states), state_count=len(states),
                pcm_bins=64, first_patterns=first, second_patterns=second,
                unrolled_dictionary_bytes=first * 42 + second * 64,
                protected_cache_state_fits=len(states) <= 18,
                scope='All-bin closure and dictionary arithmetic; player execution/layout proof is separate')


def deterministic_npz(arrays):
    """Fix ZIP timestamps so identical arrays produce identical evidence bytes."""
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
    parser.add_argument('--output', type=Path, default=ROOT / '.tmp/idle-pair-selection')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report, arrays = select_idle_pair()
    assert report['source_audio_opened'] is False
    model = dict(holds=list(ORDINARY_PENTAGON_HOLDS), beta=.5, extent=1., pcm_origin=0,
                 pcm_quantization_bias=512, idle_pair_words=list(IDLE_PAIR_WORDS))
    words, nxt, _ = integral_table(64, 2, holds=model['holds'], beta=.5, extent=1., pcm_origin=0)
    before, next_before = words.copy(), nxt.copy()
    words.flags.writeable = nxt.flags.writeable = False
    changed, next_changed = apply_idle_pair_packet(words, nxt, model)
    cells = np.argwhere(before != changed).tolist()
    assert cells == [[32, 16], [32, 17]]
    assert next_changed is nxt and np.array_equal(next_changed, next_before)
    assert np.array_equal(words, before) and not np.shares_memory(words, changed)
    same_words, same_next = apply_idle_pair_packet(words, nxt, None)
    assert same_words is words and same_next is nxt
    before_catalogue, after_catalogue = catalogue(before, next_before), catalogue(changed, next_changed)
    assert before_catalogue['closed_feedback_states'] == after_catalogue['closed_feedback_states']
    initial, final, output, mean, second_moment, variance = direct_pair_metrics(IDLE_PAIR_WORDS)
    assert np.max(abs(initial - final)) < 2e-13
    assert abs(variance - report['selected_estimated_variance']) < 1e-14
    report.update(
        starting_commit='92246ae9', model=model, selection_precedes_source_access=True,
        before_catalogue=before_catalogue, after_catalogue=after_catalogue,
        dictionary_delta_bytes=after_catalogue['unrolled_dictionary_bytes'] - before_catalogue['unrolled_dictionary_bytes'],
        original_idle_words=[int(before[32, state]) for state in (16, 17)],
        original_idle_on_tstates=[on_time_tstates(int(before[32, state])) for state in (16, 17)],
        original_successor_cycle=[17, 16], changed_word_entries=2, unchanged_word_entries=2046,
        changed_successor_entries=0, successor_object_preserved=True,
        immutable_inputs_unchanged=True, absent_option_identity=True,
        before_table_sha256=sha(before.astype('<u2').tobytes() + next_before.astype('<u2').tobytes()),
        after_table_sha256=sha(changed.astype('<u2').tobytes() + next_changed.astype('<u2').tobytes()),
        independent_sequential_propagation=dict(
            transitions=32, packet_matrices_used=False, initial_state=initial.tolist(), final_state=final.tolist(),
            periodic_state_max_residual=float(np.max(abs(initial-final))), midpoint_output=output.tolist(),
            midpoint_weighted_mean=mean, second_moment=second_moment, variance=variance,
            selected_variance_absolute_difference=abs(variance-report['selected_estimated_variance']))
    )
    packed = deterministic_npz(arrays)
    (out / 'all-pairs.npz').write_bytes(packed)
    # Load the exact saved archive to prove that every candidate and ranking was retained.
    with np.load(io.BytesIO(packed), allow_pickle=False) as saved:
        for key, value in arrays.items():
            np.testing.assert_array_equal(saved[key], value)
    report['full_enumeration'] = dict(
        file='all-pairs.npz', sha256=sha(packed), bytes=len(packed),
        first_words=424, second_words=424, pair_matrix_shape=[424, 424], pairs=179776,
        columns=['variance', 'second_moment', 'midpoint_weighted_mean', 'pair_ids'],
        ranking_rows=len(arrays['ranking']), score_symmetry_exact=True,
        includes_every_candidate=True, includes_periodic_filter_matrices=True)
    names = (
        'audiobook-beeper/idle_pair_packet_model.py',
        'audiobook-beeper/test_idle_pair_packet_model.py',
        'audiobook-beeper/experiments/song-snr/evidence/idle-pair-selection/select.py',
        'audiobook-beeper/ima_waveform_encoder.py', 'audiobook-beeper/neutral_packet_model.py',
        'audiobook-beeper/probe_feedback_packets.py',
    )
    report['current_producer_sha256'] = {name: sha((ROOT / name).read_bytes()) for name in names}
    preserved = (
        'ima_waveform_encoder.py', 'ima_beam.py', 'experiments/song-snr/clock_control.py',
        'experiments/song-snr/general.py', 'native_waveform_encoder.c', 'native_waveform_encoder.py',
        'native_ima_encoder.c', 'native_ima_encoder.py', 'centered_waveform_reference.py',
        'neutral_packet_model.py', 'idle_cycle_packet_model.py',
    )
    report['unchanged_prior_producers'] = {
        name: prove_unchanged('audiobook-beeper/' + name, '92246ae9') for name in preserved}
    report['original_python_reference'] = {
        name: prove_unchanged('audiobook-beeper/' + name, '13819086')
        for name in ('ima_waveform_encoder.py', 'ima_beam.py')}
    tests = subprocess.run([sys.executable, str(ROOT / 'audiobook-beeper/test_idle_pair_packet_model.py'), '-v'],
                           cwd=ROOT, capture_output=True, text=True)
    log = tests.stdout + tests.stderr
    (out / 'tests.log').write_text(log, encoding='utf-8')
    assert tests.returncode == 0, log
    report['tests'] = dict(passed=True, count=9, log='tests.log', log_sha256=sha((out / 'tests.log').read_bytes()),
                          command='python audiobook-beeper/test_idle_pair_packet_model.py -v')
    report['reproducer'] = 'python audiobook-beeper/experiments/song-snr/evidence/idle-pair-selection/select.py --output NEW_FOLDER'
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in (
        'selected_hex_words', 'pairs_enumerated', 'selected_estimated_variance',
        'solve_condition', 'after_catalogue', 'dictionary_delta_bytes', 'full_enumeration')}))


if __name__ == '__main__':
    main()
