"""Execute optimized streaming ZX0 and its split layout on all archived blocks.

Exact CPU costs exclude disk/ROM/ULA/IRQ and the integrated packet queue.
The f962cac paired report supplies both previous standalone CPU baselines.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import struct

from benchmark_bank_local_zx0 import sha
from test_streaming_inline_zx0 import InlineHarness
from verify_streaming_zx0_input import validate_histogram
from zx0_codec import decompress
import streaming_inline_zx0 as machine
import streaming_zx0_layout as layout

ROOT=Path(__file__).parent


class SplitHarness(InlineHarness):
    def __init__(self):
        super().__init__();regions,z,self.layout=layout.build()
        self.labels=z;c=self.cpu;c.labels=z
        c.patched={z[n] for n in ('slice_high_operand','slice_low_operand','slice_equal_branch',
            'match_high_operand','match_low_operand','match_equal_branch')}
        c.patched.update((z['dzx0t_last_offset']+1,z['dzx0t_last_offset']+2))
        for address,data in regions:
            for i,value in enumerate(data):c.write8(address+i,value)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'streaming_inline_zx0_cpu.json')
    a=p.parse_args();old_path=ROOT/'streaming_zx0_input_cpu.json';old=json.loads(old_path.read_bytes())
    evidence=json.loads((ROOT/'streaming_zx0_input_evidence.json').read_bytes())
    if not old['complete'] or evidence['cpu_report_sha256']!=sha(old_path.read_bytes()):raise ValueError('wrong reference')
    inline=InlineHarness();split=SplitHarness()
    result=dict(complete=False,release=False,scope=__doc__,baseline_commit='f962cac',
        reference_sha256=sha(old_path.read_bytes()),stream_delta_bytes=0,
        code_bytes=len(inline.code),code_hex=inline.code.hex(),labels=inline.labels,split_layout=split.layout,
        sources={n:sha((ROOT/n).read_bytes()) for n in ('streaming_inline_zx0.py','streaming_zx0_layout.py',
            'test_streaming_inline_zx0.py','benchmark_streaming_inline_zx0.py','incremental_zx0.py','zx0_codec.py',
            'benchmark_streaming_zx0_input.py')},volumes=[])
    def save():a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    for v,archive in zip(old['volumes'],evidence['evidence'],strict=True):
        packed=(ROOT/'streaming_zx0_input_evidence'/archive['file']).read_bytes()
        if sha(packed)!=archive['sha256']:raise ValueError('archive changed')
        stream=gzip.decompress(packed)
        if sha(stream)!=v['stream_sha256']:raise ValueError('stream changed')
        rows=[];hist=Counter();position=0
        for i,b in enumerate(v['blocks']):
            size,length=struct.unpack_from('<HH',stream,position);position+=4
            payload=stream[position:position+length];position+=length;raw=decompress(payload,limit=size)
            if sha(raw)!=b['raw_sha256']:raise ValueError('raw block changed')
            costs=[]
            for h in (inline,split):
                h.begin(payload,raw,input_offset=b['input_offset'],slot=(0,1,3,4)[i%4]);r=h.decode();costs.append(r)
            if costs[0]!=costs[1]:raise ValueError('split layout changes output/cost/suspension')
            hist.update(inline.histogram)
            rows.append(dict(block=i,tstates=r['tstates'],baseline_tstates=b['baseline_tstates'],
                previous_tstates=b['prototype_tstates'],delta_to_baseline=r['tstates']-b['baseline_tstates'],
                delta_to_previous=r['tstates']-b['prototype_tstates'],private_stack_bytes=r['private_stack_bytes'],
                input_waits=r['input_waits'],slices=r['slices'],raw_sha256=sha(raw),compressed_sha256=sha(payload)))
            if (i+1)%16==0:print(f'part {v["part"]}: {i+1}/{len(v["blocks"])} inline/split blocks exact',flush=True)
        if position!=len(stream):raise ValueError('trailing archive input')
        hrows=[dict(pc=pc,tstates=t,count=count) for (pc,t),count in sorted(hist.items())]
        total=sum(r['tstates'] for r in rows)
        if validate_histogram(inline.code,machine.CODE,hrows)!=total:raise ValueError('timing sums differ')
        row=dict(part=v['part'],frames=v['frames'],stream_sha256=v['stream_sha256'],blocks=rows,
            tstates=total,baseline_tstates=v['totals']['baseline_tstates'],previous_tstates=v['totals']['prototype_tstates'],
            delta_to_baseline=total-v['totals']['baseline_tstates'],delta_to_previous=total-v['totals']['prototype_tstates'],
            all_bytes_exact=True,split_code_cpu_exact=True,instruction_histogram=hrows)
        result['volumes'].append(row);save();print(json.dumps({k:value for k,value in row.items() if k not in ('blocks','instruction_histogram')}),flush=True)
    result['complete']=True;save()


if __name__=='__main__':main()
