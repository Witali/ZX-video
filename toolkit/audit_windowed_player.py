"""Archive and audit the single-set automatic windowed-player experiment.

The archive includes complete final Fuse traces, selected native CPU records
and local decisions. Model scores are estimates and cannot pass release gates.
"""
import argparse
import gzip
import json
from pathlib import Path

from audit_irq_fields import audit
from build_fap3_trd import sha
from profile_fap3 import summarize_fuse
from summarize_fast_token_player import instruction_sum
from summarize_native_mask_selection import read_archive
from summarize_uncontended_frame import metrics

ROOT = Path(__file__).parent
EVIDENCE = ROOT/'windowed_player_evidence'
OUTPUT = ROOT/'windowed_player_summary.json'


def archive(directory):
    build = json.loads((directory/'build.json').read_bytes())
    if not build['complete']: raise ValueError('complete build required')
    EVIDENCE.mkdir(exist_ok=True); entries = []
    def add(path, name):
        raw = path.read_bytes(); packed = gzip.compress(raw, mtime=0)
        target = EVIDENCE/(name+'.gz')
        if target.exists() and target.read_bytes() != packed: raise ValueError('refuse to replace archive')
        target.write_bytes(packed)
        entries.append(dict(file=target.name, sha256=sha(packed), decoded_sha256=sha(raw), decoded_bytes=len(raw)))
    for name, digest in build['source_sha256_lf'].items():
        if sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n')) != digest: raise ValueError('different source')
        add(ROOT/name, 'source-'+name)
    for name in ('build.json', 'native-cpu.json', 'selection.json', 'timing.json', 'volumes.json', 'swaps.json'):
        add(directory/name, name)
    for row in build['volumes']:
        part = row['part']; stem = f'ZX-video-huffman-preview_part{part:02}'
        if sha((directory/(stem+'.trd')).read_bytes()) != row['trd_sha256']: raise ValueError('different TRD')
        add(directory/(stem+'.json'), f'part{part:02}.metadata.json')
        for suffix in ('json', 'trace.txt', 'debugger.txt'):
            add(directory/f'part{part:02}.{suffix}', f'part{part:02}.{suffix}')
    report = dict(complete=True, release=False, files=entries,
        archive_script_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')))
    (EVIDENCE/'manifest.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


def summarize():
    blobs = read_archive(EVIDENCE, packed_sizes=False)
    build, cpu, selection, timing = [json.loads(blobs[n+'.json']) for n in ('build', 'native-cpu', 'selection', 'timing')]
    paths = [ROOT/n for n in ('fast_zx0_player_build.json', 'fast_zx0_player_summary.json',
        'fast_zx0_tokens_probe.json', 'cached_huffman_lookahead_cpu.json', 'fast_token_player_summary.json',
        'pressure_token_summary.json')]
    old, baseline, probe, frame_cpu, tokens, pressure = [json.loads(p.read_bytes()) for p in paths]
    if not all(r['complete'] for r in (build, cpu, selection, timing, old, baseline, probe, frame_cpu)):
        raise ValueError('incomplete evidence')
    for name, digest in build['source_sha256_lf'].items():
        if (sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n')) != digest
                or sha(blobs['source-'+name].replace(b'\r\n', b'\n')) != digest):
            raise ValueError(('source changed', name))
    for name, digest in build['source_references'].items():
        if sha((ROOT/name).read_bytes()) != digest: raise ValueError(('input report changed', name))
    if build['alternative_trds_built'] or build['alternative_fuse_runs'] or selection['alternative_trds_built'] or selection['alternative_fuse_runs']:
        raise ValueError('search built alternative images')
    if build['final_trds_built'] != len(build['volumes']) or build['final_fuse_runs'] != len(build['volumes']):
        raise ValueError('not exactly one final run per disk')
    swaps = build['mocked_rom_swaps']
    if ([(v['from_part'], v['to_part']) for v in swaps] != [(1, 2), (2, 3)]
            or not all(v[k] for v in swaps for k in ('prompt_exact', 'wrong_disk_rejected',
                'wrong_series_rejected', 'correct_disk_accepted', 'bootstrap_ram_exact', 'rom_mocked'))):
        raise ValueError('swap checks incomplete')
    volumes = []
    for built, nv, sv, tv in zip(build['volumes'], cpu['volumes'], selection['volumes'], timing['disks'], strict=True):
        part = built['part']; stem = f'part{part:02}'
        m = json.loads(blobs[stem+'.metadata.json']); r = json.loads(blobs[stem+'.json'])
        decision = sv['selection']; core = frame_cpu['volumes'][part-1]
        if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact']
                or not r['ay_records_exact'] or not r['progress_100_percent'] or r['debugger_installed_bytes']
                or r['frames'] != m['frames'] or r['native_frames_sampled'] != m['frames']
                or r['ay_ticks'] != 6*m['frames'] or r['pixel_samples_per_frame'] != 80
                or r['runtime_sectors_checked'] != m['video_sectors'] or m['used_sectors'] > 2544
                or not m['independently_bootable'] or m['raw_sha256'] != core['raw_sha256']
                or core['checked_frames'] != m['frames'] or r['trd_sha256'] != built['trd_sha256']
                or nv['trd_sha256'] != built['trd_sha256'] or m['trd_sha256'] != built['trd_sha256']
                or sha(blobs[stem+'.metadata.json']) != built['metadata_sha256']
                or built['metadata_sha256'] != r['integrated_bootstrap_metadata_sha256']
                or nv['stream_sha256'] != built['stream_sha256'] or nv['layout'] != built['fast_zx0']['layout']
                or not all(built[k] for k in ('dirty_ram_boot_exact', 'first_native_screen_exact',
                    'second_compact_frame_exact', 'audio_bank_immutable_exact', 'exact_video_field_roundtrip'))):
            raise ValueError('incomplete final playback/boot')
        for key in ('frames', 'raw_video_sha256', 'audio_sha256'):
            if built[key] != old['volumes'][part-1][key]: raise ValueError('decoded content changed')
        for b, candidate, name in zip(nv['blocks'], probe['volumes'][part-1]['blocks'], decision['names'], strict=True):
            expected = candidate['variants'][name]
            if (not b['exact'] or b['payload_sha256'] != expected['payload_sha256']
                    or b['raw_sha256'] != candidate['raw_sha256'] or b['decoder_tstates'] != expected['decoder_tstates']
                    or sum(b['slice_tstates']) != b['decoder_tstates']
                    or b['begin_tstates']+sum(b['step_tstates']) != b['producer_tstates']):
                raise ValueError('native block differs')
        ns = nv['summary']
        if (not ns['complete'] or not ns['sectors_exact_once'] or not ns['decoder_instruction_table_checked']
                or instruction_sum(ns['decoder_instruction_histogram']) != ns['decoder_tstates']
                or sum(i['count']*i['tstates'] for i in ns['instruction_histogram']) != ns['producer_tstates']
                or ns['total_tstates'] != ns['producer_tstates']+ns['decoder_tstates']
                or ns['decoder_tstates'] != decision['decoder_tstates'] or ns['sector_reads'] != m['video_sectors']):
            raise ValueError('native sums differ')
        for key in ('producer_tstates', 'decoder_tstates'):
            if ns[key] != sum(b[key] for b in nv['blocks']): raise ValueError('block sums differ')
        if (decision['stream_bytes'] != m['video_bytes'] or decision['stream_bytes'] > decision['capacity_bytes']
                or decision['maximum_evaluated_horizon_frames'] > decision['window_frames']
                or any(d['end_frame_exclusive']-d['first_frame'] > decision['window_frames']
                       or d['remaining_bytes'] < 0 for d in decision['decisions'])):
            raise ValueError('window horizon/capacity differs')
        for suffix, key in (('.trace.txt', 'trace_sha256'), ('.debugger.txt', 'debugger_script_sha256')):
            if sha(blobs[stem+suffix]) != r[key]: raise ValueError('trace differs')
        gates = summarize_fuse(r)
        if any(tv[k] != v for k, v in gates.items()): raise ValueError('saved gates differ')
        if tv['report_sha256'] != sha(blobs[stem+'.json']): raise ValueError('final report differs')
        gates.pop('publication_intervals_tstates'); irq = audit(r, m); irq.pop('actual_phase_tstates')
        measured = dict(metrics(r), timing_gates=gates, irq=irq, used_sectors=m['used_sectors'],
            free_sectors=m['free_sectors'], video_bytes=m['video_bytes'])
        volumes.append(dict(part=part, playback=measured, estimated_score=decision['estimated_score'],
            model_baseline_late_frames=decision['baseline_model']['estimated_score'][1],
            actual_baseline_late_frames=decision['baseline_model']['actual_late_frames']))
    for key, value in cpu['totals'].items():
        if value != sum(v['summary'][key] for v in cpu['volumes']): raise ValueError('CPU aggregate differs')
    keys = ('frames', 'nominal_late_frames', 'bad_actual_intervals', 'audio_underruns', 'ay_ticks',
        'runtime_sectors', 'publication_span_tstates', 'video_bytes', 'used_sectors')
    totals = {k: sum(v['playback'][k] for v in volumes) for k in keys}
    totals.update(nominal_schedule_met=all(v['playback']['timing_gates']['nominal_deadlines_met'] for v in volumes),
        fallback_met=all(v['playback']['timing_gates']['fallback_one_field_met'] for v in volumes),
        ay_50hz_met=all(v['playback']['timing_gates']['actual_ay_50hz'] for v in volumes))
    return dict(complete=True, release=False, scope=__doc__, totals=totals, volumes=volumes,
        native_cpu=cpu['totals'], baseline_totals=baseline['totals'], unweighted_totals=tokens['totals'],
        pressure_controls={n: v['totals'] for n, v in pressure['policies'].items()},
        planning_seconds=selection['planning_seconds'], alternative_trds_built=0, alternative_fuse_runs=0,
        final_trds_built=build['final_trds_built'], final_fuse_runs=build['final_fuse_runs'],
        full_fuse_pixel_comparison=False, physical_drive_verified=False,
        generic_media_frontend_integrated=False, model_is_estimate=True,
        references={str(p.relative_to(ROOT)).replace('\\', '/'): sha(p.read_bytes())
                    for p in (*paths, EVIDENCE/'manifest.json')},
        source_sha256_lf={n: sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in
            ('audit_windowed_player.py', 'summarize_fast_token_player.py', 'profile_fap3.py', 'audit_irq_fields.py',
             'summarize_native_mask_selection.py', 'summarize_uncontended_frame.py', 'test_windowed_zx0_planner.py')})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path); p.add_argument('--write', action='store_true')
    a = p.parse_args()
    if a.archive: archive(a.archive)
    result = json.loads(json.dumps(summarize()))
    if a.write: OUTPUT.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    elif result != json.loads(OUTPUT.read_bytes()): raise ValueError('saved audit differs')
    print(json.dumps(dict(totals=result['totals'], native_cpu=result['native_cpu'])), flush=True)


if __name__ == '__main__': main()
