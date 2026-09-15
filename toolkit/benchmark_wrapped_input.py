"""Full input/decode/release costs for copied versus wrapped input."""
import argparse
import json
from pathlib import Path

from benchmark_player_relocation import fixture
from benchmark_direct_input import loaded
from test_packet_lookahead import run,word
from test_direct_ring_input import place
from test_wrapped_input import LITERAL_COMPRESSED,LITERAL_DECODED


def whole_block(build,*,pointer,stored,split):
    cpu,labels,_,output=fixture(build)
    data=LITERAL_DECODED if stored else LITERAL_COMPRESSED
    place(cpu,1,pointer,data)
    for key,value in dict(ring_read_region=1,ring_read_high=pointer>>8,ring_read_low=pointer&255,
                           ahead_force=1,block_stored=int(stored)).items():cpu.write8(labels[key],value)
    for key,value in dict(ring_count=40,frame_length=len(data),block_length=len(LITERAL_DECODED),
                           block_end=output+len(LITERAL_DECODED),slice_output=output,
                           slice_target=output+(2 if split else len(LITERAL_DECODED))).items():word(cpu,labels,key,value)
    start=cpu.tstates;run(cpu,labels,'load_block_body');run(cpu,labels,'slice_begin')
    if split:
        for target in (17,127,128,129,257,6400):
            word(cpu,labels,'slice_target',output+target);run(cpu,labels,'slice_until')
    run(cpu,labels,'direct_release')
    assert bytes(cpu.read8(output+i) for i in range(len(LITERAL_DECODED)))==LITERAL_DECODED
    assert cpu.port_7ffd&7==7
    return cpu.tstates-start


def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline-build',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();rows={}
    def record(name,fn):
        before=fn(args.baseline_build);after=fn(args.build)
        rows[name]=dict(previous_tstates=before,current_tstates=after,delta=after-before)
    for pointer,length in ((0xC004,6000),(0xFBF0,1040),(0xF004,6000)):
        record(f'load_{pointer:04x}_{length}',lambda b,p=pointer,n=length:loaded(b,p,n)[3])
    for stored in (False,True):
        for pointer in ((0xC004,0xFFF0,0xFFFF) if not stored else (0xC004,0xF004)):
            for split in (False,True):
                record(f'{"stored" if stored else "compressed"}_{pointer:04x}_{"sliced" if split else "whole"}',
                       lambda b,p=pointer,s=stored,q=split:whole_block(b,pointer=p,stored=s,split=q))
    maps={}
    for region in (1,5):
        cpu,labels,_,_=fixture(args.build);cpu.write8(labels['direct_region'],region);cpu.set_hl(0)
        maps[str(region)]=run(cpu,labels,'direct_wrap')
    report=dict(baseline_commit='de43e1b',timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='each routine entry through RET, without invoking CALL; whole block sums load, slices and release',
        exclusions=['IRQ','ULA contention','ROM service','disk latency','drawing','scheduler'],
        assumptions='6400 decoded bytes: 128 distinct literals repeated 50 times; stored or upstream ZX0 137-byte fixture',
        routines=rows,input_increment=dict(previous_tstates=6,current_without_wrap=24,delta=18),
        wrap_helper_tstates=maps,literal_no_wrap_overhead=96,
        begin_selection_delta=dict(contiguous_compressed=34,wrapped_compressed=24,stored=2))
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
