"""Cold-boot and completely verify deterministic-clock encoding controls.

The source and stream are authenticated against the finished host experiment.
Every source uses its frozen duration-aware PDM model. Four native machine
profiles prove loading, decoder states, pulses and refills; only Pentagon Fuse
profiles authenticate the physical clock targeted by this compensated stream.
No source-specific timing, gain or delay is fitted during execution.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from build_pdm import CPU_CLOCK
from build_stream_trd import build
from general import models, timeline
from probe_reconstruction_error import wav8
from verify_pcm import save
from verify_stream_trd import fuse_check, native_check


SOURCES = ('silence', 'quiet440', 'loud3000', 'steps', 'quiet997',
           'multitone', 'speech', 'entertainer', 'sea_foam')
PROFILES = ('128', 'scorpion', 'pentagon512', 'pentagon1024')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compare_baseline_timing(root, name, profile, verify):
    """Compare whole actual traces; distinguish legacy and prior research."""
    def unavailable(reason):
        result = dict(complete_actual_before_trace_available=False, reason=reason,
                      scope='No before/after timing equality claimed; the complete after trace is still checked against the instruction-derived schedule')
        save(verify / profile / 'timing-comparison.json', result)
        return result

    if name == 'sea_foam':
        before = root / 'study' / 'inputs' / 'song'
        kind = 'authenticated main disk'
    elif name in ('speech', 'entertainer'):
        before = root / 'legacy-controls' / name
        kind = 'fresh legacy control'
    elif name in ('loud3000', 'silence', 'quiet997'):
        before = root / 'prototype' / name
        kind = 'previous duration-aware research prototype, not legacy baseline'
    else:
        return unavailable('No complete before emulator control exists for this generated source')
    old = before / 'verification' / profile
    if not (old / 'report.json').exists():
        return unavailable('The identified before source has no complete emulator trace for this profile')
    old_report = json.loads((old / 'report.json').read_bytes())
    assert old_report['complete'] and old_report['end_of_audio_reached']
    old_data = gzip.decompress((old / 'times.u32.gz').read_bytes())
    new_data = gzip.decompress((verify / profile / 'times.u32.gz').read_bytes())
    assert len(old_data) == len(new_data), ('baseline whole timing scope', name, profile)
    assert old_data == new_data, ('introduced source pulse timing change', name, profile)
    result = dict(complete_actual_before_trace_available=True, reference_kind=kind,
                  reference_trd_sha256=old_report['trd_sha256'],
                  every_source_pulse_timestamp_identical=True,
                  timestamps_compared=len(new_data) // 4,
                  relative_timestamps_sha256=sha(new_data),
                  maximum_introduced_timing_change_tstates=0,
                  scope='Every relative source OUT timestamp from two independent complete cold Fuse executions; excludes startup and final mute')
    save(verify / profile / 'timing-comparison.json', result)
    return result


def execute(root, name, cover, fuse, captured=False, stage='clock-compensation'):
    """Build and execute one complete, previously encoded corpus source."""
    method = {'clock-compensation': 'compensation', 'clock-joint': 'joint'}[stage]
    dest = root / stage / name
    host_bytes = (dest / 'host.json').read_bytes()
    host = json.loads(host_bytes)
    frozen = json.loads((dest.parent / 'parameters.json').read_bytes())
    fingerprint = dict(parameters=frozen['parameters'], model=frozen['model'], method=frozen['method'])
    assert sha(json.dumps(fingerprint, sort_keys=True).encode()) == frozen['sha256']
    assert host['source'] == name and host['method'] == method == frozen['method']
    model = dict(models())['duration_zero_half_recent']
    assert host['model'] == model, ('unfrozen model', name)
    assert host['parameters'] == frozen['parameters'] and model == frozen['model']
    assert host['parameters']['model_name'] == 'duration_zero_half_recent'
    assert host['parameters']['source_specific_fitted_clock_gain_delay'] is False
    packed = gzip.decompress((dest / 'soundtrack.ima.gz').read_bytes())
    source = wav8(dest / 'source-preview.wav').astype('u1')
    assert sha(source.tobytes()) == host['source_sha256'], ('source hash', name)
    assert sha(packed) == host['packed_sha256'], ('stream hash', name)
    assert len(source) == 2 * len(packed) == host['source_samples']
    assert host['original_content_preserved'] is True
    disk, meta = build(packed, dest / 'assembly', cover, model)
    if captured:
        assert (dest / 'audio.trd').read_bytes() == disk
        assert json.loads((dest / 'player.json').read_bytes()) == meta
    else:
        (dest / 'audio.trd').write_bytes(disk)
        save(dest / 'player.json', meta)
    verify = dest / 'verification'
    verify.mkdir(exist_ok=True)
    native = [native_check(disk, meta, packed, profile,
                           out=verify / ('native-' + profile + '.json'))
              for profile in PROFILES]
    print('Native complete: ' + name, flush=True)
    actual = []
    profiles = ('pentagon512', 'pentagon1024') if name == 'sea_foam' else ('pentagon512',)
    for profile in profiles:
        report = fuse_check(dest / 'audio.trd', meta, packed, profile,
                            verify / profile, fuse, captured=captured)
        count = report['bits_verified']
        raw = np.frombuffer(gzip.decompress(
            (verify / profile / 'times.u32.gz').read_bytes()), '<u4')
        assert len(raw) == count
        expected = timeline(len(source), 'pentagon')[:count]
        np.testing.assert_array_equal(raw.astype(float) * CPU_CLOCK / 3584000, expected)
        assert report['reloads'] == 0 and report['runtime_disk_reads_during_live_audio'] == 0
        report['every_actual_timestamp_matches_instruction_derived_schedule'] = True
        report['before_after_timing'] = compare_baseline_timing(root, name, profile, verify)
        actual.append(report)
        print('Fuse complete: ' + name + '/' + profile, flush=True)
    result = dict(
        complete=True, source=name, method=method, stage=stage, parameters=host['parameters'],
        frozen_parameter_sha256=frozen['sha256'],
        model=model, source_sha256=host['source_sha256'], packed_sha256=sha(packed),
        host_report_sha256=sha(host_bytes), trd_sha256=sha(disk),
        native=native, fuse=actual, original_content_preserved=True,
        worker_origin=meta['memory']['worker_origin'],
        hot_path_instruction_delta_tstates=0,
        ordinary_native_tstates={'128': 423, 'scorpion': 423, 'pentagon512': 449, 'pentagon1024': 449},
        page_extra_tstates=14, bank_extra_tstates={'128': 243, 'scorpion': 267, 'pentagon512': 243, 'pentagon1024': 243},
        source_independent_preset=True,
        scope='Full functional native proof on four profiles; own-clock cold Fuse proof on listed Pentagon profiles. This stream targets Pentagon timing; native 128/Scorpion results do not establish their audio quality.',
        physical_hardware_tested=False, main_release_unchanged=True)
    save(verify / 'execution.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--fuse', required=True, type=Path)
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--captured', action='store_true')
    parser.add_argument('--source', action='append', choices=SOURCES)
    parser.add_argument('--stage', choices=('clock-compensation', 'clock-joint'), default='clock-compensation',
                        help='Separately saved authenticated host experiment; no source-specific settings')
    args = parser.parse_args()
    assert 1 <= args.jobs <= 4
    root = args.evidence.resolve()
    inputs = root / 'study' / 'inputs'
    baseline = json.loads((inputs / 'song' / 'player.json').read_bytes())
    current = (inputs / 'current-main.trd').read_bytes()
    entry = next(x for x in baseline['directory'] if x['name'] == 'COVER')
    offset = (entry['track'] * 16 + entry['sector']) * 256
    cover = current[offset:offset + 6912]
    assert len(cover) == 6912
    names = args.source or SOURCES
    assert len(set(names)) == len(names), 'Duplicate sources would share mutable build outputs'
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        reports = list(pool.map(lambda name: execute(root, name, cover, args.fuse, args.captured, args.stage), names))
    print(json.dumps(dict(complete=True, stage=args.stage, sources=list(names),
                          trd_sha256={row['source']: row['trd_sha256'] for row in reports},
                          native_full_runs=sum(len(row['native']) for row in reports),
                          fuse_full_runs=sum(len(row['fuse']) for row in reports)), indent=2), flush=True)


if __name__ == '__main__':
    main()
