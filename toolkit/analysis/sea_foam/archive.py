"""Qualify and preserve the selected independently bootable sea-foam TRD."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import wave
import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path);parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--metadata',type=Path,required=True);parser.add_argument('--run-log',type=Path,required=True)
    parser.add_argument('--plan-log',type=Path,required=True);parser.add_argument('--download-log',type=Path,required=True)
    parser.add_argument('--bootstrap-tests',type=Path,required=True);parser.add_argument('--generic-tests',type=Path,required=True)
    parser.add_argument('--longer-build',type=Path,required=True);parser.add_argument('--longer-log',type=Path,required=True)
    args=parser.parse_args();root=args.build
    conversion=json.loads((root/'conversion.json').read_bytes());timing=json.loads((root/'timing.json').read_bytes())
    assert conversion['complete'] and conversion['timing_verified'] and conversion['independently_bootable']
    assert timing['complete'] and timing['all_nominal_deadlines_met']
    assert len(conversion['volumes'])==len(timing['disks'])==1
    volume=conversion['volumes'][0];proof=timing['disks'][0]
    assert proof['full_fuse_screens_exact'] and proof['cold']['dirty_ram_boot_exact']
    actual=proof['disk_timing']
    assert actual['complete'] and actual['nominal_deadlines_met'] and not actual['missed_nominal_frames']
    assert actual['actual_ay_50hz'] and not actual['ay_missing_fields']
    stem=Path(volume['file']).stem
    measured=json.loads((root/'work'/stem/'timing.json').read_bytes())
    assert measured['complete'] and measured['ay_records_exact'] and measured['ay_ticks']==conversion['ay_ticks']
    disk=(root/volume['file']).read_bytes();assert sha(disk)==volume['sha256']
    assert volume['used_sectors']<=2544 and len(disk)==655360
    plan=json.loads(args.plan.read_bytes());youtube=json.loads(args.metadata.read_bytes())
    source=Path(plan['source']);assert sha(source.read_bytes())==plan['source_sha256']
    target=HERE/'evidence'
    if target.exists():
        prior=json.loads((target/'qualification.json').read_bytes())
        if prior['trd_sha256']!=sha(disk):raise ValueError('refusing to replace a different archived disk')
    shutil.copytree(root,target,dirs_exist_ok=True)
    shutil.copyfile(args.plan,target/'prefix-plan.json')
    for name,path in (('conversion.log',args.run_log),('planning.log',args.plan_log),('download.log',args.download_log)):
        shutil.copyfile(path,target/name)
    shutil.copyfile(args.bootstrap_tests,target/'bootstrap-tests.log');shutil.copyfile(args.generic_tests,target/'generic-tests.log')
    before=target/'superseded-longer';before.mkdir(exist_ok=True)
    for name in ('conversion.json','partition.json'):
        shutil.copyfile(args.longer_build/name,before/name)
    shutil.copyfile(args.longer_log,before/'run.log')
    shutil.copyfile(args.longer_build/'work/audio-source.f32',target/'work/continuous-audio-fit/input.f32')
    def levels(path):
        with wave.open(str(path),'rb') as stream:
            assert stream.getframerate()==22050 and stream.getnchannels()==1 and stream.getsampwidth()==2
            samples=np.frombuffer(stream.readframes(stream.getnframes()),'<i2').astype(float)/32768
        return np.sqrt(np.mean(samples.reshape(-1,441)**2,axis=1))
    source_levels=levels(target/'work/processed-reference.wav');model_levels=levels(target/'work/audio-preview.wav')
    active=source_levels>10**(-45/20);shortfall=active&(model_levels<source_levels*10**(-15/20))
    level_report=dict(method='20-ms PCM16 RMS; reference above -45 dBFS and model more than 15 dB below reference',
        fields=len(source_levels),audible_reference_fields=int(active.sum()),strong_shortfall_fields=int(shortfall.sum()))
    (target/'level-check.json').write_text(json.dumps(level_report,indent=2)+'\n',encoding='utf-8',newline='\n')
    # Keep public identifiers, not ephemeral signed media URLs from yt-dlp.
    public={name:youtube.get(name) for name in ('id','title','duration','channel','webpage_url','upload_date')}
    public.update(downloaded_sha256=plan['source_sha256'],downloaded_bytes=source.stat().st_size,
        selected_source_interval_seconds=plan['source_interval_seconds'])
    (target/'source.json').write_text(json.dumps(public,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    producers=[*sorted((ROOT/'ay-converter').glob('*.py')),*sorted((ROOT/'ay-converter').glob('*.js')),
        ROOT/'ay-converter/vendor/ayumi-js/ayumi.js',*sorted((ROOT/'toolkit').glob('*.py')),*sorted(HERE.glob('*.py'))]
    result=dict(complete=True,release=True,date='2026-10-13',scope='Selected beginning-of-source excerpt only; complete native timing/content check, not the full cartoon or maximum-duration proof.',
        frames=conversion['frames'],ay_ticks=conversion['ay_ticks'],duration_seconds=conversion['duration_seconds'],
        disks=1,disk_file=volume['file'],trd_sha256=sha(disk),used_sectors=volume['used_sectors'],
        all_nominal_deadlines_met=True,missed_nominal_frames=0,maximum_deviation_tstates=actual['maximum_deviation_tstates'],
        full_fuse_screens_exact=True,every_ay_record_exact=True,actual_ay_50hz=True,independent_dirty_boot_exact=True,
        physical_hardware_tested=False,source=public,
        implementation='Existing guarded CB46 and shared real-AY engine, with complete AYH2 checkpoint restoration.',
        runtime_instruction_delta_tstates=0,startup_checkpoint_delta_tstates=255,
        checkpoint_restore_loop_tstates=dict(before_11=930,after_14=1185),
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
        producer_sources_sha256_lf={p.relative_to(ROOT).as_posix():sha(p.read_bytes().replace(b'\r\n',b'\n')) for p in producers})
    (target/'qualification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    files={p.relative_to(target).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in target.rglob('*') if p.is_file() and p!=target/'manifest.json'}
    (target/'manifest.json').write_text(json.dumps(dict(files=files),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,frames=result['frames'],seconds=result['duration_seconds'],disks=1,files=len(files))))


if __name__=='__main__':main()
