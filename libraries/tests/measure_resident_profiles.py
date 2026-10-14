"""Item28: complete resident input, one full output demand, same wire formats."""
import argparse
import json
from pathlib import Path
from measure_long_copy import samples,sha,ROOT
from measure_bit_phases import samples as zx0_samples
from native_block import execute
from lzsa.native import execute as coroutine
from lzsa.block import build as lzsa_block
from lzsa.resumable import build as lzsa_resumable
from zx0.block import build as zx0_block
from zx0.resumable import build as zx0_resumable
from test_libraries import profiles


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=dict(date='2026-10-14',baseline_revision='db9a50c0',complete=False,
        release=False,scope=__doc__,timing_source='https://www.zilog.com/docs/z80/um0080.pdf',default_profiles_exact=31,codecs={})
    assert profiles()==json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    for codec,blocks,old,new in (('lzsa2',samples,lzsa_resumable(),lzsa_block()),
                                  ('zx0',zx0_samples,zx0_resumable(),zx0_block())):
        rows=[]
        for name,payload,raw in blocks():
            before=coroutine(*old,payload,raw,source=0x2000,slice_bytes=None)
            after=execute(new,payload,raw);irq=execute(new,payload,raw,interrupts=True)
            relocated=(lzsa_block(core=0x9103,core_limit=0x9400) if codec=='lzsa2' else
                       zx0_block(core=0x9103,core_limit=0x9400))
            check=execute(relocated,payload,raw);assert check['tstates']==after['tstates']
            assert after['tstates']<before['tstates']
            rows.append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),raw_bytes=len(raw),
                baseline_tstates=before['tstates'],candidate_tstates=after['tstates'],delta_tstates=after['tstates']-before['tstates'],
                stack_bytes=after['stack_bytes'],interrupts=irq['injected_interrupts'],exact=True))
        report['codecs'][codec]=dict(baseline_bytes=sum(len(data) for _,data in old[0]),candidate_bytes=new[2]['code_bytes'],
            candidate=new[2],summary=dict(cases=len(rows),raw_bytes=sum(r['raw_bytes'] for r in rows),
                baseline_tstates=sum(r['baseline_tstates'] for r in rows),candidate_tstates=sum(r['candidate_tstates'] for r in rows),
                real_delta_tstates=sum(r['delta_tstates'] for r in rows if r['case'].startswith('real-')),
                slower_blocks=sum(r['delta_tstates']>0 for r in rows),interrupts=sum(r['interrupts'] for r in rows),
                stack_bytes=max(r['stack_bytes'] for r in rows)),blocks=rows)
        print(codec,json.dumps(report['codecs'][codec]['summary']),flush=True)
    report['complete']=True;args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')

if __name__=='__main__':main()
