"""Audit lossless token-selected Fast ZX0 CPU and complete Fuse playback.

Saved native measurements exclude ROM/IRQ/ULA and disk latency. Fuse measures
the complete schedule; its 80 pixel samples per frame are not a full screen
comparison. Rechecking this report does not rerun the CPU or emulator.
"""
import argparse
from bisect import bisect_right
import gzip
import json
from pathlib import Path

from audit_irq_fields import audit
from build_fap3_trd import sha
from fast_token_player import select
from faster_zx0 import build as decoder
from profile_fap3 import summarize_fuse
from profile_integrated_timing import analyze, stats
from summarize_fast_return_irq import rom_invariants
from summarize_uncontended_frame import metrics
from verify_streaming_zx0_input import validate_histogram

ROOT = Path(__file__).parent
OUTPUT = ROOT/'fast_token_player_summary.json'


def pins(report):
    for name, digest in report.get('source_sha256_lf', {}).items():
        if sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n')) != digest:
            raise ValueError(('source changed', name))
    for name, digest in report.get('references', {}).items():
        if sha((ROOT/name).read_bytes()) != digest:
            raise ValueError(('reference changed', name))


def instruction_sum(rows):
    return sum(validate_histogram(bytes.fromhex(r['opcode_hex']), r['pc'], [r]) for r in rows)


