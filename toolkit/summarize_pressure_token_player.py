"""Audit two complete pressure-selected Fast ZX0 builds and Fuse runs.

Native T-states, measured disk service, nominal deadlines and fallback
recovery are separate results. No estimate can pass a playback gate.
"""
import argparse
from bisect import bisect_right
import json
from pathlib import Path

from audit_irq_fields import audit
from build_fap3_trd import sha
from faster_zx0 import build as decoder
from pressure_zx0_tokens import generate
from profile_fap3 import summarize_fuse
from profile_integrated_timing import analyze, stats
from summarize_fast_return_irq import rom_invariants
from summarize_fast_token_player import pins, instruction_sum
from summarize_native_mask_selection import read_archive
from summarize_uncontended_frame import metrics

ROOT = Path(__file__).parent
OUTPUT = ROOT/'pressure_token_summary.json'
KEYS = ('frames', 'nominal_late_frames', 'audio_underruns', 'ay_ticks', 'runtime_sectors',
        'publication_span_tstates', 'bad_actual_intervals', 'read_service_tstates', 'seek_service_tstates')
CPU_KEYS = ('producer_tstates', 'decoder_tstates', 'total_tstates', 'sector_reads', 'carry_copy_bytes')


def summarize():
    paths = [ROOT/n for n in ('pressure_zx0_tokens.json', 'fast_zx0_tokens_probe.json',
        'fast_zx0_player_build.json', 'fast_zx0_player_summary.json', 'fast_token_player_summary.json',
        'fast_reservoir_profile.json', 'cached_huffman_lookahead_cpu.json', 'faster_zx0_cpu.json')]
    choices, probe, baseline_build, baseline, unweighted, reservoir, frame_cpu, old_cpu = [json.loads(p.read_bytes()) for p in paths]
    if not all(r['complete'] for r in (choices, probe, baseline_build, baseline, unweighted, reservoir, frame_cpu, old_cpu)):
        raise ValueError('incomplete reference')
    if json.loads(json.dumps(generate())) != choices: raise ValueError('different policy selections')
    pins(probe); pins(choices)
    layout = decoder('fast')[2]
    outcomes = {}
    for name in ('weight4', 'weight16'):
        build_path = ROOT/f'pressure_token_{name}_build.json'
        cpu_path = ROOT/f'pressure_token_{name}_cpu.json'
        folder = ROOT/'pressure_token_evidence'/name
        paths.extend((build_path, cpu_path, folder/'manifest.json'))
        build, cpu = [json.loads(p.read_bytes()) for p in (build_path, cpu_path)]
        if not build['complete'] or not cpu['complete']: raise ValueError('incomplete changed-player proof')
        pins(build); pins(cpu)
        blobs = read_archive(folder, packed_sizes=False)
        if blobs['build.json'] != build_path.read_bytes(): raise ValueError('different archived build')
        for source, digest in build['source_sha256_lf'].items():
            if sha(blobs['source-'+source].replace(b'\r\n', b'\n')) != digest:
                raise ValueError('different archived generator')
        swaps = build['mocked_rom_swaps']
        if ([(v['from_part'], v['to_part']) for v in swaps] != [(1, 2), (2, 3)]
                or not all(v[k] for v in swaps for k in ('prompt_exact', 'wrong_disk_rejected',
                    'wrong_series_rejected', 'correct_disk_accepted', 'bootstrap_ram_exact', 'rom_mocked'))):
            raise ValueError('disk-swap checks incomplete')
        volumes = []
        for part in (1, 2, 3):
            stem = f'part{part:02}'; m = json.loads(blobs[stem+'.metadata.json']); r = json.loads(blobs[stem+'.json'])
            built = build['volumes'][part-1]; native = cpu['volumes'][part-1]
            core = frame_cpu['volumes'][part-1]; wanted = choices['volumes'][part-1]['selections'][name]
            if (not r['complete'] or r['failure'] or r['errors'] or not r['trace_nonce_exact']
                    or not r['ay_records_exact'] or not r['progress_100_percent'] or r['debugger_installed_bytes']
                    or r['frames'] != m['frames'] or r['native_frames_sampled'] != m['frames']
                    or r['pixel_samples_per_frame'] != 80 or r['ay_ticks'] != 6*m['frames']
                    or r['runtime_sectors_checked'] != m['video_sectors'] or not m['independently_bootable']
                    or m['used_sectors'] > 2544 or m['raw_sha256'] != core['raw_sha256']
                    or core['checked_frames'] != m['frames'] or r['trd_sha256'] != m['trd_sha256']
                    or m['trd_sha256'] != built['trd_sha256'] or m['trd_sha256'] != native['trd_sha256']
                    or sha(blobs[stem+'.metadata.json']) != r['integrated_bootstrap_metadata_sha256']
                    or sha(blobs[stem+'.metadata.json']) != built['metadata_sha256']
                    or m['fast_token_selection'] != wanted or built['fast_token_selection'] != wanted
                    or m['fast_zx0']['layout'] != layout or native['layout'] != layout
                    or built['stream_sha256'] != native['stream_sha256']
                    or not m['fast_zx0']['producer_reassembled_exact']
                    or any(v['delta_tstates'] != 0 for v in m['fast_zx0']['external_operands'])
                    or not all(built[k] for k in ('dirty_ram_boot_exact', 'first_native_screen_exact',
                        'second_compact_frame_exact', 'audio_bank_immutable_exact', 'exact_video_field_roundtrip'))):
                raise ValueError(('incomplete playback or changed decoder', name, part))
            for k in ('frames', 'raw_video_sha256', 'audio_sha256'):
                if built[k] != baseline_build['volumes'][part-1][k]: raise ValueError('different content')
            for b, p, selection, old in zip(native['blocks'], probe['volumes'][part-1]['blocks'], wanted['names'],
                    old_cpu['volumes'][part-1]['variants']['fast']['blocks'], strict=True):
                option = p['variants'][selection]
                if (not b['exact'] or b['raw_sha256'] != p['raw_sha256'] or b['payload_sha256'] != option['payload_sha256']
                        or b['decoder_tstates'] != option['decoder_tstates']
                        or sum(b['slice_tstates']) != b['decoder_tstates']
                        or b['begin_tstates']+sum(b['step_tstates']) != b['producer_tstates']):
                    raise ValueError('selected native block differs')
                for k in ('producer', 'decoder'):
                    if b[k+'_delta_tstates'] != b[k+'_tstates']-old[k+'_tstates']: raise ValueError('block delta differs')
            ns = native['summary']
            if (not ns['complete'] or not ns['sectors_exact_once'] or not ns['decoder_instruction_table_checked']
                    or ns['sector_reads'] != m['video_sectors'] or ns['decoder_tstates'] != wanted['decoder_tstates']
                    or instruction_sum(ns['decoder_instruction_histogram']) != ns['decoder_tstates']
                    or sum(i['count']*i['tstates'] for i in ns['instruction_histogram']) != ns['producer_tstates']
                    or ns['total_tstates'] != ns['producer_tstates']+ns['decoder_tstates']):
                raise ValueError('native instruction totals differ')
            for k in ('producer_tstates', 'decoder_tstates'):
                if ns[k] != sum(b[k] for b in native['blocks']): raise ValueError('native block sums differ')
            for suffix, key in (('.trace.txt', 'trace_sha256'), ('.debugger.txt', 'debugger_script_sha256')):
                if sha(blobs[stem+suffix]) != r[key]: raise ValueError('trace changed')
            irq = audit(r, m); irq.pop('actual_phase_tstates')
            gates = summarize_fuse(r); gates.pop('publication_intervals_tstates')
            profile = analyze(r, m, core)
            frames = reservoir['volumes'][part-1]['frames']
            positions = [f['raw_position'] for f in frames]+[frames[-1]['raw_position']+frames[-1]['packet_bytes']]
            ends = [0]+[b['raw_end'] for b in m['blocks']]; available_rows = []; packet_counts = []
            for i, event in enumerate(e for e in r['pipeline_events'] if e['kind'] == 'packet_start'):
                completed = len(ends)-1-event['blocks_left']; block = bisect_right(ends, positions[i])-1
                available = ends[completed]-positions[i]
                if event['phase'] == 2: available += event['slice_output']-0xc000
                if (event['count'] != completed-block or event['position'] != positions[i]-ends[block]
                        or not 0 <= available <= 47616 or event['phase'] not in (0, 1, 2)
                        or event['count']+(event['phase'] != 0) > 3):
                    raise ValueError('queue ownership or reserve differs')
                available_rows.append(available)
                packet_counts.append(max(0, bisect_right(positions, positions[i]+available)-1-i))
            if len(available_rows) != m['frames']: raise ValueError('incomplete reserve trace')
            reserve = dict(decoded_available_bytes=stats(available_rows), complete_packets_available=stats(packet_counts),
                starts_at_most_six_bytes=sum(n <= 6 for n in available_rows))
            worst = sorted(profile.pop('frames'), key=lambda f: f['work_elapsed'], reverse=True)[:8]
            result = dict(metrics(r), timing_gates=gates, irq=irq, rom=rom_invariants(r, True),
                used_sectors=m['used_sectors'], free_sectors=m['free_sectors'], video_bytes=m['video_bytes'],
                video_start_sector=m['video_start_sector'], trd_sha256=m['trd_sha256'],
                ay_record_field_gaps=r['ay_record_field_gaps'], ay_record_field_duplicates=r['ay_record_field_duplicates'],
                reservoir=reserve, delivery_profile=profile, worst_work_frames=worst)
            deltas = {label:{k: result[k]-old[k] for k in KEYS} for label, old in
                (('fast', baseline['volumes'][part-1]['fast']),
                 ('unweighted', unweighted['volumes'][part-1]['selected_tokens']))}
            volumes.append(dict(part=part, playback=result, deltas=deltas))
        for key in CPU_KEYS:
            if (cpu['totals'][key] != sum(v['summary'][key] for v in cpu['volumes'])
                    or cpu['baseline_totals'][key] != old_cpu['totals']['fast'][key]
                    or cpu['deltas'][key] != cpu['totals'][key]-cpu['baseline_totals'][key]):
                raise ValueError('native aggregate differs')
        totals = {k: sum(v['playback'][k] for v in volumes) for k in (*KEYS, 'used_sectors', 'video_bytes')}
        if totals['frames'] != 4221 or totals['ay_ticks'] != 25326: raise ValueError('incomplete movie')
        totals.update(nominal_schedule_met=all(v['playback']['timing_gates']['nominal_deadlines_met'] for v in volumes),
            fallback_met=all(v['playback']['timing_gates']['fallback_one_field_met'] for v in volumes),
            ay_50hz_met=all(v['playback']['timing_gates']['actual_ay_50hz'] for v in volumes))
        outcomes[name] = dict(volumes=volumes, totals=totals, native_cpu=cpu['totals'], native_cpu_delta=cpu['deltas'])
    return dict(complete=True, release=False, scope=__doc__, baseline_commit='2881667',
        policies=outcomes, fast_baseline=baseline['totals'], unweighted_baseline=unweighted['totals'],
        unchanged_decoded_video_and_audio=True, player_instruction_delta_tstates=0,
        full_fuse_pixel_comparison=False, physical_drive_verified=False, initial_disk_and_irq_phases_not_matched=True,
        references={str(p.relative_to(ROOT)).replace('\\', '/'): sha(p.read_bytes()) for p in paths},
        source_sha256_lf={n: sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in
            ('summarize_pressure_token_player.py', 'summarize_fast_token_player.py', 'measure_fap3_fuse.py',
             'profile_integrated_timing.py', 'audit_irq_fields.py', 'profile_fap3.py',
             'summarize_fast_return_irq.py', 'summarize_native_mask_selection.py', 'summarize_uncontended_frame.py')})


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--write', action='store_true')
    args = p.parse_args(); result = json.loads(json.dumps(summarize()))
    if args.write: OUTPUT.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    elif result != json.loads(OUTPUT.read_bytes()): raise ValueError('saved summary differs')
    print(json.dumps({n: r['totals'] for n, r in result['policies'].items()}), flush=True)


if __name__ == '__main__': main()
