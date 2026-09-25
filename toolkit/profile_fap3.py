"""Instruction counts and optional complete Fuse disk measurements for FAP3.

The CPU fixture counts actual executed instructions with ideal disk delivery.
Fuse supplies end-to-end elapsed time, including ROM, disk, ULA and lost IRQs.
These are different schedules: never add their totals or call their difference
physical disk latency. No partial run can verify a disk's frame deadlines.
"""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

from benchmark_context_huffman import word
from benchmark_fap3_disk import run as disk_instruction_case
from build_fap3_trd import player_harness
from bulk_frame_stream import read_packet
import disk_progress_z80 as progress
from frame_output_pipeline import display_screen
from pipelined_frame_harness import Clock, FIELD
from probe_motion_entropy import Reader


def save(path, report):
    path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


def cpu_profile(builder, start, end):
    if builder.deferred_limit:
        raise ValueError('Deferred disk builds require run_deferred_disk.py; this ideal producer does not model pending sectors.')
    ring, _ = builder.stream(start, end)
    h = player_harness(ring, builder.tables, builder.mapping, end-start, disk_reader=False,inline_matches=builder.inline_matches,
        fast_noop_scan=builder.fast_noop_scan,irq_safe_paging=builder.irq_safe_paging,static_cache_borders=builder.static_cache_borders)
    if start:
        h.cpu.banks[5][0x2400:0x3300] = builder.states[start-1].tobytes()
    screens = dict(h.expected_screens)
    for bank, index in ((5, start-1), (7, start-2)):
        if index >= 0:
            screens[bank] = builder.checkpoint_screen(index)
            h.cpu.banks[bank][:6912] = progress.reference_screen(screens[bank], 0, end-start)
    h.cpu.ay[:] = builder.ay[start]
    r = Reader(builder.raw[builder.offsets[start]:builder.offsets[end]])
    ticks = []
    for _ in range(start, end):
        _, detail = read_packet(r, stored_guards=False)
        ticks.extend(detail['ticks'])
    r.end()
    checked = dict(packet=0, compact=0, native=0, publish=0)
    bar_frames = 0

    def observe(kind, clock):
        index = checked[kind]
        if index >= end-start:
            raise AssertionError(f'extra {kind} event')
        if kind == 'compact':
            if bytes(h.cpu.banks[5][0x2400:0x3300]) != builder.states[start+index].tobytes():
                raise AssertionError(f'compact frame {start+index} differs')
        elif kind == 'native':
            screens[7 if index % 2 == 0 else 5] = display_screen(
                builder.states[start+index].tobytes(), black_borders=True)
        elif kind == 'publish':
            if (7 if h.cpu.port_7ffd & 8 else 5) != (7 if index % 2 == 0 else 5):
                raise AssertionError('wrong visible screen')
        if kind in ('native', 'publish'):
            for bank, screen in screens.items():
                expected = progress.reference_screen(screen, bar_frames, end-start)
                if bytes(h.cpu.banks[bank][:6912]) != expected:
                    raise AssertionError(f'native screen differs: frame {start+index}, bank {bank}')
        checked[kind] += 1

    clock = Clock(h, ticks, lookahead=True, observer=observe, record_underruns=True)
    h.histogram.clear()
    prime = clock.prime()
    runs = [clock.start()]
    bar_frames = 1
    for index in range(1, end-start):
        runs.append(clock.play_one())
        bar_frames += 1
        if index % 100 == 0:
            print(f'CPU: {start+index+1}/{end} frames verified', flush=True)
    drain = clock.drain()
    if (checked != dict.fromkeys(checked, end-start) or clock.ticks != (end-start)*6
            or h.cpu.consumed != len(ring) or word(h.cpu, h.r['block_left'])):
        raise AssertionError('incomplete CPU video/audio/stream verification')
    phases = Counter()
    for (address, ticks_per_instruction), count in h.histogram.items():
        row = h.instructions.get(address)
        phase = row['phase'] if row else 'banked_zx0' if 0x7c00 <= address < h.z['state'] else 'audio'
        phases[phase] += ticks_per_instruction*count
    return dict(complete=True, frame_start=start, frame_end_exclusive=end, frames=end-start,
        full_compact_and_native_comparison=True, ay_records_exact=True, played_ay_ticks=clock.ticks,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        assumptions='Spectrum 128: 70908 T/field, six fields/frame; ideal disk producer; no ULA contention',
        excluded='bootstrap, disk-refill hook, TR-DOS ROM, physical disk, outer boot-driver CALL/loop overhead',
        field_tstates=FIELD, nominal_frame_budget_tstates=6*FIELD,
        foreground_tstates=sum(phases.values()), foreground_stages=dict(phases),
        irq_tstates=clock.irq_tstates, idle_tstates=clock.idle_tstates,
        audio_underruns=clock.underruns,
        nominal_deadlines_met_with_ideal_disk=not clock.underruns and not any(p['late_fields'] for p in clock.publications),
        unchanged_player_baseline=None if builder.inline_matches or builder.fast_noop_scan or builder.irq_safe_paging or builder.static_cache_borders else '00313d3',
        player_hot_path_delta_tstates=None if builder.inline_matches or builder.fast_noop_scan or builder.irq_safe_paging or builder.static_cache_borders else 0,
        inline_matches=builder.inline_matches,
        fast_noop_scan=builder.fast_noop_scan,
        static_cache_borders=builder.static_cache_borders,
        irq_safe_paging=builder.irq_safe_paging,
        prime=prime, runs=runs, drain=drain, publications=clock.publications, events=clock.events,
        instruction_listing=list(h.instructions.values()),
        instruction_histogram=[dict(address=a, tstates=t, count=n) for (a, t), n in sorted(h.histogram.items())],
        irq_instruction_histogram=[dict(address=a, tstates=t, count=n) for (a, t), n in sorted(clock.irq_histogram.items())],
        actual_disk_deadlines_verified=False)


