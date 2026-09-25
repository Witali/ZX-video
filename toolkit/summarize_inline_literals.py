"""Archive and verify full inline-literal CPU/Fuse results against cached-byte baseline."""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from summarize_partial_slots import pipeline
from summarize_uncontended_frame import metrics


def summarize(cpu,baseline,reports):
    if not cpu['complete'] or cpu['checked_frames']!=4221 or len(cpu['volumes'])!=3:
        raise ValueError('complete paired CPU run required')
    volumes=[]
    for c,old,new in zip(cpu['volumes'],baseline,reports):
        for r in (old,new):
            if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact']
                or not r['ay_records_exact'] or r['frames']!=c['frames_expected']
                or r['trd_sha256']!=c['trd_sha256'] or r['partial_slot_consumption']
                or not r['compiled_masks'] or not r['cached_huffman_byte']['in_bootstrap']
                or r['fast_read_retries']):
                raise ValueError('incomplete/wrong input or settings')
        if old.get('inline_literals') or new['inline_literals']['code_sha256']!=c['code']['inline']['sha256']:
            raise ValueError('wrong decoder')
        if c['delta_tstates']!=-27*c['literal_tokens']-17*c['blocks']:
            raise ValueError('unexpected CPU delta')
        if old['compiled_masks']!=new['compiled_masks'] or old['cached_huffman_byte']!=new['cached_huffman_byte']:
            raise ValueError('frame reconstruction differs')
        volume=dict(part=c['part'],frames=c['frames_expected'],blocks=c['blocks'],literal_tokens=c['literal_tokens'],
            trd_sha256=c['trd_sha256'],cpu_delta_tstates=c['delta_tstates'])
        for mode,r in (('baseline',old),('inline',new)):
            stages=c['summary'][mode]['stages']
            volume[mode]=dict(cpu_tstates=c['summary'][mode]['tstates'],cpu_stages=stages,
                metrics=metrics(r),pipeline=pipeline(r,c['frame_start']))
            if r['runtime_sectors_checked']!=c['summary'][mode]['sectors']:
                raise ValueError('CPU/Fuse sector count differs')
        volumes.append(volume)
    totals={mode:{key:sum(v[mode]['metrics'][key] for v in volumes) for key in
        ('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors',
         'read_service_tstates','seek_service_tstates','publication_span_tstates')} for mode in ('baseline','inline')}
    for mode in totals:
        totals[mode].update(cpu_tstates=cpu['totals'][mode],
            core_tstates=sum(v[mode]['cpu_stages']['local_zx0'] for v in volumes),
            wait_tstates=sum(v[mode]['pipeline']['wait_tstates'] for v in volumes),
            packet_tstates=sum(v[mode]['pipeline']['packet_tstates'] for v in volumes))
    return dict(complete=True,release=False,volumes=volumes,totals=totals,
        cpu_delta_tstates=cpu['delta_tstates'],compressed_bytes_changed=False,
        full_packet_bytes_checked_in_cpu=True,reads_of_unproduced_bytes_forbidden=True,
        fuse_samples_per_frame=80,full_fuse_pixel_comparison=False,
        new_full_pixel_cpu_comparison=False,new_bootstrap_capacity_verified=False,
        physical_drive_verified=False,initial_disk_and_irq_phases_not_matched=True,
        nominal_schedule_met=all(v['inline']['metrics']['nominal_late_frames']==0 and
            v['inline']['metrics']['max_actual_deviation_tstates']<=64 for v in volumes),
        fallback_met=all(v['inline']['metrics']['actual_out_over_one_field']==0 and
            v['inline']['metrics']['bad_actual_intervals']==0 for v in volumes),
        ay_schedule_met=all(v['inline']['metrics']['audio_underruns']==0 for v in volumes))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fresh',type=Path)
    p.add_argument('--cpu',type=Path,default=Path('toolkit/inline_literals_cpu.json'))
    p.add_argument('--baseline',type=Path,default=Path('toolkit/cached_huffman_byte_evidence'))
    p.add_argument('--evidence',type=Path,default=Path('toolkit/inline_literals_evidence'))
    p.add_argument('--output',type=Path,default=Path('toolkit/inline_literals_summary.json'))
    args=p.parse_args();files=[]
    if args.fresh:
        args.evidence.mkdir(parents=True,exist_ok=True)
        for part in (1,2,3):
            source=args.fresh/f'part{part:02}.json';r=json.loads(source.read_bytes())
            dest=args.evidence/source.name
            dest.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
            files.append(dict(file=dest.name,sha256=sha(dest.read_bytes())))
            for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
                blob=source.with_suffix(suffix).read_bytes()
                if sha(blob)!=r[key]:raise ValueError('raw trace differs')
                dest=args.evidence/(source.stem+suffix+'.gz');dest.write_bytes(gzip.compress(blob,mtime=0))
                files.append(dict(file=dest.name,sha256=sha(dest.read_bytes()),uncompressed_sha256=sha(blob)))
    else:
        saved=json.loads(args.output.read_bytes());files=saved['evidence']
    for item in files:
        blob=(args.evidence/item['file']).read_bytes()
        if sha(blob)!=item['sha256']:raise ValueError('archive differs')
        if 'uncompressed_sha256' in item and sha(gzip.decompress(blob))!=item['uncompressed_sha256']:
            raise ValueError('uncompressed archive differs')
    old=[args.baseline/f'part{part:02}.json' for part in (1,2,3)]
    result=summarize(json.loads(args.cpu.read_bytes()),[json.loads(p.read_bytes()) for p in old],
        [json.loads((args.evidence/f'part{part:02}.json').read_bytes()) for part in (1,2,3)])
    result.update(cpu_report_sha256=sha(args.cpu.read_bytes()),baseline_sha256=[sha(p.read_bytes()) for p in old],evidence=files)
    if args.fresh:args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    elif saved!=json.loads(json.dumps(result)):raise ValueError('derived results changed')
    print(json.dumps({k:v for k,v in result.items() if k not in ('volumes','evidence')},indent=2))


if __name__=='__main__':main()
