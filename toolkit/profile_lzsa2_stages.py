"""Reprofile the unchanged LZSA2 test disk: CPU components and real Fuse stages.

Do not add nested elapsed windows to CPU component measurements. The frame
model excludes packet transport, disk, IRQ and ULA; the LZSA2 model uses fixed
256-byte demands, which differ from the actual playback demand schedule.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLKIT = ROOT / 'toolkit'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def prepare(work):
    work.mkdir(parents=True, exist_ok=True)
    sources = {
        'metadata.json': 'lzsa2_dispatch_evidence/metadata.json.gz',
        'input.fap3': 'row_lzsa_evidence/fap3-video.raw.gz',
        'video.raw': 'row_lzsa_evidence/video.raw.gz',
        'video.stream': 'row_lzsa_evidence/video.stream.gz',
    }
    for name, source in sources.items():
        (work / name).write_bytes(gzip.decompress((TOOLKIT / source).read_bytes()))
    prior = load(TOOLKIT / 'lzsa2_dispatch.json')
    meta = load(work / 'metadata.json')
    image = ROOT / prior['selected_image']
    assert sha(image.read_bytes()) == meta['trd_sha256'] == prior['selected_trd_sha256']
    assert sha((work / 'input.fap3').read_bytes()) == meta['raw_sha256']
    assert sha((work / 'video.stream').read_bytes()) == prior['unchanged_stream_sha256']
    for name, digest in prior['source_sha256_lf'].items():
        assert sha((TOOLKIT / name).read_bytes().replace(b'\r\n', b'\n')) == digest, name
    return image


def commands(work, image, fuse):
    states = TOOLKIT / 'five_level_test_evidence/states.npz'
    return [
        ['benchmark_row_lzsa.py', '--stream', work / 'video.stream', '--raw', work / 'video.raw',
         '--metadata', work / 'metadata.json', '--output', work / 'transport.json'],
        ['profile_row_cpu.py', '--raw', work / 'input.fap3', '--states', states,
         '--metadata', work / 'metadata.json', '--output', work / 'frame.json'],
        ['measure_fap3_fuse.py', '--fuse', fuse, '--trd', image, '--metadata', work / 'metadata.json',
         '--raw', work / 'input.fap3', '--states', states, '--output', work / 'timing.json', '--trace-pipeline'],
    ]


def summarize(work, evidence, output):
    from profile_integrated_timing import analyze, merged, overlap
    import resumable_lzsa2

    meta, frame, transport, timing = [load(work / (n + '.json'))
                                      for n in ('metadata', 'frame', 'transport', 'timing')]
    assert frame['complete'] and transport['complete'] and timing['complete']
    assert frame['full_compact_and_both_native_exact'] and transport['all_instruction_timings_verified']
    assert meta['raw_sha256'] == frame['raw_sha256'] == sha((work / 'input.fap3').read_bytes())
    assert transport['raw_sha256'] == sha((work / 'video.raw').read_bytes())
    assert transport['stream_sha256'] == sha((work / 'video.stream').read_bytes())
    assert transport['native'] == meta['lzsa2']['layout']
    assert timing['ay_records_exact'] and timing['ay_ticks'] == meta['frames'] * 6
    assert not any(timing[k] for k in ('audio_underruns', 'ay_record_field_gaps', 'ay_record_field_duplicates'))
    assert timing['runtime_sectors_checked'] == meta['video_sectors']
    assert sha((work/'metadata.json').read_bytes()) == timing['integrated_bootstrap_metadata_sha256']
    assert sha((work/'timing.trace.txt').read_bytes()) == timing['trace_sha256']
    assert sha((work/'timing.debugger.txt').read_bytes()) == timing['debugger_script_sha256']
    previous_frame = json.loads(gzip.decompress((TOOLKIT/'row_fragment_evidence/slack16-cpu.json.gz').read_bytes()))
    for key in ('raw_sha256', 'states_sha256', 'tstates', 'stages'):
        assert frame[key] == previous_frame[key], ('frame fixture changed', key)
    profile = analyze(timing, meta, frame)
    (work / 'elapsed.json').write_text(json.dumps(profile, indent=2) + '\n', encoding='utf-8', newline='\n')
    start = profile['frames'][0]['stages']['transfer']['start']
    end = timing['publications'][-1]['tstate']
    span = end - start
    elapsed = {name: row['elapsed']['total'] for name, row in profile['stages'].items()}
    elapsed['control_prefetch_or_wait'] = span - sum(elapsed.values())
    assert elapsed['control_prefetch_or_wait'] >= 0
    elapsed_rows = [dict(stage=k, tstates=v, percent=100*v/span,
                         mean_ms_per_frame=v/(70908*50)*1000/meta['frames']) for k, v in elapsed.items()]
    service = merged([(r['start_tstate'], r['end_tstate']) for key in ('reads', 'seek_calls') for r in timing[key]])
    disk_total = overlap(service, start, end)
    disk_distribution = {k: v['disk_service']['total'] for k, v in profile['stages'].items()}
    disk_distribution['control_prefetch_or_wait'] = disk_total - sum(disk_distribution.values())
    assert min(disk_distribution.values()) >= 0

    frame_groups = Counter()
    for stage, ticks in frame['stages'].items():
        if any(word in stage for word in ('motion', 'spatial', 'cache')):
            group = 'motion_spatial_and_cache'
        elif stage.startswith('output/'):
            group = 'screen_output'
        elif stage.startswith('metadata/'):
            group = 'metadata'
        elif 'huffman' in stage:
            group = 'huffman_corrections'
        elif stage == 'reconstruct/fast_fragment':
            group = 'fragments'
        elif stage in ('reconstruct/attribute_pass', 'attribute_groups/attribute_groups'):
            group = 'attribute_reconstruction'
        else:
            group = 'reconstruction_control_and_patches'
        frame_groups[group] += ticks
    frame_groups.setdefault('motion_spatial_and_cache', 0)
    assert sum(frame_groups.values()) == frame['tstates']

    _, labels, generated = resumable_lzsa2.build(core=meta['pre_fast_bank2_zx0']['new_origin'],
                                              core_limit=meta['pre_fast_bank2_zx0']['new_end'])
    assert generated == transport['native']
    listing = {r['address']: r for r in generated['instruction_listing']}
    decoder_groups, copied, repeat_overhead = Counter(), Counter(), Counter()
    for row in transport['decoder_histogram']:
        pc = row['pc']; instruction = listing[pc]['instruction']
        if instruction in ('LDI', 'LDIR'):
            group = 'match_copy' if labels['MatchUseC'] <= pc < labels['ReadToken'] else 'literal_copy'
            copied[group] += row['count']
            if instruction == 'LDIR' and row['tstates'] == 21:
                repeat_overhead[group] += 5 * row['count']
        elif resumable_lzsa2.PREFIX <= pc < generated['prefix_end']:
            group = 'resume_wrapper'
        elif labels['ReadToken'] <= pc < labels['Token']:
            group = 'quota_checks_and_yield'
        else:
            group = 'token_lengths_offsets_and_copy_setup'
        decoder_groups[group] += row['tstates'] * row['count']
    assert sum(decoder_groups.values()) == transport['decoder_tstates']
    assert sum(copied.values()) == transport['decoded_bytes']

    # A lower bound only: excludes bridge setup, paging, calls and queue work.
    packet_copy_minimum = 16 * transport['decoded_bytes']
    pool = frame['tstates'] + transport['total_tstates'] + packet_copy_minimum
    cpu_rows = dict(frame_groups, lzsa2=transport['decoder_tstates'],
                    producer=transport['producer_tstates'], packet_copy_lower_bound=packet_copy_minimum)
    cpu_rows = [dict(stage=k, tstates=v, percent_of_component_pool=100*v/pool)
                for k, v in sorted(cpu_rows.items(), key=lambda row: -row[1])]
    assert sum(r['tstates'] for r in cpu_rows) == pool

    windows = []
    source_starts = (629, 2857, 3855)
    for index, source in enumerate(source_starts):
        rows = profile['frames'][index*64:(index+1)*64]
        windows.append(dict(local_start=index*64, source_start=source, frames=len(rows),
            elapsed={k: sum(f['stages'][k]['elapsed'] for f in rows) for k in profile['stages']},
            missed_nominal_deadlines=sum(f['late_fields'] > 0 for f in rows),
            max_late_fields=max(f['late_fields'] for f in rows)))
    prior = load(TOOLKIT / 'lzsa2_dispatch.json')['variants'][1]
    publication_span = timing['publications'][-1]['tstate'] - timing['publications'][0]['tstate']
    report = dict(complete=True, release=False, baseline_commit='de0a50d',
        scope=__doc__, player_changed=False, instruction_tstate_delta=0, compressed_byte_delta=0,
        frames=meta['frames'], blocks=len(transport['blocks']), trd_sha256=meta['trd_sha256'],
        raw_sha256=meta['raw_sha256'], stream_sha256=transport['stream_sha256'],
        states_sha256=frame['states_sha256'], runtime_video_sectors=meta['video_sectors'],
        measured_span=dict(start='first packet_start (after initial queue prefill)', end='last publication OUT',
                           tstates=span, normalized_seconds=span/(70908*50)),
        elapsed_stages=elapsed_rows, disk_windows=dict(total_tstates=disk_total, distribution=disk_distribution,
            all_read_windows_tstates=sum(r['tstates'] for r in timing['reads']),
            all_seek_windows_tstates=sum(r['tstates'] for r in timing['seek_calls']),
            note='Nested elapsed service windows include ROM/IRQ/ULA and drive service; not pure physical latency.'),
        empty_wait_tstates=profile['empty_wait']['total'], queue_at_packet=profile['queue_at_packet'],
        cpu_components=cpu_rows, cpu_component_pool_tstates=pool, frame_cpu_stages=frame['stages'],
        lzsa2_cpu_stages=dict(decoder_groups), lzsa2_copy_bytes=dict(copied),
        ldir_repeat_overhead_tstates=dict(repeat_overhead),
        ldir_bound_note='Ideal removable 5 T per repeated LDIR iteration. A real unrolled loop needs dispatch/tails/code space; not a measured saving.',
        max_observed_slice_tstates=transport['max_slice_tstates'], windows=windows,
        stage_statistics=profile['stages'], late_phase_histogram=profile['late_phase_histogram'],
        fps=(meta['frames']-1)*70908*50/publication_span,
        publication_span_tstates=publication_span,
        previous_run_span_tstates=prior['publication_span_tstates'],
        run_span_difference_tstates=publication_span-prior['publication_span_tstates'],
        missed_nominal_deadlines=timing['nominal_late_frames'], max_late_fields=timing['max_late_fields'],
        bad_actual_intervals=timing['bad_actual_intervals'], late_runs=timing['late_runs'],
        ay_ticks=timing['ay_ticks'], ay_exact=True, pixel_samples_per_frame=timing['pixel_samples_per_frame'],
        limitations=['192-frame montage, not full movie or physical hardware',
                     'CPU components exclude ULA, IRQ, ROM and real drive latency',
                     'Fixed decoder demands differ from production scheduling',
                     'Packet-copy count is an instruction lower bound, not full bridge cost',
                     'CPU component pool is not elapsed-time coverage; percentages are not runtime shares',
                     'Control/prefetch/wait gap is mixed work, not pure idle time'])
    sources = ('profile_lzsa2_stages.py', 'profile_row_cpu.py', 'profile_frame_hotspots.py',
               'benchmark_row_lzsa.py', 'measure_fap3_fuse.py', 'profile_integrated_timing.py',
               'resumable_lzsa2.py', 'frame_output_pipeline.py', 'causal_tile_z80.py', 'cell_screen_z80.py',
               'uncontended_frame.py', 'inline_huffman_patches.py', 'compact_cursor.py', 'row_dictionary_video.py')
    report['source_sha256_lf'] = {n: sha((TOOLKIT/n).read_bytes().replace(b'\r\n', b'\n')) for n in sources}
    evidence.mkdir(parents=True, exist_ok=True)
    report['evidence'] = []
    for name in ('frame.json', 'transport.json', 'timing.json', 'timing.trace.txt', 'timing.debugger.txt', 'elapsed.json'):
        raw = (work/name).read_bytes(); packed = gzip.compress(raw, mtime=0)
        (evidence/(name+'.gz')).write_bytes(packed)
        report['evidence'].append(dict(file=name+'.gz', sha256=sha(packed), raw_sha256=sha(raw)))
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: report[k] for k in ('elapsed_stages', 'cpu_components', 'lzsa2_cpu_stages',
          'disk_windows', 'queue_at_packet', 'fps', 'missed_nominal_deadlines', 'run_span_difference_tstates')}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=ROOT/'.tmp/lzsa2-stages')
    parser.add_argument('--fuse', type=Path, default=ROOT/'tools/fuse-1.9.0-sdl/fuse.exe')
    parser.add_argument('--evidence', type=Path, default=TOOLKIT/'lzsa2_stage_evidence')
    parser.add_argument('--output', type=Path, default=TOOLKIT/'lzsa2_stage_profile.json')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--prepare-only', action='store_true')
    group.add_argument('--summarize-only', action='store_true')
    args = parser.parse_args()
    if not args.summarize_only:
        image = prepare(args.work)
        if args.prepare_only:
            print(json.dumps([[str(x) for x in row] for row in commands(args.work, image, args.fuse)]))
            return
        for row in commands(args.work, image, args.fuse):
            subprocess.run([sys.executable, str(TOOLKIT/row[0]), *map(str, row[1:])], check=True, cwd=ROOT)
    summarize(args.work, args.evidence, args.output)


if __name__ == '__main__':
    main()
