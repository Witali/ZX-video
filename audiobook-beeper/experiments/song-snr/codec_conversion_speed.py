"""Compare complete conversions with controlled old and optimized C engines.

Both runs use the current frontend, original prepared song/cover, identical
search and player options, quality rendering and artifact I/O. The control
forces Python model preparation and the frozen878c578e standalone C source;
the candidate uses the normal public converter. No existing output is changed.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
AUDIO=HERE.parents[1]
for folder in (AUDIO,HERE,AUDIO.parent/'toolkit'):
    sys.path.insert(0,str(folder))


def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def worker(args):
    import convert_snr_audio as converter
    import native_waveform_encoder as native
    from unittest.mock import patch
    prepare=converter.prepare_waveform
    overrides=[]
    if args.worker=='baseline':
        def original_prepare(source,times,model,**kwargs):
            return prepare(source,times,model,backend='python')
        execute=converter.execute_workset
        def original_execute(workset,output,statistics):
            with patch.object(native,'build_executable',return_value=args.baseline_exe):
                packed=execute(workset,output,statistics)
            statistics['native_source_sha256']=args.baseline_source_sha256
            return packed
        overrides=[patch.object(converter,'prepare_waveform',original_prepare),
                   patch.object(converter,'execute_workset',original_execute)]
    from contextlib import ExitStack
    with ExitStack() as stack:
        for override in overrides:stack.enter_context(override)
        report=converter.convert(HERE/'evidence/general/inputs/sea_foam.wav',args.output,
            prepared_pcm=True,encoder='c',cover=args.cover,ffmpeg=args.ffmpeg,
            audio_progress_ui=True,started=converter.PROCESS_STARTED)
    if args.worker=='baseline':
        report['model_preparation_backend']='python'
        report['controlled_baseline_intervention']='Current frontend with Python preparation and frozen878c578e C executable; native_source_sha256 identifies the actual executed translation unit'
        save(args.output/'conversion.json',report)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--scratch',required=True,type=Path)
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    p.add_argument('--reference-trd',type=Path,default=AUDIO.parents[2]/'ZX-music-Sea-Foam-SNR20-RAM-auto.trd')
    p.add_argument('--worker',choices=('baseline','optimized'))
    p.add_argument('--cover',type=Path)
    p.add_argument('--baseline-exe',type=Path)
    p.add_argument('--baseline-source-sha256')
    args=p.parse_args()
    if args.worker:return worker(args)
    if not args.ffmpeg:raise ValueError('FFmpeg is required for complete conversion timing')
    out=args.output.resolve();scratch=args.scratch.resolve()
    for folder in (out,scratch):
        if folder.exists() and any(folder.iterdir()):raise ValueError('Preserve existing output: '+str(folder))
        folder.mkdir(parents=True,exist_ok=True)
    disk=args.reference_trd.read_bytes()
    assert sha(disk)=='b96763cad15810d8d1755870f5a02ee2bfa1a708e787921fadf581f654a9e28e'
    entry=next(disk[at:at+16] for at in range(0,2048,16) if disk[at:at+8].rstrip()==b'COVER')
    size=int.from_bytes(entry[11:13],'little');sector=entry[14]+16*entry[15]
    cover=scratch/'cover.scr';cover.write_bytes(disk[sector*256:sector*256+size]);assert size==6912
    baseline=gzip.decompress((HERE/'evidence/codec-speed-profile/variants/baseline.c.gz').read_bytes())
    build=scratch/'baseline-build';build.mkdir();(build/'kernel.c').write_bytes(baseline)
    import waveform_kernel
    import native_waveform_encoder as native
    import native_waveform_prepare as preparation
    import native_ima_encoder
    command=waveform_kernel._command().replace('/LD /MT','/DNWF_STANDALONE /MT').replace('/OUT:kernel.dll','/OUT:kernel.exe')
    compiled=subprocess.run(command,cwd=build,capture_output=True,creationflags=0x08000000)
    (out/'baseline-build.log').write_bytes(compiled.stdout+compiled.stderr)
    if compiled.returncode:raise RuntimeError('Baseline build failed')
    (out/'baseline.c.gz').write_bytes(gzip.compress(baseline,mtime=0))
    save(out/'baseline-build.json',dict(command=command,source_sha256=sha(baseline),
        executable_sha256=sha((build/'kernel.exe').read_bytes()),
        reference_TRD_sha256=sha(disk),cover_sha256=sha(cover.read_bytes())))
    # Exclude compilation from this warm paired comparison, without claiming
    # that it is absent from a real first invocation of the public converter.
    native._load();native.build_executable();preparation._load()
    native_ima_encoder._load()
    rows=[];artifacts={}
    for engine in ('baseline','optimized'):
        dest=scratch/engine
        command=[sys.executable,str(Path(__file__).resolve()),'--worker',engine,
            '--output',str(dest),'--scratch',str(scratch),'--cover',str(cover),
            '--ffmpeg',str(args.ffmpeg),'--baseline-exe',str(build/'kernel.exe'),
            '--baseline-source-sha256',sha(baseline)]
        started=time.perf_counter();result=subprocess.run(command,capture_output=True,creationflags=0x08000000)
        elapsed=time.perf_counter()-started
        (out/(engine+'.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(engine+' failed; preserve log')
        report=json.loads((dest/'conversion.json').read_bytes())
        save(out/(engine+'.json'),report)
        artifacts[engine]={path.name:dict(bytes=path.stat().st_size,sha256=sha(path.read_bytes()))
            for path in dest.iterdir() if path.is_file()}
        rows.append(dict(engine=engine,external_complete_process_seconds=elapsed,
            timings=report['timings'],packed_sha256=report['packed_sha256'],trd_sha256=report['trd_sha256']))
        print(json.dumps(rows[-1]),flush=True)
    for name in ('audio.trd','soundtrack.ima.gz','baseline.ima.gz','source-preview.wav',
                 'compensated-pcm.wav','cover.scr','host-actual.wav','reference.wav','baseline-actual.wav'):
        if name in artifacts['baseline'] or name in artifacts['optimized']:
            assert artifacts['baseline'][name]==artifacts['optimized'][name],name
    assert rows[0]['trd_sha256']==rows[1]['trd_sha256']==sha(disk)
    save(out/'artifacts.json',artifacts)
    save(out/'report.json',dict(complete=True,rows=rows,
        old_and_new_TRD_identical_to_delivered_disk=True,format_changed=False,
        exact_player_hot_path_delta_tstates=0,
        ratio=rows[0]['external_complete_process_seconds']/rows[1]['external_complete_process_seconds'],
        warm_compiler_cache=True,optional_full_Fuse_repeated=False,
        scope='One sequential paired full public conversion, including imports, preparation, C search, guards, baseline encoding, TRD assembly, filtering, previews, file I/O and cleanup; current frontend with explicit old-engine intervention'))
    snapshots=out/'producer-source';snapshots.mkdir()
    import convert_snr_audio as converter
    for name in (*converter.PRODUCERS,'experiments/song-snr/codec_conversion_speed.py'):
        (snapshots/(name.replace('/','__')+'.gz')).write_bytes(gzip.compress((AUDIO/name).read_bytes(),mtime=0))
    (out/'script.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(),mtime=0))
    (out/'README.md').write_text('''# Complete public conversion speed comparison

Measured on 2026-10-20: one sequential warm-cache pair, including process/import overhead, complete prepared song, model preparation, C encoding, guard validation, baseline encoding, TRD assembly, quality filtering, previews, file I/O and temporary cleanup. The control uses the current frontend with explicitly overridden original Python preparation and frozen878c578e standalone C search; it is not a claim that the entire frontend came from the old commit. Both actual engine sources are identified and the old complete translation unit/build command is retained.

All audio payloads, source/prior/preview WAVs and entire bootable TRDs must be byte-identical. Both TRDs reproduce the delivered b96763ca disk with its original cover and loading/playback UI. The source is all720,384 original PCM8 samples; no excerpt or new search preset is used. No player instruction changes, new SNR claim, repeated full-song Fuse run or physical-hardware claim is involved. A single fixed-order pair is an observation, not a robust timing guarantee. See report.json and both complete conversion reports for phase times; compiler caches are warm, and first-build cost is excluded from this pair.

Reproduce using codec_conversion_speed.py with --output NEW_EMPTY_DIRECTORY --scratch NEW_EMPTY_DIRECTORY --ffmpeg PATH --reference-trd PATH. The referenced existing disk is authenticated before its cover is extracted; it is never overwritten. Existing outputs are rejected. Source snapshots and the artifact index preserve the completed measurement.
''',encoding='utf-8')
    save(out/'manifest.json',dict(complete=True,files=[dict(path=path.relative_to(out).as_posix(),
        bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for path in sorted(out.rglob('*')) if path.is_file() and path.name!='manifest.json']))


if __name__=='__main__':main()
