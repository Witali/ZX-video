"""Assemble and cold-boot the selected lossless ZX0 block phases.

Preserves all baseline bootstrap options, checks a byte-exact baseline
rebuild, and assigns one identity to the three standalone experimental TRDs.
The queued/compiled-mask runtime is installed separately by the Fuse fixture;
its release bootstrap size is not verified by this storage measurement.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha
import fap3_disk_z80 as disk
from measure_volume_huffman import identify
from probe_startup_tables import undifference
from test_fap3_disk import DiskCPU, verify_swaps
from test_warm_continuation import player, until
from zx0_block_phase import Builder
from zx0_codec import decompress


OPTIONS = ('fast_disk', 'cached_seek', 'interleaved', 'cold_bitmaps',
           'startup_delta', 'inline_matches', 'fast_noop_scan',
           'irq_safe_paging', 'static_cache_borders', 'carry_huffman',
           'register_fragments', 'deferred_limit', 'keepalive_fields',
           'frame_service')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('probe', 'raw-directory', 'directory', 'states', 'zx0', 'output', 'report'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--read-cache', type=Path, action='append', default=[])
    args = p.parse_args()
    probe = json.loads(args.probe.read_bytes())
    if not probe['complete'] or [v['part'] for v in probe['volumes']] != [1, 2, 3]:
        raise ValueError('requires the completed three-volume storage probe')
    with np.load(args.states, allow_pickle=False) as f:
        states = f['states']
    if sha(states.tobytes()) != probe['states_sha256'] or sha(args.zx0.read_bytes()) != probe['compressor_sha256']:
        raise ValueError('different states or compressor')
    ends = [v['end'] for v in probe['volumes']]
    if [v['start'] for v in probe['volumes']] != [0] + ends[:-1] or ends[-1] != len(states):
        raise ValueError('incomplete movie partition')
    metas = [disk_blocks(args.directory, i)[0] for i in (1, 2, 3)]
    options = [{k: m[k] for k in OPTIONS} for m in metas]
    contract = dict(version='standalone-zx0-block-phase-1',
        raw_sha256=[v['raw_sha256'] for v in probe['volumes']],
        states_sha256=probe['states_sha256'], ends=ends, options=options,
        phases=[v['selected_phase'] for v in probe['volumes']])
    contract_sha = sha(json.dumps(contract, sort_keys=True).encode())
    fingerprint = b'FAP3ZXV1' + bytes.fromhex(contract_sha)[:6]
    args.output.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    result = dict(complete=False, release=False, scope=__doc__,
        probe_sha256=sha(args.probe.read_bytes()), contract=contract,
        contract_sha256=contract_sha, new_queue_bootstrap_capacity_verified=False,
        physical_drive_verified=False, full_playback_verified=False, volumes=[])
    def save():
        args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    records = []
    save()
    for v, meta, opts in zip(probe['volumes'], metas, options, strict=True):
        part, start, end = v['part'], v['start'], v['end']
        if (meta['frame_start'], meta['frame_end_exclusive']) != (start, end):
            raise ValueError('baseline partition differs')
        raw = (args.raw_directory / f'volume-{part}.raw').read_bytes()
        if sha(raw) != v['raw_sha256']:
            raise ValueError('different raw source')
        b = Builder(raw, states, args.zx0.resolve(), args.output / 'zx0', **opts)
        b.read_cache = args.read_cache
        b.ends = ends
        baseline, old = b.volume(start, end, part)
        if baseline is None:
            raise AssertionError('baseline does not fit')
        baseline = identify(baseline, old, bytes.fromhex(meta['disk_id_hex'])[:14])
        original = (args.directory / f'ZX-video-huffman-preview_part{part:02}.trd').read_bytes()
        if baseline != original:
            raise AssertionError('baseline rebuild is not byte exact')
        b.block_phase = v['selected_phase']
        image, m = b.volume(start, end, part)
        if image is None or not m['independently_bootable']:
            raise ValueError('selected volume is overfull or not independently bootable')
        image = identify(image, m, fingerprint)
        m['zx0_phase_contract_sha256'] = contract_sha
        trd = args.output / f'ZX-video-huffman-preview_part{part:02}.trd'
        trd.write_bytes(image)
        trd.with_suffix('.json').write_text(json.dumps(m, indent=2) + '\n', encoding='utf-8', newline='\n')
        _, stream, blocks = disk_blocks(args.output, part)
        chosen = next(r for r in v['variants'] if r['phase'] == v['selected_phase'])
        if sha(stream) != chosen['stream_sha256'] or sha(b''.join(r for _, r in blocks)) != v['packet_sha256']:
            raise AssertionError('assembled stream or packet content differs')
        cpu = DiskCPU(player(image), image)
        until(cpu, disk.DRIVER)
        section = next(s for s in m['sections'] if s['bank'] == 6)
        at = section['sector'] * 256
        table = decompress(image[at:at + section['compressed_bytes']], limit=16384)
        if section.get('startup_delta'):
            table = undifference(table)
        if sha(table) != section['sha256'] or bytes(cpu.banks[6]) != table:
            raise AssertionError('cold table restoration differs')
        row = dict(part=part, start=start, end=end, phase=b.block_phase,
            baseline_trd_sha256=sha(original), trd_sha256=sha(image),
            baseline_rebuild_byte_exact=True, packet_sha256=v['packet_sha256'],
            stream_sha256=sha(stream), independently_bootable=True,
            cold_table_all_bytes_exact=True, boot_mocked_tstates=cpu.tstates,
            baseline_used_sectors=meta['used_sectors'],
            **{k: m[k] for k in ('used_sectors', 'free_sectors', 'video_bytes',
                'video_sectors', 'video_start_sector', 'video_physical_sectors', 'layout_padding_sectors')})
        result['volumes'].append(row)
        records.append(dict(part=part, file=trd.name, metadata=trd.with_suffix('.json').name,
            frame_start=start, frame_end_exclusive=end, sha256=sha(image)))
        save()
        print(json.dumps(row), flush=True)
    (args.output / 'volumes.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8', newline='\n')
    swaps = args.output / 'swaps.json'
    verify_swaps(args.output, swaps)
    result.update(complete=True, mocked_rom_swaps=json.loads(swaps.read_bytes()))
    save()


if __name__ == '__main__':
    main()
