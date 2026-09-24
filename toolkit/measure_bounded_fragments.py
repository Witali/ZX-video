"""Compare actual optimal packet-block ZX0 sizes after bounded re-encoding."""
import argparse
import json
from pathlib import Path
from probe_two_level_fragments import measure_zx0
from probe_lossless_layouts import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','candidate','zx0','cache','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    args=p.parse_args();report=dict(complete=False,release=False,baseline_commit='3e0db88',rows=[])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for label,path in [('baseline',args.source),('candidate',args.candidate)]:
        print(label,flush=True)
        row=measure_zx0(path.read_bytes(),args.zx0.resolve(),args.cache.resolve(),8192,
            read_cache=args.read_cache,jobs=4)
        report['rows'].append(dict(label=label,**row))
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    report.update(complete=True,zx0_delta_bytes=report['rows'][1]['stream_bytes']-report['rows'][0]['stream_bytes'],
        compressor_sha256=sha(args.zx0.read_bytes()),
        excludes='bootstrap, volume boundaries, interleave, CPU and physical disk latency')
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
