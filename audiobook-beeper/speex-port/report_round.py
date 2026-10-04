"""Archive verified round binaries and compact measurements without altering baseline evidence."""
import argparse
import hashlib
import json
from pathlib import Path
from save_evidence import copy,HERE,ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant',required=True);p.add_argument('--previous',required=True);p.add_argument('--round',required=True)
    a=p.parse_args();out=ROOT/'build/speex-port';target=HERE/'rounds'/a.round;target.mkdir(parents=True,exist_ok=True)
    r=json.loads((out/a.variant/'report.json').read_text());old=json.loads((out/a.previous/'report.json').read_text())
    r.pop('out_intervals_histogram',None)
    r.update(variant=a.variant,previous=a.previous,delta_tstates=r['total_tstates']-old['total_tstates'],
             speedup_over_previous=old['total_tstates']/r['total_tstates'],
             payload_sha256=hashlib.sha256((out/'input.spxraw').read_bytes()).hexdigest())
    (target/'report.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')
    for name in ('player.ihx','player.map','checks.json','decoder.s','filter.s'):
        copy(out/a.variant/name,target/name)
    print({k:r[k] for k in ('variant','total_tstates','delta_tstates','speedup_over_previous','code_bytes','bss_bytes','tables_bytes')})


if __name__=='__main__':main()
