"""Archive cold/warm FAP3 cached-seek experiments with actual AY field gaps."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from summarize_fap3_fast_disk import metrics, read, HZ


def summary(report):
    result=metrics(report)
    result.update(ay_record_field_gaps=report['ay_record_field_gaps'],
        ay_record_field_duplicates=report['ay_record_field_duplicates'],
        seek_calls=len(report.get('seek_calls',[])),
        seek_window_seconds=sum(q['tstates'] for q in report.get('seek_calls',[]))/HZ)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','cold','warm','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for part in range(1,5):
        row=dict(part=part)
        for name,folder in (('baseline',args.baseline),('cold',args.cold),('warm',args.warm)):
            report=read(folder/f'fuse_part{part:02}.json')
            assert report['complete'] and not report['errors'] and report['ay_records_exact']
            row[name]=summary(report)
            shutil.copyfile(folder/f'fuse_part{part:02}.json',args.output/f'{name}_part{part:02}.json')
            if name!='baseline':
                stem=f'ZX-video-optimized-preview_part{part:02}'
                meta=read(folder/(stem+'.json'))
                assert hashlib.sha256((folder/(stem+'.trd')).read_bytes()).hexdigest()==meta['trd_sha256']==report['trd_sha256']
                assert meta['cached_seek'] and meta['fast_disk']
                reference=read(Path(__file__).parent/'fap3_fast_disk'/f'part{part:02}.json')
                for key in ('frame_start','frame_end_exclusive','video_bytes','used_sectors','raw_sha256','states_sha256'):
                    assert meta[key]==reference[key],key
                if name=='warm': assert row[name]['io']['trdos']['calls']==0
                shutil.copyfile(folder/(stem+'.json'),args.output/f'{name}_metadata_part{part:02}.json')
        rows.append(row)
    shutil.copyfile(args.cold/'cpu.json',args.output/'cpu.json')
    for name in ('swap_checks.json','prompt_fuse.json'):
        shutil.copyfile(args.warm/name,args.output/name)
    result=dict(baseline_commit='9db8954',status='cached seeks verified; cadence FAILED',release=False,
        frames=4221,ay_records=25326,pixel_changes=False,ay_changes=False,extra_stream_sectors=0,
        full_pixel_comparison=False,pixel_samples_per_frame=80,physical_drive_verified=False,
        io_window_scope='ROM + emulated disk + IRQ + contention; RAM CPU counted separately',
        ay_field_gaps_scope='Missing 50 Hz fields between first and last delivered records, from actual timestamps',
        volumes=rows)
    (args.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
