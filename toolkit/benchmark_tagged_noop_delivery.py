"""Measure the larger tagged stream's actual producer and ZX0 CPU cost.

Reads actual TRD sectors into the in-place slots. ROM is mocked and the
service clock is frozen, matching the retained complete-input reference.
Queue, frame, IRQ/ULA and physical disk elapsed time are measured separately.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from benchmark_bank_local_zx0 import disk_blocks
from benchmark_inplace_slot import Harness
from benchmark_inplace_streaming import CountedCPU, finish
from build_fap3_trd import sha

ROOT=Path(__file__).parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('directory','build','output'): p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args(); build=json.loads(a.build.read_bytes())
    reference=ROOT/'inplace_streaming_cpu.json'; before=json.loads(reference.read_bytes())
    previous=ROOT/'inplace_keepalive_build.json'; old=json.loads(previous.read_bytes())
    if (not build['complete'] or not before['complete'] or
            build['baseline_build_sha256']!=sha(previous.read_bytes()) or
            before['build_sha256']!=sha(previous.read_bytes())):
        raise ValueError('incomplete or mismatched evidence')
    for name,digest in before['source_sha256_lf'].items():
        if sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))!=digest: raise ValueError(('CPU baseline source differs',name))
    names=('benchmark_tagged_noop_delivery.py',*before['source_sha256_lf'])
    report=dict(complete=False,release=False,scope=__doc__,idle_clock_frozen=True,
        baseline_commit='a84451d',build_sha256=sha(a.build.read_bytes()),reference_sha256=sha(reference.read_bytes()),
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names},volumes=[])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    def save(): a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    keys=('producer_tstates','decoder_tstates','total_tstates','sector_reads','carry_copy_bytes')
    try:
        for built,ref,prev in zip(build['volumes'],before['volumes'],old['volumes'],strict=True):
            part=built['part']; m,stream,blocks=disk_blocks(a.directory,part)
            if (sha(stream)!=built['stream_sha256'] or ref['stream_sha256']!=prev['stream_sha256'] or
                    ref['video_start_sector']!=prev['video_start_sector'] or m['trd_sha256']!=built['trd_sha256']):
                raise ValueError('TRD or baseline CPU input differs')
            h=Harness(stream,built['video_start_sector'],inplace=True)
            h.cpu.__class__=CountedCPU; h.cpu.decoder_histogram=Counter()
            row=dict(part=part,stream_sha256=sha(stream),video_start_sector=built['video_start_sector'],
                baseline_summary=ref['baseline_summary'],blocks=h.results,
                producer_regions=[dict(address=at,code_hex=b.hex()) for at,b in h.regions])
            report['volumes'].append(row)
            for index,(payload,raw) in enumerate(blocks):
                h.block(payload,raw,index)
                if index%16==0:
                    save(); print(f'Part {part}: {index+1}/{len(blocks)} tagged producer/ZX0 blocks exact',flush=True)
            row['summary']=finish(h)
            row['delta']={k:row['summary'][k]-row['baseline_summary'][k] for k in keys}; save()
        report.update(complete=True,baseline=before['totals']['baseline'],
            tagged={k:sum(v['summary'][k] for v in report['volumes']) for k in keys})
        report['delta']={k:report['tagged'][k]-report['baseline'][k] for k in keys}
    except Exception as exc: report['failure']=repr(exc); raise
    finally: save()
    print(json.dumps({k:report[k] for k in ('baseline','tagged','delta')}),flush=True)


if __name__=='__main__': main()
