"""Reproduce the frozen two-word table proof without opening audio sources."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(ROOT / 'audiobook-beeper'), str(ROOT / 'toolkit')]

import numpy as np
from idle_cycle_packet_model import (IDLE_CYCLE_WORD, IDLE_CYCLE_STATES,
    apply_idle_cycle_packet, validate_idle_cycle_packet)
from neutral_packet_model import ORDINARY_PENTAGON_HOLDS, on_time_tstates
from probe_feedback_packets import integral_table


def sha(data):
    return hashlib.sha256(data).hexdigest()


def catalogue(words, nxt):
    reachable = {16}
    while True:
        expanded = reachable | set(map(int, nxt[:, sorted(reachable)].ravel()))
        if expanded == reachable:
            break
        reachable = expanded
    used = words[:, sorted(reachable)]
    first = len(np.unique(used >> 8))
    second = len(np.unique(used & 255))
    return dict(closed_feedback_states=sorted(reachable), state_count=len(reachable),
                bins_examined=64, first_patterns=first, second_patterns=second,
                unrolled_dictionary_bytes=first * 42 + second * 64,
                protected_cache_state_fits=len(reachable) <= 18,
                scope='All-bin closure and dictionary arithmetic; native layout proof is separate')


def normalized_lf(data):
    return data.replace(b'\r\n', b'\n')


def prove_unchanged(path, commit):
    prior = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)
    current = (ROOT / path).read_bytes()
    assert normalized_lf(prior) == normalized_lf(current), path
    return dict(git_reference=commit, unchanged=True,
                normalized_lf_sha256=sha(normalized_lf(current)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.tmp/idle-cycle-helper')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    model = dict(holds=list(ORDINARY_PENTAGON_HOLDS), beta=.5, extent=1., pcm_origin=0,
                 pcm_quantization_bias=512, idle_cycle_word=IDLE_CYCLE_WORD)
    assert validate_idle_cycle_packet(model) == IDLE_CYCLE_WORD
    words, nxt, _ = integral_table(64, 2, holds=model['holds'], beta=.5, extent=1., pcm_origin=0)
    before, next_before = words.copy(), nxt.copy()
    words.flags.writeable = False
    nxt.flags.writeable = False
    changed, next_changed = apply_idle_cycle_packet(words, nxt, model)
    cells = np.argwhere(changed != before).tolist()
    assert cells == [[32, 16], [32, 17]]
    assert next_changed is nxt and np.array_equal(nxt, next_before)
    assert np.array_equal(words, before) and not np.shares_memory(changed, words)
    absent_words, absent_next = apply_idle_cycle_packet(words, nxt, None)
    assert absent_words is words and absent_next is nxt
    chosen = ROOT / 'audiobook-beeper/experiments/song-snr/evidence/neutral-packet-selection/report.json'
    frozen = json.loads(chosen.read_text())
    assert frozen['selected_word'] == IDLE_CYCLE_WORD
    source_paths = (
        'audiobook-beeper/idle_cycle_packet_model.py',
        'audiobook-beeper/test_idle_cycle_packet_model.py',
        'audiobook-beeper/neutral_packet_model.py',
        'audiobook-beeper/probe_feedback_packets.py',
        'audiobook-beeper/experiments/song-snr/evidence/idle-cycle-helper/verify.py',
    )
    preserved = (
        'ima_waveform_encoder.py', 'ima_beam.py', 'experiments/song-snr/clock_control.py',
        'experiments/song-snr/general.py', 'native_waveform_encoder.c',
        'native_waveform_encoder.py', 'native_ima_encoder.c', 'native_ima_encoder.py',
        'centered_waveform_reference.py', 'neutral_packet_model.py',
    )
    originals = {name: prove_unchanged('audiobook-beeper/' + name, '0a212417')
                 for name in preserved}
    original_reference = {name: prove_unchanged('audiobook-beeper/' + name, '13819086')
                          for name in ('ima_waveform_encoder.py', 'ima_beam.py')}
    tests = subprocess.run([sys.executable, str(ROOT / 'audiobook-beeper/test_idle_cycle_packet_model.py'), '-v'],
                           cwd=ROOT, capture_output=True, text=True)
    log = tests.stdout + tests.stderr
    (out / 'tests.log').write_text(log, encoding='utf-8')
    assert tests.returncode == 0, log
    report = dict(
        date=datetime.date.today().isoformat(), starting_commit='0a212417', complete=True,
        source_audio_opened=False, new_word_selection_performed=False,
        frozen_word=IDLE_CYCLE_WORD, frozen_hex=f'0x{IDLE_CYCLE_WORD:04X}',
        frozen_selection_report=str(chosen.relative_to(ROOT)).replace('\\', '/'),
        frozen_selection_report_sha256=sha(chosen.read_bytes()),
        ordinary_period_tstates=sum(ORDINARY_PENTAGON_HOLDS),
        ordinary_on_tstates=on_time_tstates(IDLE_CYCLE_WORD),
        half_duty_area_error_tstates=abs(on_time_tstates(IDLE_CYCLE_WORD) - 449 / 2),
        model=model, feedback_states=list(IDLE_CYCLE_STATES), original_idle_successors=[17, 16],
        changed_cells=[dict(bin=row, state=state, before=int(before[row, state]),
                            after=int(changed[row, state])) for row, state in cells],
        changed_word_entries=len(cells), unchanged_word_entries=int(np.count_nonzero(before == changed)),
        changed_successor_entries=int(np.count_nonzero(next_before != next_changed)),
        successor_object_preserved=next_changed is nxt, immutable_inputs_unchanged=True,
        absent_option_identity=True, input_word_memory_not_shared=True,
        before_catalogue=catalogue(before, next_before), after_catalogue=catalogue(changed, next_changed),
        before_table_sha256=sha(before.astype('<u2').tobytes() + next_before.astype('<u2').tobytes()),
        after_table_sha256=sha(changed.astype('<u2').tobytes() + next_changed.astype('<u2').tobytes()),
        current_producer_sha256={name: sha((ROOT / name).read_bytes()) for name in source_paths},
        unchanged_prior_producers=originals, original_python_reference=original_reference,
        tests=dict(command='python audiobook-beeper/test_idle_cycle_packet_model.py -v',
                   passed=True, count=6, log='tests.log', log_sha256=sha((out / 'tests.log').read_bytes())),
        reproducer='python audiobook-beeper/experiments/song-snr/evidence/idle-cycle-helper/verify.py --output NEW_FOLDER',
        scope='Frozen source-independent word-only helper proof. No new enumeration, source encoding, audio acceptance or release claim.'
    )
    assert report['before_catalogue']['closed_feedback_states'] == report['after_catalogue']['closed_feedback_states']
    report['dictionary_delta_bytes'] = (report['after_catalogue']['unrolled_dictionary_bytes']
                                       - report['before_catalogue']['unrolled_dictionary_bytes'])
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in (
        'frozen_hex', 'changed_word_entries', 'changed_successor_entries',
        'after_catalogue', 'after_table_sha256', 'tests')}))


if __name__ == '__main__':
    main()
