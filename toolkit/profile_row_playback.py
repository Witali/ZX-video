"""Summarize a complete row-dictionary Fuse run without a CPU-only claim."""
import argparse
import json
from pathlib import Path
from profile_integrated_timing import analyze
from build_fap3_trd import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','metadata','output'): p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args(); trace=json.loads(a.trace.read_text()); meta=json.loads(a.metadata.read_text())
    # No CPU model is substituted for elapsed ULA/IRQ/drive time.
    result=analyze(trace,meta,dict(frames=[dict(tstates=None) for _ in range(meta['frames'])]))
    result.update(complete=True,release=False,scope=__doc__,deterministic_cpu_reference_available=False,
                  trace_sha256=sha(a.trace.read_bytes()),metadata_sha256=sha(a.metadata.read_bytes()))
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(stages={k:{f:v[f]['total'] for f in ('elapsed','disk_service','empty_wait')}
        for k,v in result['stages'].items()},queue=result['queue_at_packet'],late_phase=result['late_phase_histogram'])))


if __name__=='__main__':main()
