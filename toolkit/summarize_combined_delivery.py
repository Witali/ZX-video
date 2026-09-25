"""Archive complete trials and compare only identical volume partitions.

Actual OUT recovery is computed independently of IRQ counters. Each archived
trace keeps every publication, AY timestamp and sector check. Screen samples
are not promoted to full-pixel verification, and missed deadlines stay failures.
"""
import argparse
import hashlib
import json
from pathlib import Path
import disk_layout

from summarize_irq_safe import missing_fields
from summarize_volume_huffman import actual_runs


def sha(blob):return hashlib.sha256(blob).hexdigest()
def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('directory','baseline-disks','reports','evidence','output'):
        p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args();rows=[];archive=[];groups={}
    trials=[('previous',args.reports/'irq_safe_fuse.json',args.baseline_disks),
        ('inline',args.reports/'combined_inline_fuse.json',args.directory/'inline'),
        ('control',args.reports/'combined_control_fuse.json',args.directory/'control'),
        ('inline_control',args.reports/'combined_inline_control_fuse.json',args.directory/'inline_control'),
        ('deferred',args.reports/'combined_deferred_fuse.json',args.directory/'deferred'),
        ('combined',args.reports/'combined_delivery_fuse.json',args.directory/'combined')]
    for name,path,directory in trials:
        summary=read(path)
        if not summary['complete'] or not summary['all_independently_bootable']:raise ValueError('incomplete set')
        frames=ay=sectors=0;volumes=[];span=0
        for row in summary['variants'][0]['volumes']:
            data=read(directory/row['full_report'])
            disk=directory/f'ZX-video-huffman-preview_part{row["part"]:02}.trd'
            meta=read(disk.with_suffix('.json'));blob=disk.read_bytes()
            if (not data['complete'] or not data['ay_records_exact'] or data['errors']
                or sha(blob)!=row['trd_sha256'] or data['trd_sha256']!=row['trd_sha256']
                or data['frames']!=row['frames'] or data['ay_ticks']!=6*row['frames']):
                raise ValueError('evidence or image differs')
            start=meta['video_start_sector']*256
            payload=blob[start:start+meta['video_physical_sectors']*256]
            offsets=(disk_layout.positions(meta['video_sectors'],meta['video_start_sector']%16)
                if meta.get('interleaved') else range(meta['video_sectors']))
            logical=b''.join(blob[start+o*256:start+(o+1)*256] for o in offsets)
            key=(tuple(summary['ends']),row['part'])
            if key in groups and groups[key]!=logical:raise AssertionError('same-partition logical video bytes changed')
            groups[key]=logical
            runs=actual_runs(data['actual_phase_tstates'])
            nominal=sum(abs(t)>64 for t in data['actual_phase_tstates'])
            if nominal!=row['timing']['missed_nominal_frames']:raise AssertionError('nominal summary differs')
            pub=data['publications'];duration=pub[-1]['tstate']-pub[0]['tstate'];span+=duration
            frames+=data['frames'];ay+=data['ay_ticks'];sectors+=data['runtime_sectors_checked']
            volumes.append(dict(part=row['part'],frames=row['frames'],used_sectors=row['used_sectors'],
                video_bytes=row['video_bytes'],video_physical_sha256=sha(payload),
                logical_video_sha256=sha(logical[:meta['video_bytes']]),video_start_sector=meta['video_start_sector'],
                actual_fps=(len(pub)-1)*3546900/duration,missed_nominal_frames=nominal,
                fallback_one_field_met=row['timing']['fallback_one_field_met'],
                ay_missing_fields=data['ay_record_field_gaps'],empty_queue_visits=data['audio_underruns'],
                unobserved_irq_fields=len(missing_fields(data)),read_retries=data['fast_read_retries'],
                recovered_actual_runs=sum(r['recovered_at'] is not None for r in runs),
                unrecovered_actual_runs=sum(r['recovered_at'] is None for r in runs),actual_runs=runs,
                max_actual_deviation_seconds=max(map(abs,data['actual_phase_tstates']))/3546900,
                elapsed_timing=data['elapsed_timing']))
            if name!='previous':
                target=args.evidence/name/row['full_report'];target.parent.mkdir(parents=True,exist_ok=True)
                saved=(json.dumps(data,separators=(',',':'))+'\n').encode();target.write_bytes(saved)
                archive.append(dict(file=target.relative_to(args.evidence).as_posix(),sha256=sha(saved),
                    frames=data['frames'],ay_ticks=data['ay_ticks'],checked_runtime_sectors=data['runtime_sectors_checked']))
        if frames!=summary['frames'] or frames!=summary['ends'][-1]:raise AssertionError('partial movie')
        rows.append(dict(name=name,ends=summary['ends'],options=summary['contract']['options'],
            frames=frames,ay_ticks=ay,runtime_sectors=sectors,volumes=volumes,
            weighted_fps=(frames-len(volumes))*3546900/span,
            missed_nominal_frames=sum(v['missed_nominal_frames'] for v in volumes),
            ay_missing_fields=sum(v['ay_missing_fields'] for v in volumes),
            playback_seconds=sum(v['elapsed_timing']['playback_tstates'] for v in volumes)/3546900))
    result=dict(complete=True,release=False,scope=__doc__,baseline_commit='3356730',
        full_pixel_comparison=False,pixel_samples_per_frame=80,physical_drive_verified=False,
        nominal_tolerance_tstates=64,nominal_period_tstates=425448,
        comparison_groups=[['previous','inline'],['control','inline_control','deferred','combined']],
        same_partition_logical_video_exact=True,
        physical_layout_note='Larger startup code changes first-track position and interleave holes; compare deinterleaved sectors',variants=rows)
    generic=read(args.reports/'combined_delivery_generic.json')
    previous=read(args.reports/'irq_safe_generic.json')
    signatures=lambda r:[(c['source'],c['frames'],c['stream_sha256']) for c in r['cases']]
    if not generic['complete'] or not previous['complete'] or signatures(generic)!=signatures(previous):
        raise AssertionError('generic inputs incomplete or FAP3 differs')
    if not all(c['timing']['complete'] and all(cpu['complete'] and cpu['full_compact_and_native_comparison']
        for cpu in c['cpu']) for c in generic['cases']):raise AssertionError('incomplete generic CPU verification')
    if any(c['timing']['disk_adapter_instruction_tstates']['same_track']['tstates']!=911 for c in generic['cases']):
        raise AssertionError('generic CPU summary did not use IRQ-safe paging')
    result['generic']=dict(cases=len(generic['cases']),frames=sum(c['frames'] for c in generic['cases']),
        ay_ticks=sum(c['ay_ticks'] for c in generic['cases']),disks=sum(c['disks'] for c in generic['cases']),
        complete_cpu_and_fuse=True,all_streams_exact=True,deferred_in_generic_cli=False,
        deadline_failures=[c['source'] for c in generic['cases'] if not c['timing']['all_nominal_deadlines_met']])
    (args.evidence/'index.json').write_text(json.dumps(archive,indent=2)+'\n')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k not in ('volumes','options')} for r in rows],indent=2))


if __name__=='__main__':main()
