"""Check the saved block-phase evidence, coverage, timings and content hashes."""
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from summarize_uncontended_frame import metrics
from summarize_zx0_block_phase import compare_cpu


def main():
    root = Path(__file__).parent
    def read(name):
        return json.loads((root / name).read_bytes())
    summary = read('zx0_block_phase_summary.json')
    paths = dict(probe='zx0_block_phase_probe.json', build='zx0_block_phase_build.json',
                 cpu='zx0_block_phase_cpu.json', baseline_cpu='slot_queue_cpu.json')
    data = {k: read(v) for k, v in paths.items()}
    if not summary['complete'] or not all(r['complete'] for r in data.values()):
        raise AssertionError('incomplete evidence')
    for key, path in paths.items():
        if sha((root / path).read_bytes()) != summary['input_sha256'][key]:
            raise AssertionError(('input hash', key))
    if data['build']['probe_sha256'] != summary['input_sha256']['probe']:
        raise AssertionError('build input hash')
    for row in summary['evidence']:
        blob = (root / 'zx0_block_phase_evidence' / row['file']).read_bytes()
        if sha(blob) != row['sha256']:
            raise AssertionError(('evidence hash', row['file']))
        if 'uncompressed_sha256' in row and sha(gzip.decompress(blob)) != row['uncompressed_sha256']:
            raise AssertionError(('trace hash', row['file']))
    next_frame = 0
    for part in (1, 2, 3):
        v, b, cpu, old_cpu = (data[k]['volumes'][part-1] for k in ('probe', 'build', 'cpu', 'baseline_cpu'))
        saved = summary['volumes'][part-1]
        if v['part'] != part or v['start'] != next_frame or saved['start'] != v['start'] or saved['end'] != v['end']:
            raise AssertionError('frame coverage')
        next_frame = v['end']
        chosen = min(v['variants'], key=lambda r: (r['stream_bytes'], len(r['blocks']), r['phase']))
        if chosen['phase'] != v['selected_phase'] or chosen['phase'] != b['phase']:
            raise AssertionError('selection differs')
        for row in v['variants']:
            blocks = row['blocks']
            if (not row['all_zx0_blocks_exact'] or not row['packet_bytes_unchanged']
                    or sum(r['decoded_bytes'] for r in blocks) != v['packet_bytes']
                    or sum(r['zx0_bytes']+4 for r in blocks) != row['stream_bytes']
                    or row['delta_bytes'] != row['stream_bytes']-v['baseline_stream_bytes']
                    or row['sectors'] != (row['stream_bytes']+255)//256):
                raise AssertionError('storage totals')
            if any(not 1 <= r['decoded_bytes'] <= 8192 or not 1 <= r['zx0_bytes'] <= 8192 for r in blocks):
                raise AssertionError('block size')
            if any(a['raw_start']+a['decoded_bytes'] != z['raw_start'] for a, z in zip(blocks, blocks[1:])):
                raise AssertionError('block gap')
            if row['phase'] == 0 and row['stream_sha256'] != v['baseline_stream_sha256']:
                raise AssertionError('baseline ZX0 differs')
        if (b['video_bytes'] != chosen['stream_bytes'] or b['stream_sha256'] != chosen['stream_sha256']
                or b['packet_sha256'] != v['packet_sha256'] or not b['baseline_rebuild_byte_exact']
                or not b['cold_table_all_bytes_exact'] or not b['independently_bootable']
                or b['used_sectors']+b['free_sectors'] != 2544 or b['free_sectors'] < 0):
            raise AssertionError('build coverage or capacity')
        if compare_cpu(old_cpu, cpu, v, b) != saved['queue_cpu']:
            raise AssertionError('CPU comparison')
        for row in (cpu, old_cpu):
            if sum(r['tstates']*r['count'] for r in row['instruction_histogram']) != row['summary']['queue_total_tstates']:
                raise AssertionError('CPU histogram')
        baseline_path = root / f'compiled_masks_evidence/part{part:02}.json'
        new = read(f'zx0_block_phase_evidence/part{part:02}.json')
        old = json.loads(baseline_path.read_bytes())
        if sha(baseline_path.read_bytes()) != saved['baseline_report_sha256']:
            raise AssertionError('baseline Fuse hash')
        if (not new['complete'] or not new['trace_nonce_exact'] or new['errors'] or not new['ay_records_exact']
                or new['frames'] != v['end']-v['start'] or new['trd_sha256'] != b['trd_sha256']
                or new['runtime_sectors_checked'] != b['video_sectors']
                or new['ay_ticks'] != 6*new['frames'] or not new['compiled_masks']
                or metrics(new) != saved['reblocked'] or metrics(old) != saved['baseline']):
            raise AssertionError('Fuse input, coverage or timing')
        for suffix, key in (('trace.txt', 'trace_sha256'), ('debugger.txt', 'debugger_script_sha256')):
            blob = gzip.decompress((root / f'zx0_block_phase_evidence/part{part:02}.{suffix}.gz').read_bytes())
            if sha(blob) != new[key]:
                raise AssertionError('Fuse trace source')
    if next_frame != data['probe']['frames'] or len(data['build']['mocked_rom_swaps']) != 2:
        raise AssertionError('incomplete movie or disk changes')
    for row in data['build']['mocked_rom_swaps']:
        if not all(row[k] for k in ('prompt_exact', 'wrong_disk_rejected', 'wrong_series_rejected',
                                    'correct_disk_accepted', 'bootstrap_ram_exact')):
            raise AssertionError('disk change failure')
    for name, totals in summary['totals'].items():
        for key, value in totals.items():
            if value != sum(v[name][key] for v in summary['volumes']):
                raise AssertionError(('summary sum', name, key))
    print(f'Verified: {next_frame} exact packets, three complete Fuse runs, storage, CPU and evidence hashes.')


if __name__ == '__main__':
    main()
