"""Compare complete old/new runs and verify identical physical video sections."""
import argparse
import json
from pathlib import Path

from build_fap3_trd import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('baseline','candidate','baseline-disks','candidate-disks','cpu','output'):
        p.add_argument('--'+key,type=Path,required=True)
    args = p.parse_args()
    old,new,cpu = [json.loads(path.read_bytes()) for path in (args.baseline,args.candidate,args.cpu)]
    if not all(d['complete'] for d in (old,new,cpu)): raise ValueError('requires complete runs')
    if old['ends'] != new['ends'] or old['contract']['raw_sha256'] != new['contract']['raw_sha256']:
        raise ValueError('different source or boundaries')
    if any(len(d['variants'][0]['volumes']) != len(d['ends']) or
            sum(v['frames'] for v in d['variants'][0]['volumes']) != d['frames'] for d in (old,new)):
        raise ValueError('incomplete volume coverage')
    if cpu['checked_frames'] != new['frames'] or len(cpu['frames']) != new['frames']:
        raise ValueError('incomplete CPU coverage')
    rows = []
    for a,b in zip(old['variants'][0]['volumes'],new['variants'][0]['volumes']):
        if a['part'] != b['part'] or a['frames'] != b['frames']: raise ValueError('different volume')
        contents = [];metadata = []
        for directory,row in ((args.baseline_disks,a),(args.candidate_disks,b)):
            path = directory/f'ZX-video-huffman-preview_part{row["part"]:02}.trd'
            image = path.read_bytes();m = json.loads(path.with_suffix('.json').read_bytes())
            if sha(image) != row['trd_sha256'] or m['trd_sha256'] != row['trd_sha256']:
                raise ValueError('disk hash differs')
            at = m['video_start_sector']*256;size = m['video_physical_sectors']*256
            contents.append(image[at:at+size]);metadata.append(m)
        if contents[0] != contents[1]: raise AssertionError('physical video section changed')
        rows.append(dict(part=a['part'],frames=a['frames'],physical_video_byte_exact=True,
            video_physical_sha256=sha(contents[0]),video_bytes=b['video_bytes'],
            baseline_used_sectors=a['used_sectors'],used_sectors=b['used_sectors'],
            nominal_deadlines_met=b['timing']['nominal_deadlines_met'],
            fallback_one_field_met=b['timing']['fallback_one_field_met'],
            actual_ay_50hz=b['timing']['actual_ay_50hz'],
            **{key:dict(baseline=a['timing'][key],candidate=b['timing'][key],
                delta=b['timing'][key]-a['timing'][key]) for key in
                ('actual_fps','missed_nominal_frames','ay_missing_fields','runtime_disk_reads',
                 'disk_read_service_tstates','seek_service_tstates')}))
    report = dict(complete=True,release=False,scope=__doc__,volumes=rows,
        baseline_commit='491db7b',frames=sum(r['frames'] for r in rows),
        capacity_sectors=3*2544,used_sectors=sum(r['used_sectors'] for r in rows),
        baseline_used_sectors=sum(r['baseline_used_sectors'] for r in rows),
        all_independently_bootable=all(v['independently_bootable'] for v in new['variants'][0]['volumes']),
        code_bytes_delta=cpu['scanner_bytes']-cpu['baseline_scanner_bytes'],
        new_buffer_bytes=0,extra_stack_bytes=0,physical_drive_verified=False,
        deterministic_scanner=dict(baseline_tstates=cpu['baseline_scanner_tstates'],
            candidate_tstates=cpu['scanner_tstates'],delta_tstates=cpu['delta_tstates'],
            slower_frames=cpu['slower_frames'],max_extra_frame_tstates=cpu['max_extra_frame_tstates']),
        timing_note='CPU experiment excludes disk/ROM/IRQ/ULA; Fuse includes all. Do not subtract them as disk latency.')
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__ == '__main__': main()
