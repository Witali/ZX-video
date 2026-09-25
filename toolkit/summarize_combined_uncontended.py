"""Archive and verify full relocated playback against the demand-decode baseline."""
import argparse
import gzip
import json
from pathlib import Path
from build_fap3_trd import sha
from summarize_uncontended_frame import metrics


def summarize(cpu,baseline,reports):
    if (not cpu['complete'] or cpu['checked_frames']!=4221 or len(cpu['volumes'])!=3
        or not cpu['full_compact_and_both_native_exact'] or cpu['delta_tstates']!=0):
        raise ValueError('complete lossless CPU verification required')
    volumes=[]
    for c,old,new in zip(cpu['volumes'],baseline,reports):
        for r in (old,new):
            if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact']
                or not r['ay_records_exact'] or r['frames']!=c['end']-c['start']
                or r['trd_sha256']!=old['trd_sha256'] or r['fast_read_retries']
                or not r['progress_100_percent'] or not r['partial_slot_consumption']
                or not r['cached_huffman_byte']['in_bootstrap']):
                raise ValueError('incomplete/wrong input or settings')
        for key in ('inline_literals','demand_decode','compiled_masks','cached_huffman_byte',
                    'pixel_sample_offsets','runtime_sectors_checked','ay_ticks','rom_sha256'):
            if old[key]!=new[key]:raise ValueError(('different baseline',key))
        if old.get('uncontended_frame') or not new.get('uncontended_frame'):
            raise ValueError('wrong relocation variant')
        relocation=new['uncontended_frame']
        mask=[r for r in relocation['instruction_operands'] if r['address']==0xe313]
        if (len(mask)!=1 or mask[0]['old_operand']!=0xa4c0 or mask[0]['new_operand']!=0xb700
            or mask[0]['tstates']!=10 or mask[0]['baseline_tstates']!=10):
            raise ValueError('compiled metadata output was not relocated')
        installed=dict(new['slot_queue_fixture']['slot_queue_patches'])
        if (installed.get(0xe313)!=0x11 or installed.get(0xe314)!=0
            or installed.get(0xe315)!=0xb7):raise ValueError('wrong installed compiled mask operand')
        if (relocation['instruction_tstate_delta']!=0 or relocation['extra_runtime_bytes']!=0
            or any(r['delta_tstates']!=0 or r['baseline_tstates']!=r['tstates']
                   for r in relocation['instruction_operands'])):
            raise ValueError('address-only relocation changed the CPU path')
        if (c['checked_frames']!=new['frames'] or any(f['delta_tstates']!=0
            or f['baseline_tstates']!=f['tstates'] for f in c['frames'])
            or c['tstates']!=sum(f['tstates'] for f in c['frames'])):
            raise ValueError('incomplete frame CPU counts')
        volumes.append(dict(part=c['part'],frames=new['frames'],trd_sha256=new['trd_sha256'],
            baseline=metrics(old),relocated=metrics(new),cpu_tstates=c['tstates'],
            cpu_delta_tstates=c['delta_tstates'],relocation=relocation,
            installer=new['fixture_installer']))
    totals={mode:{key:sum(v[mode][key] for v in volumes) for key in
        ('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors',
         'read_service_tstates','seek_service_tstates','publication_span_tstates',
         'bad_actual_intervals')} for mode in ('baseline','relocated')}
    return dict(complete=True,release=False,baseline_commit='1d85e6e',volumes=volumes,totals=totals,
        cpu_tstates=cpu['tstates'],cpu_delta_tstates=0,compressed_bytes_changed=False,
        full_compact_and_both_native_cpu_comparison=True,fuse_samples_per_frame=80,
        full_fuse_pixel_comparison=False,new_bootstrap_capacity_verified=False,
        physical_drive_verified=False,initial_disk_and_irq_phases_not_matched=True,
        pipeline_wait_tracing=False,
        timing_note='End-to-end elapsed outcome includes ULA/IRQ/ROM/controller and phase differences; not an isolated ULA saving.',
        nominal_schedule_met=all(v['relocated']['nominal_late_frames']==0 and
            v['relocated']['max_actual_deviation_tstates']<=64 for v in volumes),
        fallback_met=all(v['relocated']['actual_out_over_one_field']==0 and
            v['relocated']['bad_actual_intervals']==0 for v in volumes),
        ay_schedule_met=all(v['relocated']['audio_underruns']==0 for v in volumes))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fresh',type=Path)
    p.add_argument('--cpu',type=Path,default=Path('toolkit/combined_uncontended_cpu.json'))
    p.add_argument('--baseline',type=Path,default=Path('toolkit/demand_decode_evidence'))
    p.add_argument('--evidence',type=Path,default=Path('toolkit/combined_uncontended_evidence'))
    p.add_argument('--output',type=Path,default=Path('toolkit/combined_uncontended_summary.json'))
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
    cpu=json.loads(args.cpu.read_bytes())
    model_path=Path(__file__).with_name('cached_huffman_byte_cpu.json')
    if (cpu['model_sha256']!=sha(model_path.read_bytes()) or
        cpu['source_sha256']!=sha(Path(__file__).with_name('benchmark_combined_uncontended.py').read_bytes())):
        raise ValueError('CPU model or benchmark source changed')
    model=json.loads(model_path.read_bytes())
    if cpu['tstates']!=model['tstates'] or cpu['states_sha256']!=model['states_sha256']:
        raise ValueError('different CPU reference')
    for c,m in zip(cpu['volumes'],model['volumes']):
        if c['raw_sha256']!=m['raw_sha256'] or [(f['frame'],f['tstates']) for f in c['frames']]!=[(f['frame'],f['tstates']) for f in m['frames']]:
            raise ValueError('different frame CPU reference')
    result=summarize(cpu,[json.loads(p.read_bytes()) for p in old],
        [json.loads((args.evidence/f'part{part:02}.json').read_bytes()) for part in (1,2,3)])
    result.update(cpu_report_sha256=sha(args.cpu.read_bytes()),baseline_sha256=[sha(p.read_bytes()) for p in old],evidence=files)
    if args.fresh:args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    elif saved!=json.loads(json.dumps(result)):raise ValueError('derived results changed')
    print(json.dumps({k:v for k,v in result.items() if k not in ('volumes','evidence')},indent=2))


if __name__=='__main__':main()
