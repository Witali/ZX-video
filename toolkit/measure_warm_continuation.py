"""Full volumes in Fuse with actual retained EOF RAM carried across disk swaps.

The controller/emulator restarts between volumes; the RAM needed by the
continuation is not regenerated. This is not a physical drive swap test.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from build_fap3_trd import sha
from profile_fap3 import summarize_fuse
from warm_resume_snapshot import make_snapshot,verify_retained


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('volumes','fuse','raw','states','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--timeout',type=float,default=300)
    args=p.parse_args()
    records=json.loads((args.volumes/'volumes.json').read_text())
    with np.load(args.states,allow_pickle=False) as saved: states=saved['states']
    report=dict(complete=False,release=False,physical_drive_verified=False,
        snapshot_model='Spectrum 128',ram_from_actual_predecessor_eof=True,
        controller_state_preserved=False,full_pixel_comparison=False,volumes=[])
    args.report.parent.mkdir(parents=True,exist_ok=True)
    def save(): args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save(); previous=None
    for record in records:
        part=record['part']; target=args.volumes/f'fuse_part{part:02}.json'
        ramfile=args.volumes/f'eof_part{part:02}.ram'
        metadata=json.loads((args.volumes/record['metadata']).read_text())
        if not metadata.get('warm_continuation'): raise ValueError('requires a warm set')
        command=[sys.executable,str(Path(__file__).with_name('measure_fap3_fuse.py')),
            '--fuse',str(args.fuse.resolve()),'--trd',str((args.volumes/record['file']).resolve()),
            '--metadata',str((args.volumes/record['metadata']).resolve()),'--raw',str(args.raw.resolve()),
            '--states',str(args.states.resolve()),'--output',str(target.resolve()),
            '--export-warm-ram',str(ramfile.resolve()),'--timeout',str(args.timeout)]
        if previous is not None:
            snapshot=args.volumes/f'resume_part{part:02}.szx'
            snapshot.write_bytes(make_snapshot(previous))
            command+=['--continuation-snapshot',str(snapshot.resolve())]
        print(f'Full Fuse warm volume {part}',flush=True)
        subprocess.run(command,check=True)
        measured=json.loads(target.read_text())
        previous=ramfile.read_bytes()
        if sha(previous)!=measured['warm_ram_sha256']: raise AssertionError('RAM dump provenance differs')
        retained=verify_retained(previous,metadata,states)
        timing=summarize_fuse(measured)
        for key in ('missed_nominal_frame_indices','publication_intervals_tstates','late_runs'): timing.pop(key)
        pubs=measured['publications']
        timing.update(actual_fps=(len(pubs)-1)*3546900/(pubs[-1]['tstate']-pubs[0]['tstate']),
            recovered_late_runs=sum(r['recovered_at'] is not None for r in measured['late_runs']),
            unrecovered_late_runs=sum(r['recovered_at'] is None for r in measured['late_runs']))
        report['volumes'].append(dict(part=part,frames=metadata['frames'],used_sectors=metadata['used_sectors'],
            free_sectors=metadata['free_sectors'],trd_sha256=metadata['trd_sha256'],
            report_sha256=sha(target.read_bytes()),retained_ram=retained,
            continuation_accepted=bool(measured.get('continuation_disk_accepted_tstates')) if part>1 else None,
            timing=timing))
        save()
    report.update(complete=True,all_nominal_deadlines_met=all(r['timing']['nominal_deadlines_met'] for r in report['volumes']))
    save()


if __name__=='__main__':main()
