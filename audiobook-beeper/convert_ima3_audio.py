"""One-command audio -> native packed IMA3 -> measured PDM TRD conversion.

Every quality decision uses both complete cold Fuse loops. Host estimates
only order the bounded encoder search; they never qualify a disk. --resume
reuses completed, hashed stages only when input, tools and producer match.
"""
import argparse
from datetime import date
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np
from build_ima3_direct import build_verified
from convert_audio import prepare_source, pcm_wav
from ima3_direct_player import MEASURED_MODEL, layout
from ima_beam import encode
from probe_reconstruction_error import wav8
from verify_pcm import save

HERE=Path(__file__).resolve().parent
SEARCH=((256,.03,128),(512,.03,128),(1024,.03,256))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage(path,operation):
    """Checkpoint complete results; preserve an interrupted attempt separately."""
    marker=path/'stage-complete.json'
    if marker.is_file():
        saved=json.loads(marker.read_bytes())
        for name,expected in saved.items():
            if digest(path/name)!=expected:
                raise ValueError(f'cached stage artifact changed: {path/name}')
        print(json.dumps(dict(reused_stage=str(path))),flush=True)
        return json.loads((path/'report.json').read_bytes())
    if path.exists():
        path.rename(path.with_name(path.name+f'.interrupted-{time.time_ns()}'))
    result=operation(path)
    files=list(path.glob('*'))+list((path/'assembly').glob('*'))
    save(marker,{str(p.relative_to(path)):digest(p) for p in files if p.is_file() and p!=marker})
    return result


def host_search(pilot,out,width,weight,block_size,ffmpeg):
    subprocess.run([sys.executable,str(HERE/'ima_waveform_encoder.py'),
                    '--input',str(pilot),'--output',str(out),'--ima3',
                    '--width',str(width),'--regularization',str(weight),
                    '--block-size',str(block_size),'--ffmpeg',ffmpeg],check=True)
    return json.loads((out/'report.json').read_bytes())


def reuse_pilot(path,old,source,identity):
    """Reuse exact evidence across PC-search changes, never across player changes."""
    old=old.resolve()
    if old==path.resolve():raise ValueError('pilot cache must be in a different completed run')
    if not (old/'stage-complete.json').is_file():raise ValueError('pilot cache is incomplete')
    previous=json.loads((old.parent/'run.json').read_bytes())
    for key in ('fuse_sha256','ffmpeg_sha256','model'):
        if previous[key]!=identity[key]:raise ValueError(f'pilot cache mismatch: {key}')
    # The converter and waveform encoder did not produce the initial PCM-IMA
    # pilot. Every other producer/verifier must match the saved run exactly.
    exempt={'convert_ima3_audio.py','ima_waveform_encoder.py'}
    for name,value in identity['producer_sha256'].items():
        if name not in exempt and previous['producer_sha256'].get(name)!=value:
            raise ValueError(f'pilot producer changed: {name}')
    if not np.array_equal(wav8(old/'source-preview.wav'),source):raise ValueError('pilot source differs')
    if (old/'assembly'/'player.asm').read_bytes()!=(HERE/'ima3-direct-player.asm').read_bytes():
        raise ValueError('pilot assembly differs')
    report=stage(old,lambda _: (_ for _ in ()).throw(ValueError('pilot cache is incomplete')))
    native=json.loads((old/'native.json').read_bytes());fuse=json.loads((old/'fuse.json').read_bytes())
    assert native['complete'] and fuse['complete'] and fuse['cycles_verified']==2
    assert fuse['every_pdm_bit_exact'] and fuse['every_predictor_and_index_exact']
    assert fuse['trd_sha256']==digest(old/'audiobook-preview.trd')
    shutil.copytree(old,path,ignore=shutil.ignore_patterns('verification-work','fuse-probe'))
    save(path/'reuse.json',dict(source=str(old),original_stage_sha256=digest(old/'stage-complete.json'),
                              exact_source_player_and_tools=True))
    return report


