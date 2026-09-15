"""Compare borrowed-input costs against the saved copying player."""
import argparse
import json
from pathlib import Path

from benchmark_player_relocation import fixture, prepare
from test_packet_lookahead import run, word
from test_direct_ring_input import place


def loaded(build,pointer,length):
    cpu,labels,_,output=fixture(build)
    place(cpu,1,pointer,bytes(length))
    for key,value in dict(ring_read_region=1,ring_read_high=pointer>>8,ring_read_low=pointer&255,ahead_force=1).items():cpu.write8(labels[key],value)
    word(cpu,labels,'ring_count',40);word(cpu,labels,'frame_length',length)
    cost=run(cpu,labels,'load_block_body')
    return cpu,labels,output,cost


def decode(build,stage):
    cpu,labels,output,_=loaded(build,0xC004,600)
    word(cpu,labels,'block_length',600);word(cpu,labels,'block_end',output+600)
    word(cpu,labels,'slice_output',output);word(cpu,labels,'slice_target',output+2)
    cpu.write8(labels['block_stored'],1)
    cost=run(cpu,labels,'slice_begin')
    if stage=='resume':
        word(cpu,labels,'slice_target',output+130);cost=run(cpu,labels,'slice_until')
    elif stage=='already_ready':cost=run(cpu,labels,'slice_until')
    elif stage=='finish':
        word(cpu,labels,'slice_target',output+600);cost=run(cpu,labels,'slice_until')
    assert cpu.port_7ffd&7==7
    return cost


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline-build',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();rows={}
    def record(name,fn):
        before=fn(args.baseline_build);after=fn(args.build)
        rows[name]=dict(previous_tstates=before,current_tstates=after,delta=after-before)
    for name,pointer,length in [('contiguous_6000',0xC004,6000),('exact_end_1040',0xFBF0,1040),('crossing_6000',0xF004,6000)]:
        record('load_'+name,lambda b,p=pointer,n=length:loaded(b,p,n)[3])
    for stage in ('begin','resume','already_ready','finish'):record('stored_slice_'+stage,lambda b,s=stage:decode(b,s))
    for background in (False,True):record('two_packets_'+('background' if background else 'foreground'),lambda b:bg_cost(b,background))
    release={}
    for pointer,length in ((0xC004,6000),(0xFBF0,1040),(0xC003,12)):
        cpu,labels,_,_=loaded(args.build,pointer,length)
        release[str(length)]=run(cpu,labels,'direct_release')
    cpu,labels,_,_=fixture(args.build)
    no_held=run(cpu,labels,'direct_release');no_page=run(cpu,labels,'direct_page')
    cpu.write8(labels['direct_region'],1);page=run(cpu,labels,'direct_page')
    consume={}
    for region,high in ((1,0xC0),(1,0xFF),(5,0xFF)):
        cpu,labels,_,_=fixture(args.build)
        word(cpu,labels,'ring_count',40)
        cpu.write8(labels['ring_read_region'],region);cpu.write8(labels['ring_read_high'],high)
        consume[f'{region}:{high:02x}']=run(cpu,labels,'consume_sector')
    report=dict(consume_sector_tstates=consume,baseline_commit='da60d63',timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='routine entry through RET, excludes invoking CALL; two packets includes all preparation and coroutine calls',
        exclusions=['IRQ','ULA contention','ROM service','disk latency','drawing','scheduler'],
        assumptions='stored fixture, ring_count=40, foreground copy forced; slice begins at output+2, resume to +130, finish at +600',
        routines=rows,release_tstates=release,release_inactive_tstates=no_held,
        page_tstates=dict(inactive=no_page,active=page),
        inline_deltas=dict(contiguous_load=161,exact_end_load=171,crossing_overhead=151,
                           slice_begin_active=154,slice_resume_active=148,slice_return=52,
                           slice_begin_copied=51,slice_resume_copied=45))
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


def bg_cost(build,background):return prepare(build,background)[0]


if __name__=='__main__':main()
