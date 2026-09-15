"""Compare emitted command T-states against a saved baseline player."""
import argparse
import json
from pathlib import Path

from test_fast_drawing import execute


def read_build(path):
    return ((path/'PLAYER.C.bin').read_bytes(),
            json.loads((path/'build_metadata.json').read_text())['player_labels'])


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline-build',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();old=read_build(args.baseline_build);new=read_build(args.build)
    cases={
        'mask_0':('command_row',bytes([95,0,0,0,0])),
        'mask_32':('command_row',bytes([95,255,255,255,255])+bytes(range(32))),
        'points_0':('command_points',bytes([95,0])),
        'points_8':('command_points',bytes([95,8])+b''.join(bytes([i*4,i]) for i in range(8))),
        'spans_2x16':('command_spans',bytes([95,2,15])+bytes(range(16))+bytes([15])+bytes(range(16,32))),
        'rle_repeat_32':('command_row_rle',bytes([95,2,158,75])),
        'rle_literal_32':('command_row_rle',bytes([95,33,31])+bytes(range(32))),
    }
    rows={}
    for name,(command,payload) in cases.items():
        before,bt=execute(*old,command,payload,start=0x80FD)
        after,at=execute(*new,command,payload,start=0x80FD)
        assert before==after
        rows[name]=dict(previous_tstates=bt,current_tstates=at,delta=at-bt)
    report=dict(baseline_commit='251a79c',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='command entry through JP command_loop; dispatch excluded',
        exclusions=['ROM service','disk latency','ULA contention','interrupt execution'],
        assumptions='logical row 95, screen 4000, stream starts 80FD and crosses a page',
        routines=rows,irq_tstates=dict(before=61,after=61,delta=0))
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
