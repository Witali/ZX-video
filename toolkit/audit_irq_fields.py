"""Locate physical fields without an IM2 entry in a complete real Fuse trace."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

FIELD=70908


def audit(r,m):
    if not r['complete'] or r['errors'] or r['failure']:raise ValueError('requires complete successful content check')
    if r['trd_sha256']!=m['trd_sha256']:raise ValueError('metadata mismatch')
    pubs=r['publications'];first=pubs[0]['tstate']//FIELD;last=pubs[-1]['tstate']//FIELD
    counts=Counter(v['tstate']//FIELD for v in r['irq_entries'])
    rows=sorted(m['slot_queue_instruction_listing'],key=lambda v:v['address'])
    missing=[]
    for field in range(first,last+1):
        if counts[field]:continue
        samples=[]
        for s in r['field_samples']:
            if s['tstate']//FIELD!=field:continue
            candidates=[v for v in rows if v['address']<=s['pc']]
            near=max(candidates,key=lambda v:v['address']) if candidates else None
            samples.append(dict(s,nearest_listing_instruction=near))
        around=[dict(index=i,**p) for i,p in enumerate(pubs) if abs(p['tstate']//FIELD-field)<=7]
        missing.append(dict(physical_field=field,samples=samples,nearby_publications=around))
    return dict(part=m['part'],complete=True,frames=len(pubs),first_publication_field=first,
        last_publication_field=last,missing_irq_fields=missing,
        duplicate_irq_fields=[dict(field=f,entries=n) for f,n in sorted(counts.items()) if first<=f<=last and n>1],
        counter_late_frames=r['nominal_late_frames'],actual_late_over_64t=sum(t>64 for t in r['actual_phase_tstates']),
        ay_record_field_gaps=r['ay_record_field_gaps'],audio_underruns=r['audio_underruns'],
        actual_phase_tstates=r['actual_phase_tstates'],
        scope='Read-only physical field/IRQ correlation. Nearest listing row is only a locator, not a ROM disassembly.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','metadata','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();report=audit(json.loads(a.trace.read_bytes()),json.loads(a.metadata.read_bytes()))
    report['input_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.trace,a.metadata)}
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('actual_phase_tstates','input_sha256')},indent=2))


if __name__=='__main__':main()
