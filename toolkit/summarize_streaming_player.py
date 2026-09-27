"""Archive and audit all three complete streaming-input player measurements.

HL/EXX is the previous playback baseline. Its archived evidence is retained;
old source pins are historical, while the new build and CPU model must match
the current source. Timings include changed disk placement/starting phase.
"""
import argparse
import copy
import gzip
import json
from pathlib import Path

from audit_irq_fields import audit
from build_fap3_trd import sha
from profile_integrated_timing import analyze, stats
from summarize_fast_return_irq import rom_invariants
from summarize_transfer_prefetch import audio_analysis, first_late_window
from summarize_uncontended_frame import metrics

ROOT = Path(__file__).parent


def pins(mapping):
    for name, digest in mapping.items():
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError(('source changed', name))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('fuse', 'directory', 'cpu'):
        p.add_argument('--' + name, type=Path)
    a = p.parse_args()
    evidence = ROOT / 'streaming_player_evidence'
    output = ROOT / 'streaming_player_summary.json'
    baseline_path = ROOT / 'hl_mask_reader_summary.json'
    baseline = json.loads(baseline_path.read_bytes())
    files = [v for v in baseline['evidence'] if v['file'].startswith('hl_')]
    if a.fuse:
        if a.directory is None or a.cpu is None:
            raise ValueError('all fresh paths required')
        evidence.mkdir(exist_ok=True)
        blobs = {'streaming_cpu.json': a.cpu.read_bytes()}
        for part in (1, 2, 3):
            stem = f'part{part:02}'
            for suffix in ('.json', '.debugger.txt', '.trace.txt'):
                blobs['streaming_' + stem + suffix] = (a.fuse / (stem + suffix)).read_bytes()
            blobs['streaming_' + stem + '.metadata.json'] = (
                a.directory / f'ZX-video-huffman-preview_part{part:02}.json').read_bytes()
        for name, raw in blobs.items():
            packed = gzip.compress(raw, mtime=0)
            name += '.gz'
            (evidence / name).write_bytes(packed)
            files.append(dict(directory=evidence.name, file=name,
                              sha256=sha(packed), uncompressed_sha256=sha(raw)))
    else:
        previous = json.loads(output.read_bytes())
        pins(previous['source_sha256'])
        if previous['baseline_summary_sha256'] != sha(baseline_path.read_bytes()):
            raise ValueError('baseline summary changed')
        files = previous['evidence']
    for f in files:
        raw = (ROOT / f['directory'] / f['file']).read_bytes()
        if sha(raw) != f['sha256'] or sha(gzip.decompress(raw)) != f['uncompressed_sha256']:
            raise ValueError(('archive changed', f['file']))

    def blob(name):
        f = next(v for v in files if v['file'] == name)
        return gzip.decompress((ROOT / f['directory'] / name).read_bytes())

    build_path = ROOT / 'streaming_player_build.json'
    build = json.loads(build_path.read_bytes())
    core_path = ROOT / 'streaming_inline_zx0_cpu.json'
    core = json.loads(core_path.read_bytes())
    if not build['complete'] or not core['complete']:
        raise ValueError('incomplete build or core CPU')
    pins(build['source_sha256'])
    pins(core['sources'])
    cpus = {v: json.loads(blob(v + '_cpu.json.gz')) for v in ('hl', 'streaming')}
    for variant, c in cpus.items():
        if not c['complete'] or c['frames'] != 4221:
            raise ValueError('incomplete queue replay')
        script = 'replay_streaming_queue.py' if variant == 'streaming' else 'replay_queue_calls.py'
        if c['source_sha256'] != sha((ROOT / script).read_bytes()):
            raise ValueError('queue model changed')
        if variant == 'streaming':
            pins(c['model_sources'])
    frame_cpu = json.loads((ROOT / 'inline_huffman_patches_cpu.json').read_bytes())
    volumes = []
    for part in (1, 2, 3):
        row = dict(part=part)
        for variant in ('hl', 'streaming'):
            stem = f'{variant}_part{part:02}'
            raw = blob(stem + '.json.gz')
            r = json.loads(raw)
            meta = blob(stem + '.metadata.json.gz')
            m = json.loads(meta)
            c = cpus[variant]['volumes'][part - 1]
            if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact'] or
                    not r['ay_records_exact'] or not r['progress_100_percent'] or
                    r['debugger_installed_bytes'] or r['fast_read_retries'] or
                    r['frames'] != m['frames'] or r['ay_ticks'] != 6 * m['frames'] or
                    r['runtime_sectors_checked'] != m['video_sectors'] or
                    r['trd_sha256'] != m['trd_sha256'] or r['trd_sha256'] != c['trd_sha256'] or
                    sha(meta) != r['integrated_bootstrap_metadata_sha256'] or
                    sha(raw) != c['trace_report_sha256'] or not m['independently_bootable'] or
                    r['native_frames_sampled'] != m['frames'] or r['pixel_samples_per_frame'] != 80):
                raise ValueError(('incomplete/different evidence', variant, part))
            for suffix, key in (('.trace.txt', 'trace_sha256'), ('.debugger.txt', 'debugger_script_sha256')):
                if sha(blob(stem + suffix + '.gz')) != r[key]:
                    raise ValueError('raw trace mismatch')
            if any(s.startswith('se ') and s[3:].split(' ', 1)[0].isdigit()
                   for s in blob(stem + '.debugger.txt.gz').decode().splitlines()):
                raise ValueError('debugger writes RAM')
            if len(r['queue_call_events']) != 2 * len(c['calls']):
                raise ValueError('queue call count differs')
            for call, before, after in zip(c['calls'], r['queue_call_events'][::2], r['queue_call_events'][1::2]):
                if (call['start'] != before['tstate'] or call['end'] != after['tstate'] or
                        sum(call['cpu_stages'].values()) != call['cpu_tstates']):
                    raise ValueError('CPU call differs')
            reference = copy.deepcopy(frame_cpu['volumes'][part - 1])
            for frame in reference['frames']:
                frame['tstates'] -= 499  # Identical verified HL metadata reader in both players.
            irq = audit(r, m)
            irq.pop('actual_phase_tstates')
            profile = analyze(r, m, reference)
            first_empty = min(r['audio_underrun_tstates'], default=None)
            starvation = None
            if first_empty is not None:
                stages = [dict(frame=f['local_frame'], stage=stage, **span)
                          for f in profile['frames'] for stage, span in f['stages'].items()
                          if span['start'] <= first_empty < span['end']]
                calls = [call for call in c['calls'] if call['start'] <= first_empty < call['end']]
                if len(stages) > 1 or len(calls) > 1:
                    raise ValueError('overlapping foreground intervals')
                starvation = dict(tstate=first_empty, stage=stages[0] if stages else None,
                    queue_call=calls[0] if calls else None,
                    earlier_full_waits=sum(e['kind'] == 'enqueue_full' and e['tstate'] < first_empty
                                           for e in r['audio_enqueue_events']))
            worst = sorted(profile.pop('frames'), key=lambda v: v['work_elapsed'], reverse=True)[:12]
            row[variant] = dict(metrics(r), irq=irq, rom=rom_invariants(r, True),
                used_sectors=m['used_sectors'], video_start_sector=m['video_start_sector'],
                ay_record_field_gaps=r['ay_record_field_gaps'],
                ay_record_field_duplicates=r['ay_record_field_duplicates'],
                actual_late_indices=[i for i, t in enumerate(r['actual_phase_tstates']) if t > 64],
                trd_sha256=m['trd_sha256'], stream_sha256=c['stream_sha256'],
                rom_sha256=r['rom_sha256'], first_actual_late_window=first_late_window(r, actual=True),
                first_starvation=starvation,
                audio_wait=audio_analysis(r, c), queue_cpu_stages=c['cpu_stages'], queue_calls=len(c['calls']),
                delivery_profile=profile, worst_work_frames=worst,
                read_service=stats([v['tstates'] for v in r['reads']]),
                seek_service=stats([v['tstates'] for v in r['seek_calls']]))
            if variant == 'streaming':
                b = build['volumes'][part - 1]
                if (m['trd_sha256'] != b['trd_sha256'] or not b['dirty_ram_boot_exact'] or
                        not b['compressed_stream_exact'] or not m['streaming_input']['enabled'] or
                        not c['input_history_frontiers_guarded'] or c['checked_copy_bytes'] <= 0):
                    raise ValueError('streaming build/replay differs')
                row[variant].update(active_prefix_bytes=c['active_prefix_bytes'],
                    phase3_prefix_bytes=c['phase3_prefix_bytes'], pending_eof_finishes=c['pending_eof_finishes'])
        if row['hl']['stream_sha256'] != row['streaming']['stream_sha256']:
            raise ValueError('compressed stream changed')
        for key, value in baseline['volumes'][part - 1]['hl'].items():
            # JSON object keys are strings; live Counter keys may be integers.
            if key in row['hl'] and value != json.loads(json.dumps(row['hl'][key])):
                raise ValueError(('baseline analysis changed', key))
        volumes.append(row)
    keys = ('frames', 'nominal_late_frames', 'audio_underruns', 'ay_ticks', 'runtime_sectors',
            'publication_span_tstates', 'bad_actual_intervals')
    totals = {v: {key: sum(r[v][key] for r in volumes) for key in keys} for v in ('hl', 'streaming')}
    for v in totals:
        totals[v].update(actual_late_frames=sum(len(r[v]['actual_late_indices']) for r in volumes),
            missing_irq_fields=sum(len(r[v]['irq']['missing_irq_fields']) for r in volumes),
            queue_and_ay_wait_cpu=sum(r[v]['audio_wait']['queue_and_full_wait_cpu'] for r in volumes))
    sources = ('summarize_streaming_player.py', 'replay_streaming_queue.py', 'verify_streaming_player.py',
               'measure_fap3_fuse.py', 'measure_integrated_bootstrap.py', 'audit_irq_fields.py',
               'summarize_uncontended_frame.py', 'summarize_transfer_prefetch.py',
               'summarize_fast_return_irq.py', 'profile_integrated_timing.py', 'inline_huffman_patches_cpu.json')
    report = dict(complete=True, release=False, scope=__doc__, baseline_code_commit='074e1e7',
        task_base_commit='f962cac', evidence=files, build_sha256=sha(build_path.read_bytes()),
        core_cpu_sha256=sha(core_path.read_bytes()), baseline_summary_sha256=sha(baseline_path.read_bytes()),
        source_sha256={f: sha((ROOT / f).read_bytes()) for f in sources}, volumes=volumes, totals=totals,
        frame_cpu_reference_note='Previous reconstruction/render CPU with verified -499 T/frame HL metadata delta; frame renderer not re-executed in queue replay.',
        deterministic_timing_excludes=['IRQ', 'ULA', 'ROM', 'physical disk latency'],
        capacity_met=all(r['streaming']['used_sectors'] <= 2544 for r in volumes),
        compressed_streams_exact=True, phases_matched=False, video_sector_layout_unchanged=False,
        full_pixel_comparison=False, pixel_samples_per_frame=80, physical_drive_verified=False,
        other_video_verified=False, nominal_schedule_met=totals['streaming']['actual_late_frames'] == 0,
        fallback_met=all(r['streaming']['max_actual_deviation_tstates'] <= 70908 + 64 and
                         not r['streaming']['bad_actual_intervals'] for r in volumes),
        ay_continuity_met=totals['streaming']['audio_underruns'] == 0 and
            totals['streaming']['missing_irq_fields'] == 0 and
            all(not r['streaming']['ay_record_field_gaps'] and not r['streaming']['ay_record_field_duplicates'] for r in volumes))
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(totals, indent=2), flush=True)


if __name__ == '__main__':
    main()
