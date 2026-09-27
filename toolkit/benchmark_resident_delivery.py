"""Measure changed resident-video streams using the retained producer/ZX0.

ROM is mocked and the service clock frozen, as in the pinned baseline.
All decoded bytes, sector order, carry copies and protected banks are
checked. Queue/frame/IRQ/ULA/ROM and physical disk elapsed time are separate.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from benchmark_bank_local_zx0 import disk_blocks
from benchmark_inplace_slot import Harness
from benchmark_inplace_streaming import CountedCPU,finish
from build_fap3_trd import sha

ROOT=Path(__file__).parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('directory','build','output'): p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args(); build=json.loads(a.build.read_bytes())
    reference_path=ROOT/'inplace_streaming_cpu.json'; reference=json.loads(reference_path.read_bytes())
    baseline_path=ROOT/'inplace_keepalive_build.json'; baseline=json.loads(baseline_path.read_bytes())
    if (not build['complete'] or not reference['complete'] or
            build['baseline_build_sha256']!=sha(baseline_path.read_bytes()) or
            reference['build_sha256']!=sha(baseline_path.read_bytes())):
        raise ValueError('incomplete or mismatched baseline')
    for name,digest in reference['source_sha256_lf'].items():
        if sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))!=digest: raise ValueError(('CPU source changed',name))
    names=('benchmark_resident_delivery.py',*reference['source_sha256_lf'])
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='a84451d',idle_clock_frozen=True,
        build_sha256=sha(a.build.read_bytes()),reference_sha256=sha(reference_path.read_bytes()),
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names},volumes=[])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    def save(): a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    keys=('producer_tstates','decoder_tstates','total_tstates','sector_reads','carry_copy_bytes'); save()
    try:
        for built,ref,old in zip(build['volumes'],reference['volumes'],baseline['volumes'],strict=True):
            part=built['part']; m,stream,blocks=disk_blocks(a.directory,part)
            if (sha(stream)!=built['stream_sha256'] or ref['stream_sha256']!=old['stream_sha256'] or
                    ref['video_start_sector']!=old['video_start_sector'] or m['trd_sha256']!=built['trd_sha256']):
                raise ValueError('different current/reference input')
            h=Harness(stream,built['video_start_sector'],inplace=True)
            h.cpu.__class__=CountedCPU; h.cpu.decoder_histogram=Counter()
            row=dict(part=part,stream_sha256=sha(stream),video_start_sector=built['video_start_sector'],
                baseline_summary=ref['baseline_summary'],blocks=h.results,
                producer_regions=[dict(address=at,code_hex=b.hex()) for at,b in h.regions])
            report['volumes'].append(row)
            for index,(payload,raw) in enumerate(blocks):
                h.block(payload,raw,index)
                if index%16==0:
                    save(); print(f'Part {part}: {index+1}/{len(blocks)} producer/ZX0 blocks exact',flush=True)
            row['summary']=finish(h); row['delta']={k:row['summary'][k]-row['baseline_summary'][k] for k in keys}; save()
        report.update(complete=True,baseline=reference['totals']['baseline'],
            candidate={k:sum(v['summary'][k] for v in report['volumes']) for k in keys})
        report['delta']={k:report['candidate'][k]-report['baseline'][k] for k in keys}
    except Exception as exc: report['failure']=repr(exc); raise
    finally: save()
    print(json.dumps({k:report[k] for k in ('baseline','candidate','delta')}),flush=True)


if __name__=='__main__': main()
