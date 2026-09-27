"""Audit uncontended half-row copy placement against the complete half-row player.

Keeps deterministic frame/copy/parser costs separate from elapsed Fuse
delivery. Full CPU pixels and sampled Fuse pixels have different coverage.
"""
import argparse
import gzip
import json
from pathlib import Path
from build_fap3_trd import sha
from audit_irq_fields import audit
from profile_fap3 import summarize_fuse
from profile_integrated_timing import analyze
from summarize_uncontended_frame import metrics
from summarize_fast_return_irq import rom_invariants

ROOT = Path(__file__).parent
OUTPUT = ROOT/'uncontended_half_player_summary.json'


def summarize():
    folder = ROOT/'uncontended_half_player_evidence'
    manifest_path = folder/'manifest.json'; manifest = json.loads(manifest_path.read_bytes())
    blobs = {}
    for item in manifest['files']:
        packed = (folder/item['file']).read_bytes(); raw = gzip.decompress(packed)
        if sha(packed)!=item['sha256'] or sha(raw)!=item['decoded_sha256'] or len(raw)!=item['decoded_bytes']:
            raise ValueError(('archive changed', item['file']))
        blobs[item['file'][:-3]] = raw
    build_path = ROOT/'uncontended_half_player_build.json'; cpu_path = ROOT/'uncontended_half_copy_cpu.json'
    baseline_path = ROOT/'half_row_player_summary.json'
    baseline_build_path = ROOT/'half_row_player_build.json'
    baseline_cpu_path = ROOT/'half_row_cache_cpu.json'
    build, cpu, baseline = [json.loads(p.read_bytes()) for p in (build_path, cpu_path, baseline_path)]
    baseline_build, baseline_cpu = [json.loads(p.read_bytes()) for p in (baseline_build_path, baseline_cpu_path)]
    if (build['baseline_build_sha256']!=sha(baseline_build_path.read_bytes())
            or cpu['reference_sha256']!=sha(baseline_cpu_path.read_bytes())):
        raise ValueError('baseline report changed')
    if (not manifest['complete'] or not all(r['complete'] for r in (build, cpu, baseline))
            or not cpu['full_compact_and_both_native_exact'] or cpu['checked_frames']!=4221
            or blobs['build.json']!=build_path.read_bytes()):
        raise ValueError('incomplete/different CPU/build evidence')
    for report in (build, cpu):
        for name, digest in report['source_sha256_lf'].items():
            if sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n'))!=digest:
                raise ValueError(('source changed', name))
    cost_keys = ('baseline_tstates', 'tstates', 'delta_tstates', 'old_copy_tstates', 'copy_tstates')
    for volume, previous in zip(cpu['volumes'], baseline_cpu['volumes'], strict=True):
        if len(volume['frames'])!=volume['checked_frames']:
            raise ValueError('CPU frame count differs')
        for frame, old_frame in zip(volume['frames'], previous['frames'], strict=True):
            if (frame['tstates']-frame['baseline_tstates']!=frame['delta_tstates']
                    or frame['copy_tstates']-frame['old_copy_tstates']!=frame['delta_tstates']
                    or frame['baseline_tstates']!=old_frame['tstates']
                    or frame['old_copy_tstates']!=old_frame['copy_tstates']
                    or frame['frame']!=old_frame['frame']):
                raise ValueError('CPU frame arithmetic differs')
        if any(sum(f[k] for f in volume['frames'])!=volume[k] for k in cost_keys):
            raise ValueError('CPU volume arithmetic differs')
    if (any(sum(v[k] for v in cpu['volumes'])!=cpu[k] for k in cost_keys)
            or cpu['parser_extra_tstates']!=0):
        raise ValueError('CPU total arithmetic differs')
    for name, digest in build['source_sha256_lf'].items():
        if sha(blobs['source-'+name].replace(b'\r\n', b'\n'))!=digest:
            raise ValueError('archived generator differs')
    swaps = build['mocked_rom_swaps']
    if ([(s['from_part'], s['to_part']) for s in swaps]!=[(1, 2), (2, 3)]
            or not all(s[k] for s in swaps for k in ('prompt_exact', 'wrong_disk_rejected',
                'wrong_series_rejected', 'correct_disk_accepted', 'bootstrap_ram_exact'))):
        raise ValueError('swap checks incomplete')
    volumes = []
    for part in (1, 2, 3):
        stem = f'part{part:02}'; m = json.loads(blobs[stem+'.metadata.json']); r = json.loads(blobs[stem+'.json'])
        built = build['volumes'][part-1]; core = cpu['volumes'][part-1]
        before = baseline['volumes'][part-1]['half_rows']
        old_build = baseline_build['volumes'][part-1]
        if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact']
                or r['debugger_installed_bytes'] or r['fast_read_retries'] or not r['ay_records_exact']
                or not r['progress_100_percent'] or not m['independently_bootable'] or m['used_sectors']>2544
                or r['frames']!=m['frames'] or core['checked_frames']!=m['frames']
                or r['native_frames_sampled']!=m['frames'] or r['pixel_samples_per_frame']!=80
                or r['ay_ticks']!=6*m['frames'] or r['runtime_sectors_checked']!=m['video_sectors']
                or r['trd_sha256']!=m['trd_sha256'] or m['trd_sha256']!=built['trd_sha256']
                or sha(blobs[stem+'.metadata.json'])!=r['integrated_bootstrap_metadata_sha256']
                or m['half_row_cache']!=built['half_row_cache'] or core['raw_sha256']!=m['raw_sha256']
                or m['uncontended_half_copy']!=built['uncontended_half_copy']
                or not all(built[k] for k in ('dirty_ram_boot_exact', 'first_native_screen_exact',
                    'second_compact_frame_exact', 'audio_bank_immutable_exact', 'exact_video_field_roundtrip'))):
            raise ValueError(('incomplete/mismatched player', part))
        for region in core['implementation']['regions']:
            at, expected = region['address'], bytes.fromhex(region['code_hex'])
            candidates = m['uncontended_half_copy']['regions']
            actual = next(bytes.fromhex(v['code_hex']) for v in candidates if v['address']==at)
            if actual!=expected: raise ValueError('CPU fixture differs from installed code')
        for key in ('video_bytes', 'video_sectors', 'stream_sha256', 'raw_video_sha256', 'audio_sha256'):
            if built[key]!=old_build[key]: raise ValueError(('stream changed', part, key))
        for suffix, key in (('.trace.txt', 'trace_sha256'), ('.debugger.txt', 'debugger_script_sha256')):
            if sha(blobs[stem+suffix])!=r[key]: raise ValueError('trace changed')
        irq = audit(r, m); irq.pop('actual_phase_tstates')
        gate = summarize_fuse(r); gate.pop('publication_intervals_tstates')
        profile = analyze(r, m, core); worst = sorted(profile.pop('frames'), key=lambda f: f['work_elapsed'], reverse=True)[:8]
        after = dict(metrics(r), timing_gates=gate, irq=irq, rom=rom_invariants(r, True),
            used_sectors=m['used_sectors'], free_sectors=m['free_sectors'], video_bytes=m['video_bytes'],
            video_start_sector=m['video_start_sector'], trd_sha256=m['trd_sha256'],
            ay_record_field_gaps=r['ay_record_field_gaps'], ay_record_field_duplicates=r['ay_record_field_duplicates'],
            delivery_profile=profile, worst_work_frames=worst)
        delta = {k: after[k]-before[k] for k in ('nominal_late_frames', 'audio_underruns', 'runtime_sectors',
            'publication_span_tstates', 'bad_actual_intervals', 'used_sectors', 'video_bytes')}
        volumes.append(dict(part=part, uncontended_copy=after, delta=delta, frame_cpu_tstates=core['tstates'],
            frame_cpu_delta_tstates=core['delta_tstates'], parser_extra_tstates=0))
    keys = ('frames', 'nominal_late_frames', 'audio_underruns', 'runtime_sectors', 'publication_span_tstates',
            'bad_actual_intervals', 'used_sectors', 'video_bytes')
    totals = {k: sum(v['uncontended_copy'][k] for v in volumes) for k in keys}
    totals.update(nominal_schedule_met=all(v['uncontended_copy']['timing_gates']['nominal_deadlines_met'] for v in volumes),
        fallback_met=all(v['uncontended_copy']['timing_gates']['fallback_one_field_met'] for v in volumes),
        ay_50hz_met=all(v['uncontended_copy']['timing_gates']['actual_ay_50hz'] for v in volumes),
        frame_cpu_tstates=cpu['tstates'], frame_cpu_delta_tstates=cpu['delta_tstates'],
        parser_extra_tstates=cpu['parser_extra_tstates'],
        accounted_cpu_delta_tstates=cpu['delta_tstates']+cpu['parser_extra_tstates'])
    return dict(complete=True, release=False, scope=__doc__, baseline_commit='0c674b6',
        references={p.name: sha(p.read_bytes()) for p in (manifest_path, build_path, cpu_path, baseline_path,
            baseline_build_path, baseline_cpu_path)},
        source_sha256_lf={n: sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in
            ('summarize_uncontended_half_player.py', 'measure_fap3_fuse.py', 'audit_irq_fields.py', 'profile_fap3.py',
             'profile_integrated_timing.py', 'summarize_uncontended_frame.py', 'summarize_fast_return_irq.py')},
        totals=totals, volumes=volumes, full_frame_cpu_pixels=True, full_fuse_pixel_comparison=False,
        full_integrated_cpu_total_measured=False, physical_drive_verified=False,
        initial_disk_and_irq_phases_not_matched=True,
        note='CPU delta covers frame stages; parser and compressed stream are unchanged. It excludes '
             'ZX0, queue/copy, AY scheduling, ULA, ROM and disk costs. Fuse covers their combined '
             'delivery effect. Video and audio streams are byte-exact against the half-row baseline.')


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--write', action='store_true')
    a = p.parse_args(); result = json.loads(json.dumps(summarize()))
    if a.write: OUTPUT.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    elif result!=json.loads(OUTPUT.read_bytes()): raise ValueError('saved analysis differs')
    print(json.dumps(result['totals']), flush=True)


if __name__ == '__main__': main()
