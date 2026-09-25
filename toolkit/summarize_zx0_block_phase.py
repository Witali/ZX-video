"""Archive storage, exact queue CPU, and complete Fuse block-phase evidence.

Compare the same queue and compiled-mask player on differently blocked ZX0
streams. CPU sums exclude ROM/physical disk, IRQ and ULA; Fuse spans include
them. No changed pixels or AY bytes are admitted by the packet hash checks.
"""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from summarize_uncontended_frame import metrics


def compare_cpu(old, new, expected, layout):
    for row, digest, stream in ((old, layout['baseline_trd_sha256'], expected['baseline_stream_sha256']),
                                (new, layout['trd_sha256'], layout['stream_sha256'])):
        if (row['trd_sha256'] != digest or row['stream_sha256'] != stream
                or row['raw_sha256'] != expected['packet_sha256']
                or [f['index'] for f in row['frames']] != list(range(expected['start'], expected['end']))):
            raise AssertionError('CPU input or frame coverage differs')
        total = sum(f['queue_fill_tstates'] + f['queue_take_tstates'] for f in row['frames'])
        if (total != row['summary']['queue_total_tstates']
                or total != sum(row['summary']['stages'].values())
                or row['summary']['raw_bytes'] != expected['packet_bytes']):
            raise AssertionError('CPU totals differ')
    before, after = old['summary']['queue_total_tstates'], new['summary']['queue_total_tstates']
    return dict(baseline_tstates=before, phase_tstates=after, delta_tstates=after-before,
        baseline_stages=old['summary']['stages'], phase_stages=new['summary']['stages'],
        baseline_blocks=old['summary']['blocks'], phase_blocks=new['summary']['blocks'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('probe', 'build', 'cpu', 'fuse', 'evidence', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--baseline-cpu', type=Path, default=Path('toolkit/slot_queue_cpu.json'))
    p.add_argument('--baseline-fuse', type=Path, default=Path('toolkit/compiled_masks_evidence'))
    args = p.parse_args()
    inputs = {k: json.loads(getattr(args, k).read_bytes()) for k in ('probe', 'build', 'cpu', 'baseline_cpu')}
    if not all(x['complete'] and len(x['volumes']) == 3 for x in inputs.values()):
        raise ValueError('requires complete three-volume input evidence')
    if inputs['build']['probe_sha256'] != sha(args.probe.read_bytes()):
        raise ValueError('build used another probe')
    args.evidence.mkdir(parents=True, exist_ok=True)
    files, volumes = [], []
    for part in (1, 2, 3):
        v, b, cpu, old_cpu = (inputs[k]['volumes'][part-1] for k in ('probe', 'build', 'cpu', 'baseline_cpu'))
        cost = compare_cpu(old_cpu, cpu, v, b)
        path = args.fuse / f'part{part:02}.json'
        old_path = args.baseline_fuse / path.name
        old, new = (json.loads(f.read_bytes()) for f in (old_path, path))
        for r, digest, sectors in ((old, b['baseline_trd_sha256'], old_cpu['summary']['sectors']),
                                   (new, b['trd_sha256'], b['video_sectors'])):
            if (not r['complete'] or not r['trace_nonce_exact'] or r['errors'] or not r['ay_records_exact']
                    or r['frames'] != v['end']-v['start'] or r['ay_ticks'] != 6*r['frames']
                    or r['trd_sha256'] != digest or r['runtime_sectors_checked'] != sectors
                    or not r.get('compiled_masks') or r.get('uncontended_frame') or not r.get('slot_queue_fixture')):
                raise ValueError('different runtime variant or incomplete Fuse verification')
        dest = args.evidence / path.name
        dest.write_text(json.dumps(new, indent=2) + '\n', encoding='utf-8', newline='\n')
        files.append(dict(file=dest.name, sha256=sha(dest.read_bytes())))
        for suffix, key in (('.trace.txt', 'trace_sha256'), ('.debugger.txt', 'debugger_script_sha256')):
            blob = path.with_suffix(suffix).read_bytes()
            if sha(blob) != new[key]:
                raise ValueError('trace hash differs')
            dest = args.evidence / (path.stem + suffix + '.gz')
            dest.write_bytes(gzip.compress(blob, mtime=0))
            files.append(dict(file=dest.name, sha256=sha(dest.read_bytes()), uncompressed_sha256=sha(blob)))
        volumes.append(dict(part=part, start=v['start'], end=v['end'], phase=b['phase'],
            trd_sha256=b['trd_sha256'], packet_sha256=v['packet_sha256'],
            baseline_report_sha256=sha(old_path.read_bytes()),
            storage={k: b[k] for k in ('baseline_used_sectors', 'used_sectors', 'free_sectors',
                                      'video_bytes', 'video_sectors', 'layout_padding_sectors')},
            baseline=metrics(old), reblocked=metrics(new), queue_cpu=cost))
    if [v['start'] for v in volumes] != [0]+[v['end'] for v in volumes[:-1]] or volumes[-1]['end'] != inputs['probe']['frames']:
        raise AssertionError('missing movie frames')
    totals = {name: {key: sum(v[name][key] for v in volumes) for key in
        ('frames', 'nominal_late_frames', 'audio_underruns', 'ay_ticks', 'runtime_sectors',
         'read_service_tstates', 'seek_service_tstates', 'publication_span_tstates')}
        for name in ('baseline', 'reblocked')}
    totals['queue_cpu'] = {k: sum(v['queue_cpu'][k] for v in volumes)
                          for k in ('baseline_tstates', 'phase_tstates', 'delta_tstates')}
    totals['storage'] = {k: sum(v['storage'][k] for v in volumes)
                        for k in ('baseline_used_sectors', 'used_sectors', 'free_sectors', 'video_bytes', 'video_sectors')}
    nominal = all(v['reblocked']['nominal_late_frames'] == 0 and v['reblocked']['max_actual_deviation_tstates'] <= 64 for v in volumes)
    fallback = all(v['reblocked']['actual_out_over_one_field'] == 0 and v['reblocked']['bad_actual_intervals'] == 0 for v in volumes)
    result = dict(complete=True, release=False, scope=__doc__, baseline_commit='94c2e6f',
        selection=inputs['build'].get('selection', 'minimum'),
        input_files={k: getattr(args, k).name for k in inputs},
        evidence_directory=args.evidence.name, baseline_directory=args.baseline_fuse.name,
        input_sha256={k: sha(getattr(args, k).read_bytes()) for k in inputs},
        source_packets_unchanged=True, every_packet_byte_compared_in_cpu=True,
        fuse_samples_per_frame=80, full_fuse_pixel_comparison=False, physical_drive_verified=False,
        new_queue_bootstrap_capacity_verified=False, initial_disk_and_irq_phases_not_matched=True,
        timing_note='End-to-end effects include initial phases and rotations, not solely CPU costs.',
        nominal_schedule_met=nominal, fallback_met=fallback, volumes=volumes, totals=totals, evidence=files)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(totals), flush=True)


if __name__ == '__main__':
    main()
