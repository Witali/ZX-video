"""Compare decoder work on the exact same blocks and frame boundaries.

Z80 T-states from UM0080; no disk, paging, contention, IRQs or frame drawing.
The old scope is turbo entry through RET. The new scope includes coroutine
entry/return, target synchronization and all suspensions at frame boundaries.
"""
import argparse
import hashlib
import json
from pathlib import Path

import build_fast_sparse_trd as codec
import zx0_codec
from validate_fast_sparse import CPU


def run(cpu,entry):
    cpu.pc=entry;cpu.push(0x5F00);start=cpu.tstates;steps=cpu.steps
    while cpu.pc!=0x5F00:
        if cpu.steps-steps>2_000_000:raise AssertionError('decoder did not return')
        cpu.step()
    return cpu.tstates-start


def benchmark(build):
    meta=json.loads((build/'build_metadata.json').read_text())
    blocks=[b for v in meta['volumes'] for b in v['blocks']]
    assembler=codec.base.MiniAssembler(0x6000);zx0_codec.emit_decoder(assembler,'turbo')
    original=assembler.resolve()
    player,labels=codec.build_player(0,0,blocked=True,incremental=True)
    old_counts=[];new_counts=[];frames=[];slices=[]
    for index,block in enumerate(blocks):
        stem=build/'compression_cache'/block['sha256']
        expected=stem.with_suffix('.raw').read_bytes()
        assert hashlib.sha256(expected).hexdigest()==block['sha256']
        payload=expected if block['stored'] else stem.with_suffix('.zx0').read_bytes()
        old=CPU(original,b'');old.set_hl(0xA000);old.set_de(0x8000)
        new=CPU(player,b'');new.sp=0x5FF0
        for cpu in (old,new):
            for i,value in enumerate(payload):cpu.write8(0xA000+i,value)
        if block['stored']:
            old_t=21*len(expected)-5  # Original stored-block LDIR.
        else:
            old_t=run(old,0x6000)
            assert bytes(old.banks[2][:len(expected)])==expected
        def word(name,value):
            new.write8(labels[name],value);new.write8(labels[name]+1,value>>8)
        word('block_end',0x8000+len(expected));word('block_length',len(expected))
        new.write8(labels['block_stored'],128 if block['stored'] else 0)
        pos=0;block_t=0
        while pos<len(expected):
            length=int.from_bytes(expected[pos:pos+2],'little')+2
            frame_t=0
            for target in (pos+2,pos+length):
                word('slice_target',0x8000+target)
                cycles=run(new,labels['slice_begin' if target==2 else 'slice_until'])
                slices.append(cycles);frame_t+=cycles
                assert bytes(new.banks[2][:target])==expected[:target]
            frames.append(frame_t);block_t+=frame_t;pos+=length
        assert pos==len(expected)
        old_counts.append(old_t);new_counts.append(block_t)
        if index%20==0:print(f'verified block {index+1}/{len(blocks)}',flush=True)
    return dict(scope=__doc__,timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
                blocks=len(blocks),frames=len(frames),old_block_tstates=old_counts,
                incremental_block_tstates=new_counts,incremental_frame_tstates=frames,
                old_block_mean=sum(old_counts)/len(old_counts),old_block_max=max(old_counts),
                incremental_block_mean=sum(new_counts)/len(new_counts),
                incremental_frame_mean=sum(frames)/len(frames),incremental_frame_max=max(frames),
                incremental_slice_max=max(slices),total_delta=sum(new_counts)-sum(old_counts))


def main():
    p=argparse.ArgumentParser();p.add_argument('build',type=Path);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();report=benchmark(args.build)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if not isinstance(v,list)},indent=2))


if __name__=='__main__':main()
