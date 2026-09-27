"""Compare retained, tuned-Turbo and adapted-Fast on identical archived ZX0.

All 188 blocks, same sectors, producer, output quotas and bytes. Real Z80
execution checks every output write, input cursor, overlap, slot and protected
bank. ROM is mocked and clock frozen; IRQ/ULA, queues, frame publication and
bootstrap size are outside this CPU experiment. Stream size cannot change.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import struct

from benchmark_inplace_slot import Harness
from benchmark_inplace_streaming import CountedCPU, finish
from build_fap3_trd import sha
from zx0_codec import decompress
import faster_zx0

ROOT=Path(__file__).parent
VARIANTS=('baseline','turbo_tuned','fast')


def fixture(stream,first,variant):
    h=Harness(stream,first,inplace=True)
    layout=faster_zx0.install_harness(h,variant) if variant!='baseline' else None
    h.cpu.__class__=CountedCPU; h.cpu.decoder_histogram=Counter()
    return h,layout


def inputs():
    build=json.loads((ROOT/'inplace_keepalive_build.json').read_bytes())
    probe=json.loads((ROOT/'inplace_zx0_probe.json').read_bytes())
    if not build['complete'] or not probe['complete']:raise ValueError('incomplete reference')
    for v in build['volumes']:
        name=f'block15872-part{v["part"]:02}.stream.gz'
        packed=(ROOT/'inplace_zx0_evidence'/name).read_bytes()
        item=next(x for x in probe['archives'] if x['file']==name)
        stream=gzip.decompress(packed)
        if sha(packed)!=item['sha256'] or sha(stream)!=v['stream_sha256']:
            raise ValueError('source archive changed')
        blocks=[]; at=0
        while at<len(stream):
            size,n=struct.unpack_from('<HH',stream,at);at+=4
            payload=stream[at:at+n];at+=n
            blocks.append((payload,decompress(payload,limit=size)))
        if at!=len(stream):raise ValueError('trailing stream')
        yield v,stream,blocks


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'faster_zx0_cpu.json')
    p.add_argument('--limit',type=int,help='Smoke only: blocks per volume')
    a=p.parse_args()
    if a.output.exists():p.error('refusing to overwrite evidence')
    if a.limit is not None and a.limit<1:p.error('positive limit required')
    reference=json.loads((ROOT/'inplace_streaming_cpu.json').read_bytes())
    result=dict(complete=False,release=False,scope=__doc__,baseline_commit='a84451d',
        repository_input='9f14ad9',compressed_stream_delta_bytes=0,volumes=[],
        actual_new_playback_measured=False,new_trds_built=False)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    def save():a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    try:
        for v,stream,blocks in inputs():
            part=v['part']; hs={}; row=dict(part=part,stream_sha256=sha(stream),
                stream_bytes=len(stream),video_start_sector=v['video_start_sector'],variants={})
            result['volumes'].append(row)
            for name in VARIANTS:
                h,layout=fixture(stream,v['video_start_sector'],name);hs[name]=h
                row['variants'][name]=dict(layout=layout,blocks=h.results)
            for index,(payload,raw) in enumerate(blocks[:a.limit]):
                expected=reference['volumes'][part-1]['baseline'][index]
                for name,h in hs.items():
                    actual=h.block(payload,raw,index)
                    for field in ('producer_tstates','sectors','carry_copy_bytes'):
                        if actual[field]!=expected[field]:raise AssertionError(('producer differs',name,part,index,field))
                    if name=='baseline' and actual['decoder_tstates']!=expected['decoder_tstates']:
                        raise AssertionError('baseline CPU changed')
                    actual['decoder_delta_tstates']=actual['decoder_tstates']-expected['decoder_tstates']
                if index%8==0:save();print(f'part {part}: {index+1}/{len(blocks)} three-way blocks exact',flush=True)
            if a.limit is None:
                for name,h in hs.items():
                    summary=finish(h)
                    rows=summary['decoder_instruction_histogram']
                    summary['decoder_bank5_tstates']=sum(r['tstates']*r['count'] for r in rows if r['pc']<0x8000)
                    summary['decoder_bank2_tstates']=summary['decoder_tstates']-summary['decoder_bank5_tstates']
                    row['variants'][name]['summary']=summary
            save()
        if a.limit is None:
            keys=('producer_tstates','decoder_tstates','total_tstates','sector_reads','carry_copy_bytes',
                  'decoder_bank5_tstates','decoder_bank2_tstates')
            result['totals']={name:{k:sum(v['variants'][name]['summary'][k] for v in result['volumes'])
                for k in keys} for name in VARIANTS}
            for name in VARIANTS[1:]:
                rows=[b for v in result['volumes'] for b in v['variants'][name]['blocks']]
                result['totals'][name].update(faster_blocks=sum(b['decoder_delta_tstates']<0 for b in rows),
                    slower_blocks=sum(b['decoder_delta_tstates']>0 for b in rows),
                    delta_tstates=sum(b['decoder_delta_tstates'] for b in rows))
        result.update(complete=a.limit is None,blocks=sum(len(v['variants']['baseline']['blocks']) for v in result['volumes']))
    except Exception as exc:result['failure']=repr(exc);save();raise
    finally:
        names=('benchmark_faster_zx0.py','faster_zx0.py','benchmark_inplace_streaming.py',
            'benchmark_inplace_slot.py','inplace_slot_input_z80.py','inplace_slot_player.py','bank2_zx0.py',
            'bank_local_zx0.py','incremental_zx0.py','zx0_codec.py','third_party/zx0/dzx0_fast.asm',
            'third_party/zx0/dzx0_turbo.asm','verify_streaming_zx0_input.py','validate_fast_sparse.py')
        result['source_sha256_lf']={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names}
        result['references']={n:sha((ROOT/n).read_bytes()) for n in
            ('inplace_keepalive_build.json','inplace_zx0_probe.json','inplace_streaming_cpu.json')}
        save()
    print(json.dumps(result.get('totals',dict(smoke_blocks=result['blocks']))),flush=True)


if __name__=='__main__':main()
