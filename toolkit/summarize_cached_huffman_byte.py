"""Archive and recheck cached-byte CPU, standalone capacity and full Fuse evidence."""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from summarize_partial_slots import pipeline
from summarize_uncontended_frame import metrics


def summarize(cpu, build, generic, old, new):
    if not all(x['complete'] for x in (cpu,build,generic)) or cpu['checked_frames'] != 4221:
        raise ValueError('complete CPU, build and generic checks required')
    if not cpu['full_compact_and_both_native_exact'] or not all(c['complete'] for g in generic['cases'] for c in g['cpu']):
        raise ValueError('image checks incomplete')
    volumes = []
    for c,b,before,after in zip(cpu['volumes'],build['volumes'],old,new):
        count = c['end']-c['start']
        if b['raw_sha256'] != c['raw_sha256'] or not b['compressed_stream_exact'] or not b['independently_bootable']:
            raise ValueError('different source or dependent disk')
        if b['used_sectors'] > 2544 or b['used_sectors'] != b['baseline_used_sectors']:
            raise ValueError('capacity/sector count regressed')
        for r, expected_sha in ((before,b['baseline_trd_sha256']), (after,b['trd_sha256'])):
            if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact']
                    or not r['ay_records_exact'] or r['frames'] != count or r['trd_sha256'] != expected_sha
                    or r['partial_slot_consumption'] or not r['compiled_masks']
                    or r['runtime_sectors_checked'] != b['video_sectors'] or r['fast_read_retries']):
                raise ValueError('incomplete or different Fuse experiment')
        cached = after['cached_huffman_byte']
        if not cached['in_bootstrap'] or cached['code_sha256'] != c['code_sha256']:
            raise ValueError('different cached reconstruction code')
        volumes.append(dict(part=b['part'],frames=count,used_sectors=b['used_sectors'],
            video_bytes=b['video_bytes'],baseline_cpu_tstates=c['baseline_tstates'],
            cpu_tstates=c['tstates'],cpu_delta_tstates=c['delta_tstates'],
            baseline=dict(metrics=metrics(before),pipeline=pipeline(before,c['start'])),
            cached=dict(metrics=metrics(after),pipeline=pipeline(after,c['start']))))
    if len(volumes) != 3 or sum(v['frames'] for v in volumes) != 4221:
        raise ValueError('partial movie')
    names = ('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors',
             'read_service_tstates','seek_service_tstates','publication_span_tstates')
    totals = {mode:{name:sum(v[mode]['metrics'][name] for v in volumes) for name in names}
              for mode in ('baseline','cached')}
    for mode in totals:
        totals[mode].update({name:sum(v[mode]['pipeline'][name] for v in volumes)
                            for name in ('packet_tstates','synchronous_waits','wait_tstates')})
    return dict(complete=True,release=False,volumes=volumes,totals=totals,
        cpu_baseline_tstates=cpu['baseline_tstates'],cpu_tstates=cpu['tstates'],
        cpu_delta_tstates=cpu['delta_tstates'],slower_cpu_frames=cpu['slower_frames'],
        compressed_streams_unchanged=True,new_cached_bootstrap_capacity_verified=True,
        queue_and_masks_still_debugger_fixture=True,full_compact_and_native_cpu_comparison=True,
        fuse_samples_per_frame=80,full_fuse_pixel_comparison=False,physical_drive_verified=False,
        initial_disk_and_irq_phases_not_matched=True,
        nominal_schedule_met=all(v['cached']['metrics']['nominal_late_frames']==0 and
            v['cached']['metrics']['max_actual_deviation_tstates']<=64 for v in volumes),
        fallback_met=all(v['cached']['metrics']['actual_out_over_one_field']==0 and
            v['cached']['metrics']['bad_actual_intervals']==0 for v in volumes),
        ay_schedule_met=all(v['cached']['metrics']['audio_underruns']==0 for v in volumes))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fresh',type=Path,help='archive fresh partNN.json and raw traces; omit to verify archive')
    p.add_argument('--evidence',type=Path,default=Path('toolkit/cached_huffman_byte_evidence'))
    p.add_argument('--baseline',type=Path,default=Path('toolkit/partial_slots_evidence'))
    p.add_argument('--output',type=Path,default=Path('toolkit/cached_huffman_byte_summary.json'))
    args = p.parse_args()
    inputs = {name:Path(f'toolkit/cached_huffman_byte_{name}.json') for name in ('cpu','build','generic')}
    old_paths = [args.baseline/f'baseline-part{part:02}.json' for part in (1,2,3)]
    files = []
    if args.fresh:
        args.evidence.mkdir(parents=True,exist_ok=True)
        for part in (1,2,3):
            source = args.fresh/f'part{part:02}.json'
            blob = source.read_bytes();r = json.loads(blob)
            target = args.evidence/source.name
            target.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
            files.append(dict(file=target.name,sha256=sha(target.read_bytes())))
            for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
                blob = source.with_suffix(suffix).read_bytes()
                if sha(blob) != r[key]: raise ValueError('raw trace hash differs')
                target = args.evidence/(source.stem+suffix+'.gz')
                target.write_bytes(gzip.compress(blob,mtime=0))
                files.append(dict(file=target.name,sha256=sha(target.read_bytes()),uncompressed_sha256=sha(blob)))
    else:
        saved = json.loads(args.output.read_bytes());files = saved['evidence']
    for item in files:
        blob = (args.evidence/item['file']).read_bytes()
        if sha(blob) != item['sha256']: raise ValueError('archive changed')
        if 'uncompressed_sha256' in item and sha(gzip.decompress(blob)) != item['uncompressed_sha256']:
            raise ValueError('uncompressed trace differs')
    result = summarize(*(json.loads(path.read_bytes()) for path in inputs.values()),
        [json.loads(path.read_bytes()) for path in old_paths],
        [json.loads((args.evidence/f'part{part:02}.json').read_bytes()) for part in (1,2,3)])
    result.update(input_sha256={k:sha(v.read_bytes()) for k,v in inputs.items()},
                  baseline_report_sha256=[sha(path.read_bytes()) for path in old_paths],evidence=files)
    if args.fresh:
        args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    elif saved != json.loads(json.dumps(result)):
        raise ValueError('derived results or input hashes changed')
    print(json.dumps({k:v for k,v in result.items() if k not in ('volumes','evidence')},indent=2))


if __name__ == '__main__':
    main()
