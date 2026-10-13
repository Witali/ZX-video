"""Authenticate complete cold auditions, archive their evidence and report."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import wave

HERE=Path(__file__).resolve().parent
CORE=HERE.parents[1]


def sha(data): return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('--node',required=True)
    args=parser.parse_args()
    root=args.build
    report=json.loads((root/'report.json').read_bytes())
    norm=report['input_normalization']
    assert norm['applied_before_analysis']
    assert norm['target_peak_dbfs']==-1 and norm['clipping_samples']==0
    if norm['source_peak']:
        assert abs(norm['normalized_peak']-10**(-1/20))<1e-12
    raw=gzip.decompress((root/'registers.gz').read_bytes())
    width=report['register_bytes_per_state'];state_bytes=report['packed_state_bytes']
    packed=gzip.decompress((root/report['packed_filename']).read_bytes())
    assert report['ticks']==15000 and len(raw)==15000*width and len(packed)==15000*state_bytes
    assert sha(raw)==report['registers_sha256'] and sha(packed)==report['packed_sha256']
    proofs=[]; joined=[]
    for item in report['parts']:
        number=item['number'];ticks=item['end_tick']-item['start_tick']
        part=root/f'part{number:02d}'
        proof=json.loads((part/'verification.json').read_bytes())
        assert proof['complete'] and proof['native']['complete'] and proof['native']['registers_exact']
        fuse=proof['fuse']
        assert fuse['complete'] and fuse['cold_boot'] and fuse['every_register_exact']
        part_raw=gzip.decompress((part/'registers.gz').read_bytes())
        writes=ticks*13+sum(part_raw[t*width+13]!=255 for t in range(ticks)) if width==14 else ticks*11
        assert fuse['ticks']==ticks and fuse['register_writes']==writes
        assert not fuse['missing_or_duplicate_fields'] and fuse['runtime_disk_reads']==0
        assert fuse['recording']['complete'] and fuse['recording']['cycles']==1
        assert sha((part/'audio-preview.trd').read_bytes())==fuse['trd_sha256']
        joined.append(part_raw)
        proofs.append(dict(number=number,native=proof['native'],fuse=fuse))
    assert b''.join(joined)==raw
    for name,rate in (('ay-preview.wav',44100),('original-preview.wav',22050)):
        with wave.open(str(root/name),'rb') as audio:
            assert audio.getframerate()==rate and audio.getnframes()==300*rate
    report.update(all_disks_fuse_verified=True,verification=proofs,
        native_ticks_verified=sum(p['native']['ticks'] for p in proofs),
        fuse_ticks_verified=sum(p['fuse']['ticks'] for p in proofs),
        fuse_register_writes_verified=sum(p['fuse']['register_writes'] for p in proofs),
        python_version=sys.version,node_version=subprocess.check_output([args.node,'--version']).decode().strip())
    import numpy as np
    report['numpy_version']=np.__version__
    toolkit=CORE.parent/'toolkit'
    sources=[*sorted(CORE.glob('*.py')),*sorted(CORE.glob('*.js')),CORE/'ay-player.asm',CORE/'vendor/ayumi-js/ayumi.js',
             *sorted(HERE.glob('*.py')),*sorted(HERE.glob('*.js')),
             *(toolkit/name for name in ('ay_huffman_stream.py','ay_interrupt.py','resident_audio_z80.py',
                'fixed_resident_audio.py','convert_video.py','convert_cb41.py','video_cadence.py','cell_audio_stream.py','build_fap3_trd.py',
                'fap3_disk_z80.py','measure_cell_codebook_movie.py'))]
    report['producer_sources_sha256_lf']={p.relative_to(CORE.parent).as_posix():sha(p.read_bytes().replace(b'\r\n',b'\n')) for p in sources}
    report['baseline_commit']='e7450386'
    report['date']='2026-10-13'
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    target=HERE/'evidence'
    shutil.copytree(root,target,dirs_exist_ok=True)
    logs={'build.log':'bbb-compact-final-build.log','initial-normalized-build.log':'bbb-five-minute-normalized.log',
          **{f'part{i:02d}-verification.log':f'bbb-compact-part{i:02d}-verify.log' for i in range(1,len(proofs)+1)},
          'compressed-fit.log':'bbb-compact-fit.log','short-note-recovery.log':'bbb-compact-combined.log',
          'superseded-recovery-only.log':'bbb-compact-recovered.log',
          'ay-model-feedback.log':'bbb-ay-final-fit.log','ay-final-feedback.log':'bbb-ay-polished.log',
          'superseded-ym-envelope-fit.log':'bbb-envelope-fit.log','superseded-ym-envelope-ramps.log':'bbb-envelope-combined.log',
          'interrupted-render-only.log':'bbb-five-minute-auto-build.log',
          'interrupted-column-pool.log':'bbb-five-minute-auto-parallel.log',
          'interrupted-bounded-full-search.log':'bbb-five-minute-final.log',
          'superseded-unnormalized-build.log':'bbb-five-minute-shortlist.log'}
    for destination,name in logs.items():
        shutil.copyfile(root.parent/name,target/destination)
    if report.get('resumed_complete_noise_stage'):
        shutil.copyfile(root.parent/'bbb-complete-noise.json',target/'resume-noise.json')
    shutil.copyfile(root.parent/'bbb-five-minute-shortlist/report.json',target/'superseded-unnormalized-host-report.json')
    shortlist=json.loads((root.parent/'bbb-shortlist-check/report.json').read_bytes())
    assert shortlist['complete'] and len(shortlist['cases'])==5
    assert all(x['shortlist_error_db']<=x['seed_error_db'] for x in shortlist['cases'].values())
    shutil.copytree(root.parent/'bbb-shortlist-check',target/'shortlist-validation',dirs_exist_ok=True)
    shutil.copyfile(root.parent/'bbb-shortlist-check.log',target/'shortlist-validation/run.log')
    feedback=json.loads((root.parent/'bbb-feedback-check/report.json').read_bytes())
    assert feedback['complete'] and len(feedback['cases'])==5
    assert all(x['after']['objective_db']<=x['before']['objective_db'] for x in feedback['cases'].values())
    shutil.copytree(root.parent/'bbb-feedback-check',target/'feedback-validation',dirs_exist_ok=True)
    shutil.copyfile(root.parent/'bbb-feedback-check.log',target/'feedback-validation/run.log')
    for name in ('bbb-final-audio-tests.log','bbb-final-toolkit-tests.log','bbb-final-recovery-tests.log','bbb-chip-selection-tests.log',
                 'bbb-dynamics-tests.log','bbb-dynamics-parity-tests.log','bbb-chip-capabilities.log',
                 'bbb-final-movie-fixture.log','bbb-final-movie-current.log'):
        shutil.copyfile(root.parent/name,target/name)
    for name in ('source-processing.json','stage-report.json','final-feedback.json'):
        shutil.copyfile(root.parent/'bbb-compact-fit'/name,target/f'initial-compressed-{name}')
    for name in ('bbb-envelope-first-failed-trace.txt.gz','bbb-envelope-first-failed-trace.json'):
        if (root.parent/name).exists():shutil.copyfile(root.parent/name,target/name)
    shutil.copytree(root.parent/'bbb-final-movie-fixture',target/'public-movie-fixture',dirs_exist_ok=True)
    seed=target/'seed-normalized';seed.mkdir(exist_ok=True)
    for name in ('report.json','registers.gz','channel-states.json.gz','note-events.json','input-normalization.json',
                 'noise-fit.json.gz','mixer-fit.json.gz','scheduling-check.json','objective-check.json'):
        shutil.copyfile(root.parent/'bbb-five-minute-normalized'/name,seed/name)
    files={p.relative_to(target).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
           for p in sorted(target.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    (target/'manifest.json').write_text(json.dumps(dict(date=report['date'],files=files),indent=2)+'\n',encoding='utf-8',newline='\n')
    for name,expected in files.items():
        data=(target/name).read_bytes()
        assert len(data)==expected['bytes'] and sha(data)==expected['sha256'],name
    print(json.dumps(dict(complete=True,seconds=300,ticks=15000,disks=len(proofs),
                         fuse_register_writes=report['fuse_register_writes_verified'],archived_files=len(files),archive_bytes=sum(x['bytes'] for x in files.values()))))


if __name__=='__main__': main()
