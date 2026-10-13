"""Compare the same guarded decoder before/after --long-copy, not complete input."""
import argparse
import json
from pathlib import Path


def comparison(before,after):
    old=json.loads(before.read_text());new=json.loads(after.read_text())
    assert old['complete'] and new['complete']
    assert old['stream_sha256']==new['stream_sha256'] and old['cases']==new['cases']
    rows=[]
    for left,right,li,ri in zip(old['blocks'],new['blocks'],old['independent'],new['independent']):
        assert left['payload_sha256']==right['payload_sha256']==li['payload_sha256']==ri['payload_sha256']
        assert left['raw_sha256']==right['raw_sha256']
        for key in ('sectors','carry_copy_bytes','input_waits','first_output_loaded_bytes'):
            assert left[key]==right[key]
        delta=right['decoder_tstates']-left['decoder_tstates']
        assert delta<=0 and right['producer_tstates']==left['producer_tstates']
        native=[]
        for a,b in zip(li['full_flags'],ri['full_flags']):
            assert a['exact'] and b['exact'] and a['input_waits']==b['input_waits']
            # IRQ costs belong to a separate check; less CPU work may change
            # the number of accepted synthetic interrupts.
            native.append(dict(input_start=b['input_start'],exact=True,
                before_tstates=a['tstates'],after_tstates=b['tstates'],
                injected_interrupts=b['injected_interrupts']))
        rows.append(dict(case=ri['case'],payload_sha256=right['payload_sha256'],
            raw_sha256=right['raw_sha256'],baseline_decoder_tstates=left['decoder_tstates'],
            candidate_decoder_tstates=right['decoder_tstates'],delta_tstates=delta,
            sectors=right['sectors'],input_waits=len(right['input_waits']),native=native))
    summary={key:new['candidate'][key] for key in ('producer_tstates','decoder_tstates',
        'total_tstates','sector_reads','sectors_exact_once','carry_copy_bytes','max_step_tstates')}
    summary.update(baseline_decoder_tstates=old['candidate']['decoder_tstates'],
        baseline_total_tstates=old['candidate']['total_tstates'],
        delta_tstates=new['candidate']['total_tstates']-old['candidate']['total_tstates'],
        slower_blocks=sum(r['delta_tstates']>0 for r in rows))
    return dict(cases=new['cases'],placements_per_case=6,stream_sha256=new['stream_sha256'],summary=summary,blocks=rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();directory=args.directory
    report=dict(complete=True,release=False,scope=__doc__,
        direct=comparison(directory/'streaming-before.json',directory/'streaming-after.json'),
        call=comparison(directory/'streaming-call-before.json',directory/'streaming-call-after.json'))
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({mode:report[mode]['summary'] for mode in ('direct','call')}))


if __name__=='__main__':main()
