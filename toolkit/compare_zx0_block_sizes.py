"""Check complete ZX0 storage/CPU reports for two block sizes on one stream.

Only storage and isolated decoder execution are compared. No claim about
ring capacity, sector delivery, integrated memory placement or playback.
"""
import argparse
import json
from pathlib import Path

from probe_lossless_layouts import sha


def summarize(raw, storage_path, cpu_path):
    storage = json.loads(storage_path.read_text(encoding='utf-8'))
    cpu = json.loads(cpu_path.read_text(encoding='utf-8'))
    if (not storage['complete'] or not cpu['complete']
            or cpu['input_sha256'] != sha(raw) or storage['input_sha256'] != sha(raw)
            or len(storage['blocks']) != storage['blocks_expected']
            or len(cpu['blocks']) != len(storage['blocks'])
            or storage['encoder_mode'] != 'optimal ZX0 v2'):
        raise ValueError('different/incomplete input')
    position = size = ticks = 0
    for i, (block, measured) in enumerate(zip(storage['blocks'], cpu['blocks'])):
        chunk = raw[position:position+block['decoded_bytes']]
        position += len(chunk)
        if (len(chunk) != block['decoded_bytes'] or sha(chunk) != block['sha256']
                or measured['index'] != i or measured['raw_sha256'] != block['sha256']
                or measured['raw_bytes'] != len(chunk) or measured['compressed_bytes'] != block['zx0_bytes']):
            raise AssertionError('block coverage differs')
        size += block['zx0_bytes']+4; ticks += measured['tstates']
    if (position != len(raw) or size != storage['zx0_with_headers_bytes']
            or ticks != cpu['summary']['total_tstates']):
        raise AssertionError('full stream totals differ')
    return dict(block_bytes=storage['block_bytes'], blocks=len(storage['blocks']),
        video_bytes_with_headers=size, video_plus_ay_estimate_bytes=size+77696,
        preliminary_three_trd_margin_bytes=1937664-size-77696,
        densely_packed_video_sectors=(size+255)//256, total_tstates=ticks,
        max_block_tstates=cpu['summary']['max_block_tstates'], benchmark_layout=cpu['benchmark_layout'],
        decoder_bytes=cpu['decoder_bytes'], decoder_sha256=cpu['decoder_sha256'],
        encoder_sha256=storage['encoder_sha256'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--storage', type=Path, nargs=2, required=True)
    p.add_argument('--cpu', type=Path, nargs=2, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    raw = args.raw.read_bytes()
    old, new = [summarize(raw, s, c) for s, c in zip(args.storage, args.cpu)]
    if old['decoder_sha256'] != new['decoder_sha256'] or old['encoder_sha256'] != new['encoder_sha256']:
        raise ValueError('different codec implementations')
    report = dict(scope=__doc__, baseline_commit='7dea054', complete=True, input_sha256=sha(raw),
        raw_bytes=len(raw), before=old, after=new,
        delta={key: new[key]-old[key] for key in ('video_bytes_with_headers', 'densely_packed_video_sectors',
            'total_tstates', 'max_block_tstates', 'decoder_bytes')},
        decoder_implementation_changed=False, player_changed=False, integrated_player_delta_tstates=0,
        smaller_disk_buffer_accepted=False, physical_disk_latency_measured=False)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
