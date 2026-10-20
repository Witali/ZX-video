"""Case11x compact policy across guarded modes and strongest existing options."""
import argparse,json
from pathlib import Path
from measure_long_copy import samples,sha
from test_streaming_lzsa2 import independent


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    cases=[c for c in samples() if not c[0].startswith('random-')]
    cases += [('single-nibble-eof-A',bytes.fromhex('ef41f0e8'),b'A'),('single-nibble-eof-empty',bytes.fromhex('e7f0e8'),b'')]
    result=dict(date='2026-10-20',complete=False,release=False,goal_achieved=False,profiles={})
    for direct in (False,True):
        rows=[]
        options=dict(direct_header=direct,long_copy=True,word_state_init=True,restore_compare=True,
            fast_jumps=True,nibble_prefill=True,compact_sync=True)
        for name,payload,raw in cases:
            places=[]
            for offset in (0,1,252,253,254,255):
                before=independent(payload,raw,offset=offset,**options)
                after=independent(payload,raw,offset=offset,compact_branches=True,**options)
                assert before['exact'] and after['exact'] and before['input_waits']==after['input_waits']
                assert before['input_start']==after['input_start']
                irq=independent(payload,raw,offset=offset,compact_branches=True,interrupts=True,**options) if offset==253 else None
                places.append(dict(offset=offset,baseline_tstates=before['tstates'],candidate_tstates=after['tstates'],
                    delta_tstates=after['tstates']-before['tstates'],exact=True,waits=after['input_waits'],
                    injected_interrupts=irq['injected_interrupts'] if irq else 0))
            rows.append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),placements=places))
        result['profiles']['direct' if direct else 'call']=dict(options=options,cases=rows)
        print('direct' if direct else 'call',len(rows),'cases * 6 exact placements',flush=True)
    result['complete']=True
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
