"""Reassemble PLAYER while preserving every byte outside its existing file.

The baseline hash is required explicitly. The new PLAYER must retain its
size, sector allocation and VIDEO file start. Every resulting byte outside
PLAYER is checked against the baseline.
"""
import argparse
import hashlib
import json
from pathlib import Path

import build_fast_sparse_trd as codec
from validate_streaming_player import extract_file, parse_dir


def sha(data):
    return hashlib.sha256(data).hexdigest()


def options(meta):
    return dict(packed=meta['packing'] != 'sector', blocked=meta['packing'] == 'zx0',
                clocked=meta['pacing'] != 'legacy', deadline=meta['pacing'] == 'deadline',
                read_batch=meta['read_batch'], fast_draw=meta['drawing'] == 'registers',
                fast_disk=meta['disk_reader'] != 'trdos', irq_disk=meta['disk_reader'] == 'trdos503-irq',
                interleaved=meta['disk_layout'] == 'interleaved',
                incremental=meta['zx0_decoding'] == 'incremental',
                keepalive_fields=meta['motor_keepalive_fields'], prefetch_quota=meta['prefetch_quota'],
                full_rom_clock=meta['rom_clock'] == 'full', cached_seek=meta['disk_seek'] == 'cached',
                lookahead=meta['packet_lookahead'], uncontended=meta['uncontended'],
                read_reserve=meta['read_reserve'], memory_clock=meta['memory_clock'],
                direct_input=meta['direct_input'], wrapped_input=meta['wrapped_input'],
                ay_noise=meta.get('ay_noise', False), audio_irq=meta.get('audio_irq', False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--expected-player-sha256', required=True)
    args = p.parse_args()
    meta = json.loads((args.build / 'build_metadata.json').read_text())
    before = (args.build / 'PLAYER.C.bin').read_bytes()
    settings = options(meta)
    if sha(before) != args.expected_player_sha256:
        raise ValueError('saved PLAYER does not match the expected baseline hash')
    after, labels = codec.build_player(meta['video_track'], meta['video_sector'], **settings)
    if len(after) != len(before):
        raise ValueError('PLAYER size changed; rebuild the disk allocation')
    args.output.mkdir(parents=True, exist_ok=True)
    evidence = []
    for volume in meta['volumes']:
        original = (args.build / volume['trd_name']).read_bytes()
        entry = next(item for item in parse_dir(original) if item[0] == 'PLAYER')
        assert extract_file(original, entry) == before
        start = (entry[3] * 16 + entry[4]) * 256
        image = original[:start] + after + original[start + len(before):]
        assert extract_file(image, entry) == after
        assert image[:start] == original[:start] and image[start + len(after):] == original[start + len(before):]
        (args.output / volume['trd_name']).write_bytes(image)
        evidence.append(dict(file=volume['trd_name'], previous_sha256=sha(original), sha256=sha(image)))
    meta['player_labels'] = labels
    meta['drawing_cycle_reference'] = 'SMOOTH_CADENCE_RESULTS_ru.md'
    meta['attributes_delta_tstates'] = dict(previous='95+251*N+40*W',
        current='112+86*N+55*W-C (N>0); 91 (N=0)',
        scope='command entry through JP command_loop; dispatch, IRQ and contention excluded',
        symbols='N: attributes; W: extended gaps; C: carry from low-byte gap addition')
    meta['player_rebuild'] = dict(previous_player_sha256=sha(before), player_sha256=sha(after),
                                  player_bytes=len(after), non_player_bytes_unchanged=True, disks=evidence)
    (args.output / 'PLAYER.C.bin').write_bytes(after)
    (args.output / 'build_metadata.json').write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in meta['player_rebuild'].items() if key != 'disks'}, indent=2))


if __name__ == '__main__':
    main()
