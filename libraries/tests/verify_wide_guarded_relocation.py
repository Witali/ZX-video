"""Move live guarded tables/handlers, complementing the padding-origin probe."""
import argparse
import gzip
import json
from pathlib import Path

from measure_long_copy import ROOT,samples,sha
from measure_full_token_dispatch import directed_tokens
from wide_guarded_support import wide_profile,native


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    original=ROOT/'libraries/evidence/wide_guarded_native.json.gz'
    before=json.loads(gzip.decompress(original.read_bytes()))
    assert before['complete']
    cases=list(samples())+[(n,p,r) for n,p,r,v in directed_tokens()]
    report=dict(date='2026-10-20',complete=False,release=False,goal_achieved=False,
        original_native_sha256=sha(original.read_bytes()),core=0x9e00,profiles={})
    for key,p in before['profiles'].items():
        profile=wide_profile(shared='shared' in key,direct='direct' in key,core=0x9e00)
        assert profile[1]['dispatch_low']==0x9e00
        assert profile[2]['service_memory_bytes']==p['metadata']['service_memory_bytes']
        rows=[]
        for index,((name,payload,raw),old) in enumerate(zip(cases,p['native_blocks'],strict=True)):
            assert name==old['case'] and sha(payload)==old['payload_sha256'] and sha(raw)==old['raw_sha256']
            reference=next(r for r in old['placements'] if r['offset']==253)
            exact=native(profile,payload,raw,offset=253)
            irq=native(profile,payload,raw,offset=253,interrupts=True)
            assert exact['tstates']==reference['candidate_tstates']
            assert exact['input_waits']==reference['input_waits']==irq['input_waits']
            assert exact['output_cursors']==reference['output_cursors']==irq['output_cursors']
            rows.append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),
                tstates=exact['tstates'],private_stack_bytes=exact['private_stack_bytes'],
                caller_stack_bytes=exact['caller_stack_bytes'],injected_interrupts=irq['injected_interrupts'],
                irq_private_stack_bytes=irq['private_stack_bytes'],irq_caller_stack_bytes=irq['caller_stack_bytes'],
                exact=True,publication_input_waits_tstates_equal=True))
            if index%100==0:print(key,index,'/',len(cases),'moved live tables/handlers exact',flush=True)
        report['profiles'][key]=dict(metadata=profile[2],cases=len(rows),blocks=rows,
            live_code_shift_bytes=-512,dispatch_low=profile[1]['dispatch_low'],
            token_body=profile[1]['token_body'],regions=[dict(address=at,bytes=len(blob),sha256=sha(blob))
                                                      for at,blob in profile[0]],
            injected_interrupts=sum(r['injected_interrupts'] for r in rows))
        print(key,'complete',flush=True)
    report['source_sha256_lf']={str(p.relative_to(ROOT)).replace('\\','/'):sha(p.read_bytes().replace(b'\r\n',b'\n'))
        for p in (Path(__file__),Path(__file__).with_name('wide_guarded_support.py'))}
    report['complete']=True
    args.output.write_bytes(gzip.compress(json.dumps(report,indent=2).encode()+b'\n',mtime=0))


if __name__=='__main__':main()