def summarize_fuse(report):
    complete = report['complete']
    pubs = report['publications']
    phases = report['actual_phase_tstates']
    intervals = [b['tstate']-a['tstate'] for a, b in zip(pubs, pubs[1:])]
    # Instruction/I/O phase varies within one IRQ. 64 T is the existing
    # measurement tolerance; it cannot conceal an entire 70908-T field.
    missed = [i for i, (pub, phase) in enumerate(zip(pubs, phases))
              if pub['late_fields'] or abs(phase) > 64]
    sound_ok = not (report['ay_record_field_gaps'] or report['ay_record_field_duplicates']
                    or report['audio_underruns'])
    recovery = all(run['recovered_at'] is not None for run in report['late_runs'])
    reads = report['reads']
    seeks = report.get('seek_calls', [])
    costs = [r['tstates'] for r in reads]
    return dict(complete=complete, nominal_deadlines_met=complete and not missed and sound_ok,
        missed_nominal_frame_indices=missed, missed_nominal_frames=len(missed),
        fallback_one_field_met=complete and sound_ok and recovery
            and all(-64 <= p <= FIELD+64 for p in phases)
            and all(5*FIELD-64 <= t <= 7*FIELD+64 for t in intervals),
        late_runs=report['late_runs'], late_runs_recovered=recovery,
        maximum_deviation_tstates=max(map(abs, phases), default=0),
        publication_intervals_tstates=intervals, actual_ay_50hz=sound_ok,
        ay_missing_fields=report['ay_record_field_gaps'],
        runtime_disk_reads=len(reads), disk_read_service_tstates=sum(costs),
        disk_read_min_tstates=min(costs, default=0), disk_read_max_tstates=max(costs, default=0),
        seek_service_tstates=sum(call['tstates'] for call in seeks),
        startup_and_playback_timing=report.get('elapsed_timing'),
        disk_latency_note='Fuse call intervals combine ROM execution, physical emulation, IRQs and contention; no artificial separation',
        partial_run_passes=False)