def convert(args):
    out=args.output.resolve();manifest=out/'run.json'
    producers={p.name:digest(p) for p in HERE.glob('*.py')}
    producers['ima3-direct-player.asm']=digest(HERE/'ima3-direct-player.asm')
    identity=dict(input_sha256=digest(args.input),prepared_pcm=args.prepared_pcm,
                  duration=args.duration,target_snr_db=args.target_snr,attempts=args.attempts,
                  recording=not args.no_recording,model=MEASURED_MODEL,producer_sha256=producers,
                  reuse_pilot=str(args.reuse_pilot.resolve()) if args.reuse_pilot else None,
                  fuse_sha256=digest(args.fuse),ffmpeg_sha256=digest(Path(args.ffmpeg)))
    if out.exists() and any(out.iterdir()):
        if not args.resume or not manifest.is_file():
            raise ValueError('output is not empty; use --resume only for this converter output')
        if json.loads(manifest.read_bytes())!=identity:
            raise ValueError('resume input, settings, tools or producer changed; choose a new output directory')
    else:
        out.mkdir(parents=True,exist_ok=True);save(manifest,identity)
    reserve=layout(bytes(256),MEASURED_MODEL)[-1]
    capacity=(5*16383+9471+(16384-reserve)//3*3)//3*8
    if args.prepared_pcm:
        source=wav8(args.input)
        if len(source)>capacity or len(source)<8192 or len(source)%8 or np.any(source[-128:]!=128):
            raise ValueError('prepared PCM must fit RAM, have >=8192 samples in groups of eight and a 128-sample silent guard')
        source_meta=dict(input=str(args.input),prepared_pcm_unchanged=True,prepared_samples=len(source),
                         sample_rate_hz=8000,pcm_bits=8,channels=1,maximum_prepared_samples=capacity)
    else:
        source,source_meta=prepare_source(args.input,args.ffmpeg,args.duration,capacity,8)
        source_meta['maximum_packed_bytes']=capacity//8*3
    source_meta['source_sha256']=hashlib.sha256(source.tobytes()).hexdigest()
    save(out/'input.json',source_meta);pcm_wav(out/'source-preview.wav',source)
    print(json.dumps(dict(stage='prepare',**source_meta)),flush=True)
    def initial(path):
        if args.reuse_pilot:return reuse_pilot(path,args.reuse_pilot,source,identity)
        packed=encode(source,width=32,allowed_codes=np.arange(0,16,2),predictor_bounds=(-30720,30719))
        return build_verified(source,packed,path,args.fuse,args.ffmpeg)
    pilot=out/'pilot';pilot_report=stage(pilot,initial)
    model=json.loads((pilot/'player.json').read_bytes())['model']
    silent=not np.any(source!=128)
    def measured(path,report):
        probe=json.loads((path/'phase-probe.json').read_bytes())
        startup=probe['first_output_absolute_tstates'][0]/3546900
        return dict(directory=path.name,**report['quality'],cold_startup_seconds=startup,
                    startup_within_60_seconds=startup<=60)
    candidates=[measured(pilot,pilot_report)];hosts=[]
    def accepted(result):
        score=result['minimum_snr_db']
        return result['speed_within_two_percent'] and result['startup_within_60_seconds'] and (silent or score is not None and score>=args.target_snr)
    for number,(width,weight,block_size) in enumerate(SEARCH[:args.attempts],1):
        if any(accepted(c) for c in candidates):break
        folder=out/f'encode-{number}'
        estimate=stage(folder,lambda p:host_search(pilot,p,width,weight,block_size,args.ffmpeg))
        hosts.append(dict(directory=folder.name,**estimate));save(out/'host-search.json',hosts)
        # Save expensive full traces for candidates near the goal, and always
        # execute the best estimate when the bounded search is exhausted.
        if estimate['host_fixed_clock_snr_db']<args.target_snr and number<args.attempts:continue
        best_host=max(hosts,key=lambda h:h['host_fixed_clock_snr_db'])
        encoded=out/best_host['directory'];variant=out/f'disk-{best_host["directory"]}'
        result=stage(variant,lambda p:build_verified(source,
            gzip.decompress((encoded/'soundtrack.ima.gz').read_bytes()),p,args.fuse,args.ffmpeg,model))
        candidates.append(measured(variant,result))
        save(out/'variants.json',candidates)
    eligible=[c for c in candidates if c['speed_within_two_percent'] and c['startup_within_60_seconds']]
    if not eligible:raise RuntimeError('no complete disk meets the speed and startup limits')
    best=max(eligible,key=lambda c:c['minimum_snr_db'] if c['minimum_snr_db'] is not None else -math.inf)
    selected=out/best['directory']
    for path in selected.iterdir():
        if path.is_file() and path.name!='stage-complete.json':shutil.copy2(path,out/path.name)
    shutil.copytree(selected/'assembly',out/'assembly',dirs_exist_ok=True)
    recording=None
    if not args.no_recording:
        def record(path):
            subprocess.run([sys.executable,str(HERE/'record_pcm.py'),str(out),'--fuse',str(args.fuse),
                            '--output',str(path),'--machine','128'],check=True)
            return json.loads((path/'report.json').read_bytes())
        recording=stage(out/'sound-128',record)
        assert recording['recording_complete'] and recording['paging_latches_match'] and recording['secondary_paging_unchanged']
        assert recording['startup_seconds']<=60,'cold preparation exceeds 60 seconds'
        shutil.copy2(out/'sound-128'/'fuse-preview.wav',out/'result-preview.wav')
    else:shutil.copy2(out/'clock-aware-output-preview.wav',out/'result-preview.wav')
    report=dict(date=date.today().isoformat(),complete=True,source=source_meta,selected=best,candidates=candidates,
                target_snr_db=args.target_snr,target_applicable=not silent,target_met=None if silent else accepted(best),
                quality_gate_passed=accepted(best),preview_only=not accepted(best),
                search_attempts=len(hosts),bounded_search=True,recording=recording,
                trd_sha256=digest(out/'audiobook-preview.trd'),physical_hardware_tested=False,
                source_reference='Prepared 8-kHz PCM8, no fitted gain/delay/time stretch; unchanged 70 Hz..4.5 kHz filter',
                spectrum_expansion=False,pcm_buffer_bytes=0,pdm_buffer_bytes=0,
                limitations=['Target is measured per input; it is not guaranteed for arbitrary audio.',
                             '25 dB remains a requested search target, not an established hardware capability.'])
    save(out/'report.json',report);print(json.dumps(report),flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'));p.add_argument('--fuse',type=Path,required=True)
    p.add_argument('--duration',type=float);p.add_argument('--target-snr',type=float,default=20.)
    p.add_argument('--attempts',type=int,choices=(1,2,3),default=3)
    p.add_argument('--prepared-pcm',action='store_true',help='reuse an exact PCM8/8k mono reference with its existing silent guard')
    p.add_argument('--no-recording',action='store_true',help='skip normal-speed sound capture, retaining full native/Fuse trace checks')
    p.add_argument('--resume',action='store_true')
    p.add_argument('--reuse-pilot',type=Path,help='optional completed converter pilot cache; exact source/player/tools are checked')
    a=p.parse_args()
    if not a.ffmpeg:p.error('FFmpeg not found; supply --ffmpeg')
    if not math.isfinite(a.target_snr) or a.target_snr<20 or a.target_snr>60:p.error('target SNR must be 20..60 dB')
    try:r=convert(a)
    except Exception as error:
        if a.output.is_dir() and (a.output/'run.json').is_file():
            save(a.output/'failure.json',dict(complete=False,type=type(error).__name__,error=str(error)))
        raise
    raise SystemExit(0 if r['quality_gate_passed'] else 2)


if __name__=='__main__':main()
