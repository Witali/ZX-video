"""Verify CB41 disk selection and actual predecessor-EOF continuation.

Mock mode exercises real prompt/bootstrap opcodes with ROM reads modeled.
Fuse mode carries actual EOF RAM through a snapshot, poisons other banks,
and measures the complete next volume. The emulator/controller restart;
this does not claim a physical floppy swap test or require retained RAM.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from build_fap3_trd import sha
from build_five_level_test_trd import save
from test_fap3_disk import verify_swaps
from warm_resume_snapshot import make_snapshot

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('build','fuse','raw','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--mode',choices=('mock','fuse'),required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    capacity = json.loads((a.build/'capacity.json').read_bytes())
    assert capacity['all_volumes_fit']
    volumes = capacity['volumes']
    if a.mode=='mock':
        stage = a.output/'mock'
        stage.mkdir(exist_ok=True)
        records = []
        for row in volumes:
            folder = a.build/f'volume-{row["volume"]}'
            image = folder/'candidate.trd'
            assert sha(image.read_bytes())==row['trd_sha256']
            name = f'part-{row["volume"]}.trd'
            shutil.copyfile(image,stage/name)
            shutil.copyfile(folder/'metadata.json',(stage/name).with_suffix('.json'))
            records.append(dict(part=row['volume'],file=name))
        save(stage/'volumes.json',records)
        verify_swaps(stage,a.output/'swaps.json')
        return
    records, previous = [], None
    for row in volumes:
        part = row['volume']
        folder = a.build/f'volume-{part}'
        target = a.output/f'part-{part}.json'
        command = [sys.executable,str(ROOT/'measure_fap3_fuse.py'),'--fuse',str(a.fuse.resolve()),
            '--trd',str((folder/'candidate.trd').resolve()),'--metadata',str((folder/'metadata.json').resolve()),
            '--states',str((folder/'states.npz').resolve()),'--raw',str(a.raw.resolve()),
            '--output',str(target.resolve()),'--timeout','180']
        if previous is not None:
            snapshot = a.output/f'resume-{part}.szx'
            snapshot.write_bytes(make_snapshot(previous))
            command += ['--continuation-snapshot',str(snapshot.resolve())]
        ram = a.output/f'eof-{part}.ram'
        if part<len(volumes):
            command += ['--export-warm-ram',str(ram.resolve())]
        result = subprocess.run(command,capture_output=True,text=True)
        (a.output/f'part-{part}.log').write_text(result.stdout+result.stderr,encoding='utf-8',newline='\n')
        if result.returncode:
            raise RuntimeError(f'continuation volume {part} failed; see {target} and its log')
        report = json.loads(target.read_bytes())
        assert report['complete'] and report['trd_sha256']==row['trd_sha256']
        if part<len(volumes):
            previous = ram.read_bytes()
            assert len(previous)==49152 and sha(previous)==report['warm_ram_sha256']
        pubs = report['publications']
        intervals = [b['tstate']-a['tstate'] for a,b in zip(pubs,pubs[1:])]
        assert len(pubs)==row['frames']
        records.append(dict(part=part,frames=row['frames'],complete=True,
            from_actual_previous_eof=part>1,trd_sha256=row['trd_sha256'],
            report_sha256=sha(target.read_bytes()),nominal_late_frames=report['nominal_late_frames'],
            ay_records_exact=report['ay_records_exact'],ay_ticks=report['ay_ticks'],
            ay_gaps=report['ay_record_field_gaps'],ay_duplicates=report['ay_record_field_duplicates'],
            audio_underruns=report['audio_underruns'],
            continuation_disk_accepted_tstates=report.get('continuation_disk_accepted_tstates'),
            actual_interval_tstates=[min(intervals),max(intervals)],
            actual_phase_tstates=[min(report['actual_phase_tstates']),max(report['actual_phase_tstates'])]))
        save(a.output/'continuation.json',dict(complete=part==len(volumes),release=False,
            scope=__doc__,volumes=records,physical_drive_swap_verified=False,
            controller_state_preserved=False,actual_predecessor_ram=True,
            independent_cold_boot_also_required=True,
            source_sha256_lf={name:sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n')) for name in (
                'verify_cell_codebook_continuation.py','warm_resume_snapshot.py','measure_fap3_fuse.py')}))
        print(json.dumps(records[-1]),flush=True)


if __name__=='__main__':
    main()