def verify_volumes(builder, records, output, fuse=None, timeout=1800):
    directory = output/'timing'; directory.mkdir(exist_ok=True)
    report = dict(complete=False, all_nominal_deadlines_met=False, release=False,
        profile='instruction counts with ideal input; optional complete Fuse measurements',
        player_hot_path_changed=builder.inline_matches or builder.fast_noop_scan or builder.irq_safe_paging or builder.static_cache_borders,
        player_hot_path_delta_tstates=None if builder.inline_matches or builder.fast_noop_scan or builder.irq_safe_paging or builder.static_cache_borders else 0, disks=[])
    # Absolute adapter costs from instruction tables, separately from ROM/disk.
    options = dict(fast_disk=builder.fast_disk, cached_seek=builder.cached_seek, interleaved=builder.interleaved,
        irq_safe_paging=builder.irq_safe_paging)
    report['disk_adapter_instruction_tstates'] = {
        name: disk_instruction_case(**options, **case) for name, case in (
            ('same_track', {}), ('track_change', dict(cached=2)),
            ('track_wrap', dict(sector=15)), ('ring_wrap', dict(high=255, region=3)))}
    report['disk_adapter_excludes'] = 'ROM execution, IRQ, ULA contention and physical latency; includes paging'
    save(output/'timing.json', report)
    try:
        for record in records:
            stem = Path(record['file']).stem
            print(f'Counting CPU instructions: {stem}', flush=True)
            cpu = cpu_profile(builder, record['frame_start'], record['frame_end_exclusive'])
            save(directory/(stem+'.cpu.json'), cpu)
            row = dict(file=record['file'], cpu_report='timing/'+stem+'.cpu.json', cpu_complete=cpu['complete'])
            report['disks'].append(row)
            if fuse:
                target = directory/(stem+'.fuse.json')
                command = [sys.executable, str(Path(__file__).with_name('measure_fap3_fuse.py')),
                    '--fuse', str(fuse.resolve()), '--trd', str(output/record['file']),
                    '--metadata', str(output/record['metadata']), '--raw', str(output/'work/stream.raw'),
                    '--states', str(output/'work/conversion.npz'), '--output', str(target), '--timeout', str(timeout)]
                subprocess.run(command, check=True)
                result = json.loads(target.read_text(encoding='utf-8'))
                row.update(fuse_report='timing/'+target.name, disk_timing=summarize_fuse(result))
            save(output/'timing.json', report)
        report['complete'] = True
        report['all_nominal_deadlines_met'] = bool(fuse) and all(
            row['disk_timing']['nominal_deadlines_met'] for row in report['disks'])
    except Exception as error:
        report['failure'] = f'{type(error).__name__}: {error}'
        save(output/'timing.json', report)
        raise
    save(output/'timing.json', report)
    return report


def main():
    import argparse
    import numpy as np
    from build_fap3_trd import Builder, sha
    from convert_video import executable
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--zx0')
    p.add_argument('--fuse', type=Path)
    p.add_argument('--timeout', type=float, default=1800)
    args = p.parse_args()
    output = args.build.resolve()
    records = json.loads((output/'volumes.json').read_text(encoding='utf-8'))
    first = json.loads((output/records[0]['metadata']).read_text(encoding='utf-8'))
    for record in records:
        if sha((output/record['file']).read_bytes()) != record['sha256']:
            raise ValueError('disk image differs from its manifest')
    with np.load(output/'work/conversion.npz', allow_pickle=False) as saved:
        states = saved['states']
    builder = Builder((output/'work/stream.raw').read_bytes(), states,
        Path(executable(args.zx0, 'zx0')), output/'work/zx0',
        fast_disk=first['fast_disk'], cached_seek=first['cached_seek'], interleaved=first['interleaved'],
        deferred_limit=first.get('deferred_limit',0),
        keepalive_fields=first.get('keepalive_fields',0),frame_service=first.get('frame_service',False),
        cold_bitmaps=first.get('cold_bitmaps',False),inline_matches=first.get('inline_matches',False),
        startup_delta=first.get('startup_delta',False),fast_noop_scan=first.get('fast_noop_scan',False),
        irq_safe_paging=first.get('irq_safe_paging',False),static_cache_borders=first.get('static_cache_borders',False))
    if sha(builder.raw) != first['raw_sha256'] or sha(states.tobytes()) != first['states_sha256']:
        raise ValueError('checkpoint or stream differs from disk metadata')
    result = verify_volumes(builder, records, output, args.fuse, args.timeout)
    manifest_path = output/'conversion.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['timing_verified'] = result['all_nominal_deadlines_met']
        # A completed independent verification also completes a prior build
        # interrupted specifically in verification, with all volume hashes checked.
        if len(records) == len(result['disks']):
            manifest['complete'] = True
            manifest.pop('failure', None)
        save(manifest_path, manifest)


if __name__ == '__main__':
    main()
