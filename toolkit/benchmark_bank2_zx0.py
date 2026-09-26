"""Pair every actual ZX0 block at 256-byte quotas, with identical guarded RAM.

Counts deterministic decoder CPU only, excluding transport, IRQ/ULA and
disk. Exact bytes, input bounds, suspension positions and costs must match.
"""
import argparse
import json
from pathlib import Path
from bank2_zx0 import build,install_decoder
from benchmark_bank_local_zx0 import Harness,disk_blocks
from build_fap3_trd import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();_,_,machine=build()
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='19942a9',
        machine=machine,source_sha256=sha(Path(__file__).read_bytes()),volumes=[])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    def save():a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    for part in (1,2,3):
        meta,stream,blocks=disk_blocks(a.directory,part)
        row=dict(part=part,trd_sha256=meta['trd_sha256'],stream_sha256=sha(stream),blocks=[],complete=False)
        report['volumes'].append(row)
        for i,(payload,raw) in enumerate(blocks):
            hs=[Harness(dynamic_input=True,inline_literals=True) for _ in range(2)];install_decoder(hs[1])
            for h in hs:
                h.begin(payload,raw,slot=(0,1,3,4)[i%4],screen_bit=(i&1)*8,input_offset=min(255,8192-len(payload)))
                for target in list(range(256,len(raw),256))+[len(raw)]:h.run(target)
                h.finish()
            if hs[0].slices!=hs[1].slices:raise AssertionError(('slice result or cycles differ',part,i))
            row['blocks'].append(dict(index=i,bytes=len(raw),compressed_sha256=sha(payload),raw_sha256=sha(raw),
                baseline_tstates=hs[0].total,tstates=hs[1].total,delta_tstates=hs[1].total-hs[0].total,
                slices=hs[1].slices))
            if i%10==0:save();print(f'Disk {part}: paired exact blocks {i+1}/{len(blocks)}',flush=True)
        row.update(complete=True,baseline_tstates=sum(b['baseline_tstates'] for b in row['blocks']),
                   tstates=sum(b['tstates'] for b in row['blocks']))
        save()
    report.update(complete=True,blocks=sum(len(v['blocks']) for v in report['volumes']),
        decoded_bytes=sum(b['bytes'] for v in report['volumes'] for b in v['blocks']),
        baseline_tstates=sum(v['baseline_tstates'] for v in report['volumes']),
        tstates=sum(v['tstates'] for v in report['volumes']),delta_tstates=0)
    save();print(json.dumps({k:v for k,v in report.items() if k not in ('volumes','machine')}),flush=True)


if __name__=='__main__':main()
