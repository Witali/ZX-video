"""Archive complete FAP3 interleaving measurements against cached linear reads."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from summarize_fap3_cached_seek import summary,read


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','baseline','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); args.output.mkdir(parents=True,exist_ok=True); rows=[]
    for part in range(1,5):
        stem=f'ZX-video-optimized-preview_part{part:02}'
        meta=read(args.build/(stem+'.json'))
        current=read(args.build/f'fuse_part{part:02}.json')
        previous=read(args.baseline/f'warm_part{part:02}.json')
        old_meta=read(args.baseline/f'warm_metadata_part{part:02}.json')
        assert meta['trd_sha256']==current['trd_sha256']==hashlib.sha256((args.build/(stem+'.trd')).read_bytes()).hexdigest()
        assert current['complete'] and not current['errors'] and current['interleaved']
        for key in ('frame_start','frame_end_exclusive','raw_sha256','states_sha256','video_bytes','video_sectors'):
            assert meta[key]==old_meta[key],key
        rows.append(dict(part=part,previous=summary(previous),current=summary(current),
            layout_padding_sectors=meta['layout_padding_sectors'],used_sectors=meta['used_sectors'],
            previous_used_sectors=old_meta['used_sectors']))
        shutil.copyfile(args.build/(stem+'.json'),args.output/f'part{part:02}.json')
        shutil.copyfile(args.build/f'fuse_part{part:02}.json',args.output/f'fuse_part{part:02}.json')
    for name in ('cpu.json','layout_checks.json','swap_checks.json','prompt_fuse.json'):
        shutil.copyfile(args.build/name,args.output/name)
    report=dict(baseline_commit='5ddc5a0',status='interleaving verified; cadence FAILED',release=False,
        frames=4221,ay_records=25326,pixel_changes=False,ay_changes=False,full_pixel_comparison=False,
        pixel_samples_per_frame=80,physical_drive_verified=False,volumes=rows)
    (args.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__': main()
