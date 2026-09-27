"""Audit complete Fast ZX0 disk playback against the retained Turbo player.

Fuse measures actual IRQ/ULA/ROM/disk timing; frame samples are not full
screens. Full-byte native ZX0 and unchanged frame proofs are linked separately.
"""
import argparse
import gzip
import json
from pathlib import Path

from audit_faster_zx0 import audit as audit_cpu
from audit_irq_fields import audit
from build_fap3_trd import sha
from profile_fap3 import summarize_fuse
from profile_integrated_timing import analyze, stats
from summarize_fast_return_irq import rom_invariants
from summarize_uncontended_frame import metrics

ROOT = Path(__file__).parent
OUTPUT = ROOT/'fast_zx0_player_summary.json'


def summarize():
    folder = ROOT/'fast_zx0_player_evidence'
    manifest_path = folder/'manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    if not manifest['complete']: raise ValueError('incomplete archive')
    blobs = {}
    for item in manifest['files']:
        packed = (folder/item['file']).read_bytes()
        raw = gzip.decompress(packed)
        if sha(packed) != item['sha256'] or sha(raw) != item['decoded_sha256'] or len(raw) != item['decoded_bytes']:
            raise ValueError(('archive changed', item['file']))
        blobs[item['file'][:-3]] = raw
    names = ('fast_zx0_player_build.json', 'inplace_keepalive_build.json',
             'inplace_keepalive_summary.json', 'cached_huffman_lookahead_cpu.json', 'faster_zx0_cpu.json')
    paths = [ROOT/n for n in names]
    build, old_build, baseline, frame_cpu, native = [json.loads(p.read_bytes()) for p in paths]
    cpu = audit_cpu(rebuild=True)
    queue_path = ROOT/'fast_zx0_queue_cpu.json'
    queue = json.loads(queue_path.read_bytes())
    if not queue['complete'] or len(queue['deltas']) != 10 or len(queue['cold_references']) != 22:
        raise ValueError('queue verification incomplete')
    for name, digest in queue['source_sha256_lf'].items():
        if sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n')) != digest:
            raise ValueError(('queue source changed', name))
    for name, reference in (('baseline', old_build), ('fast', build)):
        variant = queue['variants'][name]
        if any(variant[k] != reference['volumes'][0][k] for k in ('trd_sha256', 'metadata_sha256')):
            raise ValueError('queue verification used different disk')
        for row in variant['cases']:
            if sum(i['tstates']*i['count'] for i in row['instruction_histogram']) != row['tstates']:
                raise ValueError('queue instruction total differs')
    for before, after, delta in zip(queue['variants']['baseline']['cases'],
            queue['variants']['fast']['cases'], queue['deltas'], strict=True):
        if (any(before[k] != after[k] for k in ('case', 'tstates', 'excluded_calls', 'phase', 'count', 'position'))
                or delta != dict(case=after['case'], baseline_tstates=before['tstates'],
                    fast_tstates=after['tstates'], delta_tstates=0)):
            raise ValueError('queue control changed')
    if (not all(r['complete'] for r in (build, old_build, baseline, frame_cpu, native))
            or blobs['build.json'] != paths[0].read_bytes()
            or build['baseline_build_sha256'] != sha(paths[1].read_bytes())):
        raise ValueError('incomplete or mismatched evidence')
    for name, digest in build['source_sha256_lf'].items():
        if (sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n')) != digest
                or sha(blobs['source-'+name].replace(b'\r\n', b'\n')) != digest):
            raise ValueError(('source changed', name))
    swaps = build['mocked_rom_swaps']
    if ([(v['from_part'], v['to_part']) for v in swaps] != [(1, 2), (2, 3)]
            or not all(v[k] for v in swaps for k in ('prompt_exact', 'wrong_disk_rejected',
                'wrong_series_rejected', 'correct_disk_accepted', 'bootstrap_ram_exact', 'rom_mocked'))):
        raise ValueError('disk-swap checks incomplete')
    volumes = []
    for part in (1, 2, 3):
        stem = f'part{part:02}'
        m = json.loads(blobs[stem+'.metadata.json']); r = json.loads(blobs[stem+'.json'])
        built, previous = build['volumes'][part-1], old_build['volumes'][part-1]
        core = frame_cpu['volumes'][part-1]
        if (not r['complete'] or r['failure'] or r['errors'] or not r['trace_nonce_exact']
                or not r['ay_records_exact'] or not r['progress_100_percent'] or r['debugger_installed_bytes']
                or r['frames'] != m['frames'] or r['native_frames_sampled'] != m['frames']
                or r['pixel_samples_per_frame'] != 80 or r['ay_ticks'] != 6*m['frames']
                or r['runtime_sectors_checked'] != m['video_sectors'] or not m['independently_bootable']
                or m['used_sectors'] > 2544 or m['raw_sha256'] != core['raw_sha256']
                or core['checked_frames'] != m['frames'] or r['trd_sha256'] != m['trd_sha256']
                or m['trd_sha256'] != built['trd_sha256']
                or sha(blobs[stem+'.metadata.json']) != r['integrated_bootstrap_metadata_sha256']
                or sha(blobs[stem+'.metadata.json']) != built['metadata_sha256']
                or m['fast_zx0'] != built['fast_zx0']
                or not all(built[k] for k in ('dirty_ram_boot_exact', 'first_native_screen_exact',
                    'second_compact_frame_exact', 'audio_bank_immutable_exact', 'exact_video_field_roundtrip'))):
            raise ValueError(('incomplete playback or boot', part))
        for key in ('video_bytes', 'video_sectors', 'stream_sha256', 'raw_video_sha256', 'audio_sha256', 'frames'):
            if built[key] != previous[key]: raise ValueError(('payload differs', part, key))
        measured = native['volumes'][part-1]
        if built['stream_sha256'] != measured['stream_sha256']:
            raise ValueError('native decoder used different bytes')
        # Match installed decoder bytes to the complete paired CPU experiment.
        fast_layout = measured['variants']['fast']['layout']
        if m['fast_zx0']['layout'] != fast_layout:
            raise ValueError('installed decoder differs from native CPU proof')
        if not m['fast_zx0']['producer_reassembled_exact'] or any(
                v['delta_tstates'] != 0 for v in m['fast_zx0']['external_operands']):
            raise ValueError('unexpected producer or external instruction change')
        for suffix, key in (('.trace.txt', 'trace_sha256'), ('.debugger.txt', 'debugger_script_sha256')):
            if sha(blobs[stem+suffix]) != r[key]: raise ValueError('trace changed')
        irq = audit(r, m); irq.pop('actual_phase_tstates')
        gates = summarize_fuse(r); gates.pop('publication_intervals_tstates')
        profile = analyze(r, m, core)
        worst = sorted(profile.pop('frames'), key=lambda v: v['work_elapsed'], reverse=True)[:8]
        after = dict(metrics(r), timing_gates=gates, irq=irq, rom=rom_invariants(r, True),
            used_sectors=m['used_sectors'], free_sectors=m['free_sectors'], video_bytes=m['video_bytes'],
            video_start_sector=m['video_start_sector'], trd_sha256=m['trd_sha256'],
            ay_record_field_gaps=r['ay_record_field_gaps'], ay_record_field_duplicates=r['ay_record_field_duplicates'],
            read_service=stats([v['tstates'] for v in r['reads']]),
            keepalive_service=stats([v['tstates'] for v in r['seek_calls'] if v['kind'] == 'keepalive']),
            delivery_profile=profile, worst_work_frames=worst)
        before = baseline['volumes'][part-1]['keepalive']
        delta = {k: after[k]-before[k] for k in ('nominal_late_frames', 'audio_underruns', 'runtime_sectors',
                 'publication_span_tstates', 'bad_actual_intervals', 'used_sectors', 'video_bytes')}
        volumes.append(dict(part=part, fast=after, delta=delta))
    keys = ('frames', 'nominal_late_frames', 'audio_underruns', 'ay_ticks', 'runtime_sectors',
            'publication_span_tstates', 'bad_actual_intervals', 'used_sectors', 'video_bytes')
    totals = {k: sum(v['fast'][k] for v in volumes) for k in keys}
    if totals['frames'] != sum(build['contract']['ends'][i]-(build['contract']['ends'][i-1] if i else 0)
                               for i in range(3)) or totals['ay_ticks'] != 6*totals['frames']:
        raise ValueError('incomplete movie')
    totals.update(nominal_schedule_met=all(v['fast']['timing_gates']['nominal_deadlines_met'] for v in volumes),
        fallback_met=all(v['fast']['timing_gates']['fallback_one_field_met'] for v in volumes),
        ay_50hz_met=all(v['fast']['timing_gates']['actual_ay_50hz'] for v in volumes))
    return dict(complete=True, release=False, scope=__doc__, baseline_commit='a84451d',
        totals=totals, baseline_totals=baseline['totals'], volumes=volumes,
        paired_native_cpu=cpu['variants'], all_video_and_audio_bytes_unchanged=True,
        full_fuse_pixel_comparison=False, full_integrated_cpu_total_measured=False,
        physical_drive_verified=False, initial_disk_and_irq_phases_not_matched=True,
        queue_control_deltas=queue['deltas'],
        references={p.name: sha(p.read_bytes()) for p in (*paths, queue_path, manifest_path)},
        source_sha256_lf={n: sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in
            ('summarize_fast_zx0_player.py', 'measure_fap3_fuse.py', 'profile_integrated_timing.py',
             'profile_fap3.py', 'audit_irq_fields.py', 'summarize_fast_return_irq.py', 'summarize_uncontended_frame.py')})


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--write', action='store_true')
    args = p.parse_args(); result = json.loads(json.dumps(summarize()))
    if args.write: OUTPUT.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    elif result != json.loads(OUTPUT.read_bytes()): raise ValueError('saved summary differs')
    print(json.dumps(result['totals']), flush=True)


if __name__ == '__main__': main()
