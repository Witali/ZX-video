"""Complete native comparisons for individually selected second-pass profiles."""
import argparse
import hashlib
import json
from pathlib import Path

from measure_long_copy import samples, compare
from test_libraries import profiles, ROOT
from lzsa.resumable import build


def digest(data):return hashlib.sha256(data).hexdigest()


def layout(profile):
    regions,labels,report=profile
    return dict(code_bytes=report['code_bytes'],core_end=report['core_end'],prefix_end=report['prefix_end'],
        state_bytes=labels['end']-labels['state'],private_stack=report['private_stack'],
        output_base=report['output_base'],labels_sha256=digest(json.dumps(labels,sort_keys=True).encode()),
        standalone_raw_region_sectors=sum((len(data)+255)//256 for _,data in regions),
        regions=[dict(address=at,bytes=len(data),sha256=digest(data)) for at,data in regions])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--item',choices=('10',),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    defaults=profiles()
    assert defaults==json.loads((ROOT/'tests/decoder_baseline.json').read_text())['profiles']
    baseline=build(long_copy=True,core_limit=0x9000)
    candidate=build(long_copy=True,near_literals=True,core_limit=0x9000)
    rows=[dict(case=name,**compare(payload,raw,baseline,candidate)) for name,payload,raw in samples()]
    assert candidate[2]['code_bytes']==baseline[2]['code_bytes']-3
    assert 'LongLiterals8Jump' not in candidate[1]
    report=dict(date='2026-10-14',item=args.item,baseline_revision='3f34a4a4',complete=True,release=False,
        scope=__doc__,baseline=layout(baseline),candidate=layout(candidate),
        summary=dict(cases=len(rows),decoded_bytes=sum(row['raw_bytes'] for row in rows),
            baseline_tstates=sum(row['baseline_tstates'] for row in rows),
            candidate_tstates=sum(row['candidate_tstates'] for row in rows),
            delta_tstates=sum(row['delta_tstates'] for row in rows),
            real_delta_tstates=sum(row['delta_tstates'] for row in rows if row['case'].startswith('real-')),
            slower_blocks=sum(row['delta_tstates']>0 for row in rows),
            slower_slices=sum(row['slower_slices'] for row in rows),
            injected_interrupts=sum(row['injected_interrupts'] for row in rows)),
        defaults_exact=len(defaults),streaming_profile_changed=False,blocks=rows)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report['summary']))


if __name__=='__main__':main()
