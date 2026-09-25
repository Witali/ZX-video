"""Compare complete same-partition disk trials and preserve every timing event."""
import argparse
import json
from pathlib import Path
import disk_layout
from build_fap3_trd import sha
from profile_fap3 import summarize_fuse
from summarize_irq_safe import missing_fields
from summarize_volume_huffman import actual_runs


def read(path): return json.loads(path.read_bytes())


def logical(directory, part):
    path = directory/f'ZX-video-huffman-preview_part{part:02}.trd'
    meta = read(path.with_suffix('.json')); image = path.read_bytes()
    if sha(image) != meta['trd_sha256']: raise AssertionError('image hash differs')
    if not meta['independently_bootable'] or meta['used_sectors']>2544: raise AssertionError('disk does not fit or needs prior RAM')
    first = meta['video_start_sector']
    offsets = disk_layout.positions(meta['video_sectors'],first%16)
    data = b''.join(image[(first+n)*256:(first+n+1)*256] for n in offsets)
    return data,meta


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('directory','baseline-directory','evidence','output','cpu','generic'):
        p.add_argument('--'+name,type=Path,required=True)
    args = p.parse_args(); rows = []; archive = []
    args.evidence.mkdir(parents=True,exist_ok=True)
    for part in (1,2,3):
        new,meta = logical(args.directory,part)
        old,previous = logical(args.baseline_directory,part)
        if not meta.get('static_cache_borders') or previous.get('static_cache_borders',False):
            raise AssertionError('wrong experiment options')
        if new!=old or any(meta[k]!=previous[k] for k in ('frame_start','frame_end_exclusive','raw_sha256','states_sha256')):
            raise AssertionError('partition or logical stream differs')
        pair = []
        for directory in (args.baseline_directory,args.directory):
            data = read(directory/f'fuse_part{part:02}.json')
            expected = previous if directory==args.baseline_directory else meta
            if (not data['complete'] or data['errors'] or not data['ay_records_exact']
                    or data['frames']!=expected['frames'] or data['ay_ticks']!=6*data['frames']
                    or data['trd_sha256']!=expected['trd_sha256']): raise AssertionError('incomplete trace')
            timing = summarize_fuse(data)
            runs = actual_runs(data['actual_phase_tstates'])
            timing.update(actual_runs=runs,recovered_actual_runs=sum(r['recovered_at'] is not None for r in runs),
                unrecovered_actual_runs=sum(r['recovered_at'] is None for r in runs),
                unobserved_irq_fields=len(missing_fields(data)),empty_queue_visits=data['audio_underruns'],
                actual_fps=(len(data['publications'])-1)*3546900/(data['publications'][-1]['tstate']-data['publications'][0]['tstate']),
                playback_seconds=data['elapsed_timing']['playback_tstates']/3546900,
                max_actual_deviation_seconds=timing['maximum_deviation_tstates']/3546900)
            pair.append(timing)
        target = args.evidence/f'fuse_part{part:02}.json'
        saved = (json.dumps(data,separators=(',',':'))+'\n').encode(); target.write_bytes(saved)
        archive.append(dict(file=target.name,sha256=sha(saved),frames=data['frames'],ay_ticks=data['ay_ticks'],
            checked_runtime_sectors=data['runtime_sectors_checked'],trd_sha256=meta['trd_sha256']))
        rows.append(dict(part=part,frames=meta['frames'],used_sectors=meta['used_sectors'],
            baseline_used_sectors=previous['used_sectors'],logical_bytes=meta['video_bytes'],
            logical_sha256=sha(new[:meta['video_bytes']]),logical_stream_exact=True,
            baseline=pair[0],optimized=pair[1]))
    cpu,generic = read(args.cpu),read(args.generic)
    if not cpu['complete'] or not generic['complete'] or sum(v['frames'] for v in rows)!=cpu['checked_frames']:
        raise AssertionError('partial comparison')
    before = read(Path(__file__).with_name('combined_delivery_generic.json'))
    sig = lambda report:[(v['source'],v['frames'],v['stream_sha256']) for v in report['cases']]
    if sig(before)!=sig(generic): raise AssertionError('generic FAP3 changed')
    if not all(c['timing']['complete'] and all(x['complete'] and x['full_compact_and_native_comparison'] for x in c['cpu'])
               for c in generic['cases']): raise AssertionError('partial generic verification')
    result = dict(complete=True,release=False,baseline_commit='6e724f4',
        full_movie_stage_pixel_comparison=True,full_movie_fuse_pixel_comparison=False,
        full_stage_entropy_scope='Volume-1 Huffman tables across all 4221 unchanged states; runtime disk tables differ per volume.',
        fuse_pixel_samples_per_frame=80,physical_drive_verified=False,volumes=rows,
        frames=sum(v['frames'] for v in rows),ay_ticks=sum(v['ay_ticks'] for v in archive),
        runtime_sectors=sum(v['checked_runtime_sectors'] for v in archive),
        cpu_delta_tstates=cpu['delta_tstates'],generic_streams_exact=True)
    for key in ('baseline','optimized'):
        result[key] = {name:sum(v[key][name] for v in rows) for name in
            ('missed_nominal_frames','ay_missing_fields','playback_seconds','empty_queue_visits','unobserved_irq_fields')}
    result['playback_delta_seconds']=result['optimized']['playback_seconds']-result['baseline']['playback_seconds']
    (args.evidence/'index.json').write_text(json.dumps(archive,indent=2)+'\n')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='volumes'},indent=2))


if __name__ == '__main__': main()
