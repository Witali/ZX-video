"""Measure the fixed AY forest ceiling and potential unused payload-bank space."""
import argparse
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent;ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'toolkit'))
import ay_interrupt
import ay_huffman_stream as wire
import build_long_video_trd as video


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('prepared', type=Path);p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    core = args.prepared/'work/ay-core'
    saved = json.loads((core/'analysis.json').read_bytes());width = saved['packed_state_bytes']
    raw = (core/'ay.bin').read_bytes()
    frames = [video.AyFrame.deserialize(raw[i:i+width]) for i in range(0, len(raw), width)]
    ticks = ay_interrupt.encode_ticks(frames)
    contexts = [set() for _ in range(16)];rows = []
    for at, tick in enumerate(ticks):
        mask = sum(1 << v for v in tick[1::2]);contexts[0].add(mask & 255);contexts[1].add(mask >> 8)
        for reg, value in zip(tick[1::2], tick[2::2]):contexts[reg+2].add(value)
        if at%5 == 4:
            nodes = sum(max(0, len(c)-1) for c in contexts)
            rows.append(dict(frames=(at+1)//5, forest_nodes=nodes, fixed_forest_fits=nodes <= 1045))
    maximum = max(row['frames'] for row in rows if row['fixed_forest_fits'])
    _, coded = wire.encode(ticks[:maximum*5], bytes(14))
    _, full = wire.encode(ticks[:len(rows)*5], bytes(14))
    report = dict(complete=True, source_frames=len(rows), fixed_node_capacity=1045,
        maximum_fixed_forest_prefix_frames=maximum, seconds=maximum/10,
        prefix_payload_bytes=coded['payload_bytes'], full_payload_bytes=full['payload_bytes'],
        full_forest_nodes=rows[-1]['forest_nodes'], rows=rows,
        scope='Exact host AY ceiling only; disk bytes and native playback are separate gates.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'rows'}))


if __name__ == '__main__':main()