def summarize():
    names = ('fast_token_player_build.json', 'fast_token_player_cpu.json', 'fast_zx0_tokens_probe.json',
             'fast_zx0_player_build.json', 'fast_zx0_player_summary.json', 'faster_zx0_cpu.json',
             'cached_huffman_lookahead_cpu.json', 'fast_reservoir_profile.json')
    paths = [ROOT/n for n in names]
    build, cpu, probe, old_build, baseline, old_cpu, frame_cpu, reserve = [json.loads(p.read_bytes()) for p in paths]
    for r in (build, cpu, probe, old_build, baseline, old_cpu, frame_cpu, reserve):
        if not r['complete']: raise ValueError('incomplete reference')
    for r in (build, cpu, probe): pins(r)
    if (build['baseline_build_sha256'] != sha(paths[3].read_bytes())
            or build['contract']['token_probe_sha256'] != sha(paths[2].read_bytes())
            or probe['player_instruction_delta_tstates'] != 0):
        raise ValueError('different baseline or token probe')
    layout = decoder('fast')[2]
    if layout != probe['decoder_layout']: raise ValueError('decoder differs')
    candidate_ticks = candidate_count = 0
    for pv, ov in zip(probe['volumes'], old_cpu['volumes'], strict=True):
        for row, original in zip(pv['blocks'], ov['variants']['fast']['blocks'], strict=True):
            if row['raw_sha256'] != original['raw_sha256']: raise ValueError('different raw input')
            for field in ('payload_sha256', 'decoder_tstates'):
                if row['variants']['min0'][field] != original[field]:
                    raise ValueError('different baseline block')
            if set(row['variants']) != {f'min{n}' for n in probe['thresholds']}:
                raise ValueError('missing threshold')
            for option in row['variants'].values():
                if 'reuses' in option:
                    if {k: v for k, v in option.items() if k != 'reuses'} != row['variants'][option['reuses']]:
                        raise ValueError('duplicate candidate differs')
                    continue
                if option['executed']:
                    if (not option['exact'] or not option['all_offsets_fit']
                            or option['minimum_slack_bytes'] < 0
                            or not option['decoder_instruction_table_checked']
                            or sum(option['slice_tstates']) != option['decoder_tstates']
                            or max(option['slice_tstates']) != option['max_slice_tstates']):
                        raise ValueError('incomplete native candidate')
                    candidate_ticks += option['decoder_tstates']; candidate_count += 1
    if instruction_sum(probe['decoder_instruction_histogram']) != candidate_ticks:
        raise ValueError('candidate instruction sum differs')

    folder = ROOT/'fast_token_player_evidence'
    manifest_path = folder/'manifest.json'; manifest = json.loads(manifest_path.read_bytes())
    if not manifest['complete']: raise ValueError('incomplete archive')
    blobs = {}
    for item in manifest['files']:
        packed = (folder/item['file']).read_bytes(); raw = gzip.decompress(packed)
        if sha(packed) != item['sha256'] or sha(raw) != item['decoded_sha256'] or len(raw) != item['decoded_bytes']:
            raise ValueError(('archive changed', item['file']))
        blobs[item['file'][:-3]] = raw
    if blobs['build.json'] != paths[0].read_bytes(): raise ValueError('different archived build')
    for name, digest in build['source_sha256_lf'].items():
        if sha(blobs['source-'+name].replace(b'\r\n', b'\n')) != digest:
            raise ValueError('different archived source')
    swaps = build['mocked_rom_swaps']
    if ([(v['from_part'], v['to_part']) for v in swaps] != [(1, 2), (2, 3)]
            or not all(v[k] for v in swaps for k in ('prompt_exact', 'wrong_disk_rejected',
                'wrong_series_rejected', 'correct_disk_accepted', 'bootstrap_ram_exact', 'rom_mocked'))):
        raise ValueError('disk-swap checks incomplete')
    volumes = []
    for part in (1, 2, 3):
        stem = f'part{part:02}'
        m = json.loads(blobs[stem+'.metadata.json']); r = json.loads(blobs[stem+'.json'])
        built = build['volumes'][part-1]; previous = old_build['volumes'][part-1]
        core = frame_cpu['volumes'][part-1]; native = cpu['volumes'][part-1]
        selection = built['fast_token_selection']
        if selection != select(probe['volumes'][part-1], margin_sectors=selection['bootstrap_margin_sectors']):
            raise ValueError('different measured token selection')
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
                or m['fast_token_selection'] != selection or m['fast_zx0'] != built['fast_zx0']
                or not all(built[k] for k in ('dirty_ram_boot_exact', 'first_native_screen_exact',
                    'second_compact_frame_exact', 'audio_bank_immutable_exact', 'exact_video_field_roundtrip'))):
            raise ValueError(('incomplete playback or boot', part))
        for key in ('raw_video_sha256', 'audio_sha256', 'frames'):
            if built[key] != previous[key]: raise ValueError(('decoded content differs', part, key))
        if (native['stream_sha256'] != built['stream_sha256'] or native['layout'] != layout
                or m['fast_zx0']['layout'] != layout or not m['fast_zx0']['producer_reassembled_exact']
                or any(v['delta_tstates'] != 0 for v in m['fast_zx0']['external_operands'])):
            raise ValueError('different native decoder or stream')
        ns = native['summary']
        if not ns['complete'] or not ns['sectors_exact_once'] or not ns['decoder_instruction_table_checked']:
            raise ValueError('incomplete native volume')
        for row, candidate, name, original in zip(native['blocks'], probe['volumes'][part-1]['blocks'],
                selection['names'], old_cpu['volumes'][part-1]['variants']['fast']['blocks'], strict=True):
            option = candidate['variants'][name]
            if (not row['exact'] or row['raw_sha256'] != candidate['raw_sha256']
                    or row['payload_sha256'] != option['payload_sha256']
                    or row['decoder_tstates'] != option['decoder_tstates']
                    or sum(row['slice_tstates']) != row['decoder_tstates']
                    or row['begin_tstates']+sum(row['step_tstates']) != row['producer_tstates']):
                raise ValueError('different selected native block')
            for field in ('decoder', 'producer'):
                if row[field+'_delta_tstates'] != row[field+'_tstates']-original[field+'_tstates']:
                    raise ValueError('different block delta')
        for field in ('decoder_tstates', 'producer_tstates'):
            if sum(b[field] for b in native['blocks']) != ns[field]: raise ValueError('native volume sum differs')
        if (instruction_sum(ns['decoder_instruction_histogram']) != ns['decoder_tstates']
                or sum(i['count']*i['tstates'] for i in ns['instruction_histogram']) != ns['producer_tstates']
                or ns['producer_tstates']+ns['decoder_tstates'] != ns['total_tstates']
                or ns['sector_reads'] != m['video_sectors']
                or selection['decoder_tstates'] != ns['decoder_tstates']):
            raise ValueError('native instruction/sector totals differ')
        for suffix, key in (('.trace.txt', 'trace_sha256'), ('.debugger.txt', 'debugger_script_sha256')):
            if sha(blobs[stem+suffix]) != r[key]: raise ValueError('trace changed')
        irq = audit(r, m); irq.pop('actual_phase_tstates')
        gates = summarize_fuse(r); gates.pop('publication_intervals_tstates')
        profile = analyze(r, m, core)
        original_frames = reserve['volumes'][part-1]['frames']
        positions = [row['raw_position'] for row in original_frames]
        positions.append(positions[-1]+original_frames[-1]['packet_bytes'])
        ends = [0]+[b['raw_end'] for b in m['blocks']]
        available_rows = []; packet_counts = []
        starts = [e for e in r['pipeline_events'] if e['kind'] == 'packet_start']
        for i, event in enumerate(starts):
            completed = len(ends)-1-event['blocks_left']
            block = bisect_right(ends, positions[i])-1
            available = ends[completed]-positions[i]
            if event['phase'] == 2: available += event['slice_output']-0xc000
            if (event['count'] != completed-block or event['position'] != positions[i]-ends[block]
                    or not 0 <= available <= 3*15872 or event['phase'] not in (0, 1, 2)
                    or event['count']+(event['phase'] != 0) > 3):
                raise ValueError('queue reserve or ownership differs')
            available_rows.append(available)
            packet_counts.append(max(0, bisect_right(positions, positions[i]+available)-1-i))
        if len(available_rows) != m['frames']: raise ValueError('incomplete reserve trace')
        reservoir = dict(decoded_available_bytes=stats(available_rows),
            complete_packets_available=stats(packet_counts),
            starts_at_most_six_bytes=sum(n <= 6 for n in available_rows),
            compact_at_least_one_period_early=sum(row['nominal_tstate']-row['stages']['prepare']['end'] >= 6*70908
                for row in profile['frames']))
        worst = sorted(profile.pop('frames'), key=lambda v: v['work_elapsed'], reverse=True)[:8]
        after = dict(metrics(r), timing_gates=gates, irq=irq, rom=rom_invariants(r, True),
            used_sectors=m['used_sectors'], free_sectors=m['free_sectors'], video_bytes=m['video_bytes'],
            video_start_sector=m['video_start_sector'], trd_sha256=m['trd_sha256'],
            ay_record_field_gaps=r['ay_record_field_gaps'], ay_record_field_duplicates=r['ay_record_field_duplicates'],
            read_service=stats([v['tstates'] for v in r['reads']]),
            keepalive_service=stats([v['tstates'] for v in r['seek_calls'] if v['kind'] == 'keepalive']),
            delivery_profile=profile, worst_work_frames=worst, reservoir=reservoir)
        before = baseline['volumes'][part-1]['fast']
        delta = {k: after[k]-before[k] for k in ('nominal_late_frames', 'audio_underruns', 'runtime_sectors',
            'publication_span_tstates', 'bad_actual_intervals', 'used_sectors', 'video_bytes',
            'read_service_tstates', 'seek_service_tstates')}
        volumes.append(dict(part=part, selected_tokens=after, delta=delta))
    for key, total in cpu['totals'].items():
        if (total != sum(v['summary'][key] for v in cpu['volumes'])
                or cpu['baseline_totals'][key] != old_cpu['totals']['fast'][key]
                or cpu['deltas'][key] != total-cpu['baseline_totals'][key]):
            raise ValueError('native aggregate differs')
    keys = ('frames', 'nominal_late_frames', 'audio_underruns', 'ay_ticks', 'runtime_sectors',
            'publication_span_tstates', 'bad_actual_intervals', 'used_sectors', 'video_bytes',
            'read_service_tstates', 'seek_service_tstates')
    totals = {k: sum(v['selected_tokens'][k] for v in volumes) for k in keys}
    if totals['frames'] != 4221 or totals['ay_ticks'] != 6*totals['frames']:
        raise ValueError('incomplete movie')
    totals.update(nominal_schedule_met=all(v['selected_tokens']['timing_gates']['nominal_deadlines_met'] for v in volumes),
        fallback_met=all(v['selected_tokens']['timing_gates']['fallback_one_field_met'] for v in volumes),
        ay_50hz_met=all(v['selected_tokens']['timing_gates']['actual_ay_50hz'] for v in volumes))
    return dict(complete=True, release=False, scope=__doc__, baseline_commit='2881667',
        totals=totals, baseline_totals=baseline['totals'], volumes=volumes,
        native_cpu=cpu['totals'], native_cpu_baseline=cpu['baseline_totals'], native_cpu_delta=cpu['deltas'],
        unique_native_candidates=candidate_count, unchanged_decoded_video_and_audio=True,
        player_instruction_delta_tstates=0, full_fuse_pixel_comparison=False,
        full_integrated_cpu_total_measured=False, physical_drive_verified=False,
        initial_disk_and_irq_phases_not_matched=True,
        references={p.name: sha(p.read_bytes()) for p in (*paths, manifest_path)},
        source_sha256_lf={n: sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in
            ('summarize_fast_token_player.py', 'measure_fap3_fuse.py', 'profile_integrated_timing.py',
             'profile_fap3.py', 'audit_irq_fields.py', 'summarize_fast_return_irq.py', 'summarize_uncontended_frame.py')})


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--write', action='store_true')
    args = p.parse_args(); result = json.loads(json.dumps(summarize()))
    if args.write: OUTPUT.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    elif result != json.loads(OUTPUT.read_bytes()): raise ValueError('saved summary differs')
    print(json.dumps(dict(totals=result['totals'], native_cpu_delta=result['native_cpu_delta'])), flush=True)


if __name__ == '__main__': main()
