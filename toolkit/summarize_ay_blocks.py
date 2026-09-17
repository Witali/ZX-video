"""Compare measured block partitions without conflating CPU and disk timing."""
import argparse
import hashlib
import json
from pathlib import Path

from summarize_ay_delivery import summarize


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(build):
    meta_path=build/'build_metadata.json'; timing_path=build/'fuse_timing.json'
    meta=json.loads(meta_path.read_text());timing=json.loads(timing_path.read_text())
    if len(meta['volumes'])!=len(timing):raise ValueError('missing volume trace')
    for volume,trace in zip(meta['volumes'],timing):
        if volume['frames']!=trace['frames']:raise ValueError('frame count differs')
    result=dict(build=build.name,block_bytes=meta['block_codec'].get('encoder_block_limit',8192),
        metadata_sha256=sha(meta_path),timing_sha256=sha(timing_path),
        player_sha256=sha(build/'PLAYER.C.bin'),player_bytes=(build/'PLAYER.C.bin').stat().st_size,
        blocks=sum(len(v['blocks']) for v in meta['volumes']),
        physical_video_sectors=sum(v['physical_video_sectors'] for v in meta['volumes']),
        disks=[dict(name=v['trd_name'],sha256=sha(build/v['trd_name']),
                    frame_start=v['frame_start'],frame_end=v['frame_end'],
                    physical_video_sectors=v['physical_video_sectors']) for v in meta['volumes']],
        delivery=summarize(meta,timing),
        rom=[dict(mean_ms=t['rom_call_mean_ms'],max_ms=t['rom_call_max_ms'],
                  scope=t['note']) for t in timing])
    cpu_path=build/'cpu_validation.json'
    if cpu_path.exists():
        cpu=json.loads(cpu_path.read_text())
        if cpu['frames']!=meta['frames']:raise ValueError('incomplete screen validation')
        if all('verified_audio_ticks' in v for v in cpu['volumes']) and sum(v['verified_audio_ticks'] for v in cpu['volumes'])!=meta['frames']*6:
            raise ValueError('incomplete audio validation')
        if any(v['underflows'] for v in cpu['volumes']):raise ValueError('ring underflow')
        result['cpu']={key:value for key,value in cpu.items() if key!='volumes'}
        result['cpu']['measurement_sha256']=sha(cpu_path)
        queues=[v['minimum_live_queue_before_flip'] for v in cpu['volumes'] if v['minimum_live_queue_before_flip'] is not None]
        result['cpu']['minimum_live_queue_before_flip']=min(queues,default=None)
        result['cpu']['minimum_sp']=min(v['minimum_sp'] for v in cpu['volumes'])
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('builds',type=Path,nargs='+',help='baseline first')
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    results=[describe(build) for build in args.builds];baseline=results[0]
    for result in results:
        result['identical_player']=result['player_sha256']==baseline['player_sha256']
        result['sector_delta']=result['physical_video_sectors']-baseline['physical_video_sectors']
        if 'cpu' in result and 'cpu' in baseline:
            result['cpu_mean_deltas']={key:result['cpu'][key]-baseline['cpu'][key] for key in
                ('delivery_tstates_mean','background_preparation_tstates_mean','combined_preparation_tstates_mean')}
    report=dict(note='Same decoder instruction paths, different data and scheduling. CPU excludes IRQ/ULA/ROM/disk; Fuse includes them. Disk change gaps are excluded from per-volume intervals.',variants=results)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([dict(build=r['build'],block_bytes=r['block_bytes'],sectors=r['physical_video_sectors'],
        identical_player=r['identical_player'],max_ms=max(v['maximum_ms'] for v in r['delivery']['volumes']),
        late=r['delivery']['intervals_over_125ms'],cpu_mean_deltas=r.get('cpu_mean_deltas')) for r in results],indent=2))


if __name__=='__main__':main()
