"""Count queue-control paths in the actual old/new cold-loaded machine code.

Includes CALL instructions and internal queue routines. Excludes callee bodies
for AY/drive service, decoder, sector supply and packet copy by intercepting
those entries. These isolated path counts are not a full playback CPU replay.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from benchmark_compact_screen import STACK, STOP
from benchmark_context_huffman import word
from build_fap3_trd import sha
from test_fap3_disk import DiskCPU
from test_warm_continuation import player,until
import fap3_disk_z80 as disk

ROOT=Path(__file__).parent


def run(image,m,case):
    c=DiskCPU(player(image),image);until(c,disk.DRIVER)
    q=m['queue_labels'];z=m['decoder_labels'];bridge=q['bridge'];stream=bool(m.get('streaming_input'))
    listing={r['address']:r for r in m['slot_queue_instruction_listing']}
    for name in ('phase','count','write_slot','read_slot'):c.write8(q[name],0)
    word(c,q['blocks_left'],1);word(c,q['position'],0)
    word(c,z['block_length'],1024);word(c,z['block_end'],0xc400);word(c,z['slice_output'],0xc000)
    if stream:
        c.write8(z['input_needed'],0);c.write8(z['finished'],0)
    phase={'full':0,'eof_idle':0,'begin':0,'header_wait':1,'prefix_ready':1,
        'decode_more':2,'decode_eof':2,'input_wait':2,'supply':3,'take_ready':0,
        'take_partial':2,'take_need_decode':2,'take_need_input':3}[case]
    c.write8(q['phase'],phase)
    if case=='full':c.write8(q['count'],3)
    if case=='eof_idle':word(c,q['blocks_left'],0)
    if case=='decode_eof':word(c,z['slice_output'],0xc300)
    if case in ('take_need_decode','take_need_input'):word(c,z['slice_output'],0xc100)
    if case=='take_ready':c.write8(q['count'],1);word(c,q['lengths'],1024)
    if case=='take_partial':word(c,z['slice_output'],0xc200)
    if case=='take_need_input':c.write8(z['input_needed'],1)
    c.pc=q['take'] if case.startswith('take_') else q['step'];c.sp=STACK;c.push(STOP)
    c.set_bc(1024 if case=='take_ready' else 512 if case in ('take_need_decode','take_need_input') else 256)
    c.set_de(0xa500);c.iff1=False;hist=Counter();calls=Counter();steps=0
    def complete_decode():
        target=word(c,z['slice_target']);word(c,z['slice_output'],target)
        if stream:
            c.write8(z['finished'],int(target==0xc400));c.write8(z['input_needed'],int(case=='input_wait'))
    while c.pc!=STOP:
        steps+=1
        if steps>10000 or c.pc==q['fatal']:raise AssertionError(('queue case failed',case,hex(c.pc)))
        pc=c.pc;skip=None
        if pc==m['resident_audio']['hooks']['queue_service']:
            c.a=c.read8(q['phase']);skip='AY/drive hook'
        elif pc==bridge['begin_input']:skip='begin producer'
        elif pc==bridge['input_step']:
            c.a=int(case!='header_wait');skip='sector prefix'
        elif pc==bridge['begin_decode']:
            word(c,z['slice_output'],0xc000);skip='begin decoder'
        elif pc==bridge['decode_step']:
            complete_decode();skip='decode prefix'
        elif pc==bridge['copy']:
            c.set_de(c.de()+c.bc());c.set_bc(0);skip='packet copy'
        if skip:
            calls[skip]+=1;c.pc=c.pop();continue
        before=c.tstates;c.step();ticks=c.tstates-before
        row=listing[pc];wanted=row['tstates']
        if ticks not in (wanted if isinstance(wanted,list) else [wanted]):
            raise AssertionError(('queue instruction timing',row,ticks))
        hist[pc,ticks]+=1
    if c.sp!=STACK:raise AssertionError('queue stack differs')
    return dict(case=case,tstates=sum(t*n for (_,t),n in hist.items()),excluded_calls=dict(calls),
        phase=c.read8(q['phase']),count=c.read8(q['count']),position=word(c,q['position']),
        instruction_histogram=[dict(address=pc,tstates=t,count=n,instruction=listing[pc]['instruction'])
            for (pc,t),n in sorted(hist.items())])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('baseline','streaming','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();report=dict(complete=False,release=False,scope=__doc__,variants={})
    for name,folder in (('baseline',a.baseline),('streaming',a.streaming)):
        stem=folder/'ZX-video-huffman-preview_part01'
        image=stem.with_suffix('.trd').read_bytes();meta=stem.with_suffix('.json').read_bytes();m=json.loads(meta)
        if sha(image)!=m['trd_sha256']:raise ValueError('image identity differs')
        cases=['full','eof_idle','begin','header_wait','prefix_ready','decode_more','decode_eof',
               'take_ready','take_partial','take_need_decode']
        if name=='streaming':cases+=['input_wait','supply','take_need_input']
        rows=[run(image,m,case) for case in cases]
        report['variants'][name]=dict(trd_sha256=sha(image),metadata_sha256=sha(meta),cases=rows)
    report['complete']=True
    report['source_sha256_lf']={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in
        ('measure_inplace_streaming_queue.py','validate_fast_sparse.py','test_fap3_disk.py')}
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:[(r['case'],r['tstates']) for r in v['cases']] for k,v in report['variants'].items()}))


if __name__=='__main__':main()
