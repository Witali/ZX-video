"""Compare complete playback and identify lost IRQs in monitored DI windows.

Diagnostic runs may have a different disk/start phase from the baseline.
Their timestamps must not be substituted into the before/after comparison.
"""
import argparse
import hashlib
import json
from pathlib import Path

FIELD=70908
IRQ_PULSE=36  # Spectrum 128 Ferranti 7C, libspectrum timings.c
TIMING_SOURCE='https://github.com/speccytools/libspectrum/blob/master/timings.c'
def read(path): return json.loads(path.read_bytes())
def sha(data): return hashlib.sha256(data).hexdigest()
def missing_fields(data):
    ticks=data['audio_tick_tstates'];lo,hi=ticks[0]//FIELD,ticks[-1]//FIELD
    observed={t//FIELD for t in ticks+data['audio_underrun_tstates']}
    return sorted(set(range(lo,hi+1))-observed)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('baseline','candidate','baseline-disks','candidate-disks','diagnostics','output','evidence'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--generic',type=Path,help='Normalize legacy hot-path summary flags without changing measured results')
    p.add_argument('--generic-baseline',type=Path,help='Check generic FAP3 streams against the previous experiment')
    args=p.parse_args();old,new=read(args.baseline),read(args.candidate)
    if not old['complete'] or not new['complete'] or old['ends']!=new['ends']: raise ValueError('incomplete or different partition')
    rows=[]
    for i,end in enumerate(new['ends'],1):
        pair=[];images=[]
        for directory,summary in ((args.baseline_disks,old),(args.candidate_disks,new)):
            r=summary['variants'][0]['volumes'][i-1]
            data=read(directory/r['full_report'])
            disk=directory/f'ZX-video-huffman-preview_part{i:02}.trd'
            meta=read(disk.with_suffix('.json'));blob=disk.read_bytes()
            if not data['complete'] or sha(blob)!=data['trd_sha256'] or data['trd_sha256']!=r['trd_sha256']:
                raise ValueError('evidence differs')
            at=meta['video_start_sector']*256;images.append(blob[at:at+meta['video_physical_sectors']*256])
            pair.append(dict(unobserved_irq_fields=len(missing_fields(data)),empty_queue_visits=data['audio_underruns'],
                ay_missing_fields=data['ay_record_field_gaps'],actual_fps=r['timing']['actual_fps'],
                nominal_missed=r['timing']['missed_nominal_frames'],used_sectors=r['used_sectors']))
        if images[0]!=images[1]: raise AssertionError('physical video bytes changed')
        rows.append(dict(part=i,frame_end_exclusive=end,physical_video_byte_exact=True,
            physical_video_sha256=sha(images[0]),baseline=pair[0],candidate=pair[1]))
    diagnostic=[];args.evidence.mkdir(parents=True,exist_ok=True)
    for name in ('part01.json','addresses01.json'):
        path=args.diagnostics/name;data=read(path)
        if not data['complete']: raise ValueError('partial diagnosis')
        ticks=data['audio_tick_tstates'];lo,hi=ticks[0]//FIELD,ticks[-1]//FIELD
        observed={v['tstate']//FIELD for v in data['irq_entries']}
        missing=sorted(set(range(lo,hi+1))-observed);details=[]
        for field in missing:
            edge=field*FIELD
            if 'paging_samples' in data:
                nearby=[r for r in data['paging_samples'] if edge-108<=r['tstate']<edge+108]
                pair=None
                for start in nearby:
                    if start['kind']!='after_di': continue
                    stop=next((r for r in nearby if r['kind']=='before_ret'
                        and r['tstate']>start['tstate'] and (r['sp'],r['caller'])==(start['sp'],start['caller'])),None)
                    # DI may span the field boundary. EI is followed by RET,
                    # so IRQ becomes eligible only after RET completes.
                    if stop and start['tstate']-4<=edge and stop['tstate']+10>=edge+IRQ_PULSE:
                        pair=(start,stop);break
                if pair is None: raise AssertionError('lost IRQ not covered by the paging DI interval')
                start,stop=pair
                if stop['tstate']-start['tstate']!=74: raise AssertionError('paging instruction interval differs')
                details.append(dict(field=field,di_instruction_start_tstate=start['tstate']-4,
                    di_after_tstate=start['tstate'],irq_eligible_after_tstate=stop['tstate']+10,
                    pulse_start=edge,pulse_end=edge+IRQ_PULSE,samples=nearby))
            else:
                details.append(dict(field=field,samples=[r for r in data['field_samples'] if r['tstate']//FIELD==field]))
        target=args.evidence/('diagnostic_'+name)
        blob=(json.dumps(data,separators=(',',':'))+'\n').encode();target.write_bytes(blob)
        diagnostic.append(dict(file=target.name,sha256=sha(blob),frames=data['frames'],
            recorded_irq_entries=len(data['irq_entries']),unobserved_irq_fields=len(missing),
            all_missing_fields=details,identical_baseline_timing=False))
    result=dict(complete=True,release=False,scope=__doc__,baseline_commit='00fb0fd',frames=new['frames'],
        volumes=rows,diagnostics=diagnostic,
        baseline_unobserved_irq_fields=sum(r['baseline']['unobserved_irq_fields'] for r in rows),
        unobserved_irq_fields=sum(r['candidate']['unobserved_irq_fields'] for r in rows),
        all_physical_video_sections_exact=True,physical_drive_verified=False,
        irq_pulse_tstates=IRQ_PULSE,irq_timing_source=TIMING_SOURCE)
    if args.generic:
        generic=read(args.generic)
        changed=any(generic.get(k,False) for k in ('inline_matches','fast_noop_scan','irq_safe_paging'))
        corrections=[]
        for case in generic['cases']:
            expected=dict(player_hot_path_changed=changed,player_hot_path_delta_tstates=None if changed else 0)
            previous={k:case['timing'].get(k) for k in expected}
            if previous!=expected:
                corrections.append(dict(source=case['source'],previous=previous))
                case['timing'].update(expected)
        if corrections:
            generic['summary_metadata_correction']=dict(script=Path(__file__).name,
                reason='Old aggregate flags considered only inline_matches; no measured timings were changed',cases=corrections)
            args.generic.write_text(json.dumps(generic,indent=2)+'\n')
        if args.generic_baseline:
            prior=read(args.generic_baseline)
            keys=lambda r:[(c['source'],c['frames'],c['stream_sha256']) for c in r['cases']]
            if not generic['complete'] or not prior['complete'] or keys(generic)!=keys(prior):
                raise AssertionError('generic FAP3 streams differ or incomplete')
            result['generic_streams_exact']=True
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('diagnostics','volumes')}))


if __name__=='__main__': main()
