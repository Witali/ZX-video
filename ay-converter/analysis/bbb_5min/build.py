"""Build the first five minutes with the unchanged shared automatic AY core.

Only independent candidate renders are scheduled concurrently. A built-in
fixture authenticates every period/mode/level against the sequential tools.
Analyse the whole timeline once; split disks only after fitting all states.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import numpy as np

HERE=Path(__file__).resolve().parent
CORE=HERE.parents[1]
sys.path.insert(0,str(CORE))
from engine import encode
from ay_format import registers
from music_player import build_disk
from verify_preview import expected_registers,extract_player,native_check
import noise_colour
import quality
import spectrogram
import mixer_fit
import fast_mixer

RUN=subprocess.run


def sha(data): return hashlib.sha256(data).hexdigest()


def save(path,obj):
    path.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8',newline='\n')


def parallel_run(command,workers=6,**kwargs):
    script=Path(str(command[1])).name if len(command)>1 else ''
    kind={'render_noise_candidates.js':'noise','render_mixer_candidates.js':'mixer'}.get(script)
    if kind is None or (kind=='noise' and str(command[-1])=='baseline'):
        return RUN(command,**kwargs)
    step=(31+workers-1)//workers
    groups=[(i,min(31,i+step-1)) for i in range(1,32,step)]
    def work(bounds):
        return RUN([str(command[0]),str(HERE/'render_group.js'),str(CORE),kind,
                    *map(str,bounds),*map(str,command[2:])],**kwargs)
    start=time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        completed=list(pool.map(work,groups))
    print(json.dumps(dict(stage='candidate_render',kind=kind,groups=len(groups),
                          elapsed_seconds=time.perf_counter()-start)),flush=True)
    return subprocess.CompletedProcess(command,max(r.returncode for r in completed))


def parallel_objective(function, workers):
    """Schedule independent cost columns without changing their arithmetic.

    Keep the canonical function body, including every FFT batch and reduction.
    Replace its sole period loop with a joined pool. Each task writes one
    disjoint cost column. A source-structure mismatch is an explicit failure.
    """
    lines=inspect.getsource(function).splitlines()
    if function.__name__=='_optimize':
        # The multiplication is identical in every FFT batch. Compute it once
        # per waveform while retaining each sample and reduction exactly.
        score_line=next(i for i,line in enumerate(lines) if line.strip()=='def score(audio):')
        lines.insert(score_line+1,'            audio = audio*gain')
        lines=[line.replace('spectra_at(audio*gain,','spectra_at(audio,') for line in lines]
    loops=[i for i,line in enumerate(lines) if line.strip() in
           ('for period in range(1,32):','for period in range(1, 32):')]
    if len(loops)!=1: raise ValueError('canonical candidate loop changed')
    first=loops[0]; indent=len(lines[first])-len(lines[first].lstrip()); end=first+1
    while end<len(lines) and (not lines[end].strip() or len(lines[end])-len(lines[end].lstrip())>indent): end+=1
    pad=' '*indent
    replacement=[pad+'def evaluate_period(period):',*lines[first+1:end],
                 pad+f'with ThreadPoolExecutor(max_workers={workers}) as pool:',
                 pad+'    list(pool.map(evaluate_period, range(1,32)))']
    namespace=dict(function.__globals__,ThreadPoolExecutor=ThreadPoolExecutor)
    exec(compile('\n'.join([*lines[:first],*replacement,*lines[end:]])+'\n',
                 str(HERE/'parallel-objective-generated.py'),'exec'),namespace)
    return namespace[function.__name__]


def bounded_spectra(function):
    """Gather the same zero-padded FFT windows without copying the whole PCM."""
    source=inspect.getsource(function)
    old="    padded = np.pad(samples,(size//2,size//2))\n    segments = padded[centres[:,None]+np.arange(size)]"
    new="    indices = centres[:,None]+np.arange(size)-size//2\n    segments = samples[np.clip(indices,0,len(samples)-1)]\n    segments[(indices < 0) | (indices >= len(samples))] = 0."
    if new in source: return function
    if source.count(old)!=1: raise ValueError('canonical FFT window gather changed')
    namespace=dict(function.__globals__)
    exec(compile(source.replace(old,new),str(HERE/'bounded-spectra-generated.py'),'exec'),namespace)
    return namespace[function.__name__]


def objective_check(node,workers):
    """Authenticate every cost column and final decision on a short chip stream."""
    raw=np.zeros((16,11),dtype=np.uint8)
    carriers=np.arange(16)%3
    for t,c in enumerate(carriers):
        raw[t]=[120+t*3,1,80+t,2,170-t,0,0 if t%4==0 else 2+t,
                0x38^(1<<(int(c)+3)),12,9,6]
    proofs={}
    with tempfile.TemporaryDirectory(prefix='bbb-objective-check-') as directory:
        root=Path(directory)
        (root/'raw.gz').write_bytes(gzip.compress(raw.tobytes(),mtime=0))
        RUN([node,str(CORE/'render_ym2149.js'),str(root/'raw.gz'),str(root/'audio.f32'),'50',str(root/'render.json')],check=True)
        samples=noise_colour.downsample(np.fromfile(root/'audio.f32','<f4').astype(float))
        for kind,module,name in [('noise',noise_colour,'optimize'),('mixer',mixer_fit,'_optimize')]:
            original=getattr(module,name); chooser=module.choose_path; costs=[]
            def capture(cost,*args):
                costs.append(sha(cost.astype('<f8').tobytes()))
                return chooser(cost,*args)
            module.choose_path=capture
            try:
                extra={} if kind=='noise' else dict(tone_volumes=raw[:,8:].tolist(),
                    noise_shares=np.full(16,.3),carriers=carriers.tolist())
                sequential=original(samples,raw.tobytes(),node,work_parent=root,**extra)
                spectrum=noise_colour.spectra_at
                try:
                    noise_colour.spectra_at=bounded_spectra(spectrum)
                    threaded=parallel_objective(original,workers)
                    parallel=threaded(samples,raw.tobytes(),node,work_parent=root,**extra)
                finally: noise_colour.spectra_at=spectrum
                assert costs[0]==costs[1] and sequential==parallel,kind
                proofs[kind]=dict(all_costs_byte_exact=True,result_and_metadata_exact=True,
                                  cost_sha256=costs[0],registers_sha256=sha(parallel[0]))
            finally: module.choose_path=chooser
    return dict(complete=True,workers=workers,proofs=proofs)


def scheduling_check(node,workers):
    """Byte proof for all 465 candidate waveforms on varying routing/silence."""
    raw=np.zeros((16,11),dtype=np.uint8)
    tones=np.zeros_like(raw)
    route=dict(carriers=[],levels=[],eligible=[])
    for t in range(len(raw)):
        c=t%3
        raw[t]=[100+t*5,1,90+t,2,170-t,0,0 if t%4==0 else 2+t,0x38^(1<<(c+3)),12,9,6]
        tones[t]=raw[t]; tones[t,6:8]=[0,0x38]
        if t%5==0: tones[t,8+c]=0
        route['carriers'].append(c); route['levels'].append(7+t%7)
        route['eligible'].append(t%4!=0)
    with tempfile.TemporaryDirectory(prefix='bbb-render-check-') as directory:
        p=Path(directory); a=p/'serial'; b=p/'parallel'; a.mkdir(); b.mkdir()
        (p/'seed.gz').write_bytes(gzip.compress(raw.tobytes(),mtime=0))
        (p/'tones.gz').write_bytes(gzip.compress(tones.tobytes(),mtime=0))
        save(p/'route.json',route)
        jobs=[('noise',d,None) for d in (-2,-1,0)] + [('mixer',d,m) for m in ('noise','mixed') for d in (-3,-2,-1,0,1,2)]
        count=0; digest=hashlib.sha256()
        for kind,delta,mode in jobs:
            if kind=='noise':
                cmd=[node,str(CORE/'render_noise_candidates.js'),str(p/'seed.gz'),str(a),str(delta)]
                parallel=[*cmd[:3],str(b),str(delta)]; prefix='noise'
            else:
                cmd=[node,str(CORE/'render_mixer_candidates.js'),str(p/'seed.gz'),str(p/'tones.gz'),str(p/'route.json'),str(a),mode,str(delta)]
                parallel=[*cmd[:5],str(b),mode,str(delta)]; prefix='candidate'
            RUN(cmd,check=True)
            parallel_run(parallel,workers,check=True)
            for period in range(1,32):
                name=f'{prefix}-{period}.f32'; left=(a/name).read_bytes(); right=(b/name).read_bytes()
                assert left==right,(kind,mode,delta,period)
                digest.update(left); count+=1
        return dict(complete=True,waveforms=count,byte_exact=True,combined_sha256=digest.hexdigest(),workers=workers)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--node',required=True)
    p.add_argument('--ffmpeg',required=True)
    p.add_argument('--workers',type=int,default=6)
    p.add_argument('--chip',choices=('AY-3-8910','YM2149'),default='AY-3-8910')
    p.add_argument('--dynamics',choices=('compact','original'),default='compact')
    p.add_argument('--check-only',action='store_true')
    p.add_argument('--resume-noise',type=Path,help='reuse an authenticated complete noise-colour stage')
    p.add_argument('--full-mixer',action='store_true',help='use the 374-candidate reference instead of the analytic shortlist')
    p.add_argument('--normalize-peak-db',type=float,default=-1.,help='normalize selected PCM before analysis, default -1 dBFS')
    args=p.parse_args()
    if not 1<=args.workers<=12: p.error('workers must be 1..12')
    if args.normalize_peak_db != -1:
        p.error('the shared automatic engine uses the fixed -1 dBFS target')
    out=args.output; out.mkdir(parents=True,exist_ok=True)
    check=scheduling_check(args.node,args.workers); save(out/'scheduling-check.json',check)
    objective=objective_check(args.node,args.workers); save(out/'objective-check.json',objective)
    if args.check_only: return
    started=time.perf_counter()
    command=[args.ffmpeg,'-v','error','-nostdin','-i',str(args.source),'-t','301','-map','0:a:0','-vn','-ac','1','-ar','22050','-f','f32le','-']
    import audio_input
    mono,downmix=audio_input.probe_filter(args.source,args.ffmpeg)
    if mono:command[-1:-1]=['-af',mono]
    samples=np.frombuffer(RUN(command,capture_output=True,check=True).stdout,'<f4').astype(float)
    assert len(samples)>=300*22050 and np.isfinite(samples).all()
    source_peak=float(np.max(abs(samples[:300*22050])))
    source_rms=float(np.sqrt(np.mean(samples[:300*22050]**2)))
    target_peak=10**(args.normalize_peak_db/20)
    input_gain=target_peak/source_peak if source_peak>0 else 1.
    # One scalar for the selected interval and following context. Preserve
    # every waveform ratio; do not compress dynamics or normalize per tick.
    samples=samples*input_gain
    original=samples[:300*22050]
    normalization=dict(applied_before_analysis=True,method='global selected-interval sample-peak normalization',
        target_peak_dbfs=args.normalize_peak_db,source_peak=source_peak,source_rms=source_rms,
        gain_linear=input_gain,gain_db=20*np.log10(input_gain),
        normalized_peak=float(np.max(abs(original))),normalized_rms=float(np.sqrt(np.mean(original**2))),
        normalization_interval_seconds=[0,300],same_gain_on_analysis_context=True,dynamics_preserved=True,
        sample_rate_hz=22050,normalized_pcm_sha256=sha(original.astype('<f8').tobytes()),
        clipping_samples=int(np.count_nonzero(abs(original)>1)),true_peak_or_lufs_normalization=False)
    assert normalization['clipping_samples']==0
    if source_peak: assert np.isclose(normalization['normalized_peak'],target_peak,rtol=1e-14)
    save(out/'input-normalization.json',normalization)
    with args.source.open('rb') as stream: source_hash=hashlib.file_digest(stream,'sha256').hexdigest()
    print(json.dumps(dict(stage='analyse',duration_seconds=300,ticks=15000,source_sha256=source_hash)),flush=True)
    subprocess.run=lambda command,**kw: parallel_run(command,args.workers,**kw)
    original_noise,original_mixer,original_optimizer,original_spectrum=noise_colour.optimize,mixer_fit._optimize,mixer_fit.optimize,noise_colour.spectra_at
    original_fast=fast_mixer.optimize
    noise_colour.spectra_at=bounded_spectra(original_spectrum)
    resume_proof={}
    if args.resume_noise:
        resume=json.loads(args.resume_noise.read_bytes())
        assert source_hash==resume['source_sha256']
        def resume_noise(pcm,initial,node,**kw):
            assert sha(np.asarray(pcm,dtype='<f8').tobytes())==resume['pcm_sha256'], 'noise PCM changed'
            result=bytes.fromhex(resume['fitted_registers'])
            assert sha(result)==resume['fitted_registers_sha256'] and len(result)==len(initial)
            # Reapply every saved change to the fresh canonical arrangement.
            # This validates unchanged periods/routing/voices and clamped levels.
            replay=np.frombuffer(initial,np.uint8).reshape(-1,11).copy()
            for state in resume['noise_fit']['states']:
                t=state['tick']; assert replay[t,6]==state['old_period']
                replay[t,6]=state['period']
                for c in range(3):
                    if not replay[t,7] & (1<<(c+3)):
                        replay[t,8+c]=max(1,int(replay[t,8+c])+state['volume_delta'])
            assert replay.tobytes()==result, 'canonical noise input changed'
            with tempfile.TemporaryDirectory(prefix='bbb-resume-proof-',dir=out) as directory:
                p=Path(directory); (p/'initial.gz').write_bytes(gzip.compress(initial,mtime=0))
                RUN([str(node),str(CORE/'render_ym2149.js'),str(p/'initial.gz'),str(p/'audio.f32'),'50',str(p/'render.json')],check=True)
                baseline=noise_colour.downsample(np.fromfile(p/'audio.f32','<f4').astype(float))
                gain=float(np.sqrt(np.mean(pcm**2)/max(np.mean(baseline**2),1e-20)))
            assert gain==resume['noise_fit']['global_source_model_rms_gain'], 'noise gain changed'
            resume_proof.update(source_and_pcm_exact=True,every_saved_change_reapplied_exact=True,
                                baseline_gain_exact=True,initial_registers_sha256=sha(initial),fitted_registers_sha256=sha(result))
            print(json.dumps(dict(stage='resume_complete_noise',ticks=len(result)//11)),flush=True)
            return result,resume['noise_fit']
        noise_colour.optimize=resume_noise
    else: noise_colour.optimize=parallel_objective(original_noise,args.workers)
    if args.full_mixer: mixer_fit._optimize=parallel_objective(original_mixer,args.workers)
    else:
        fast_mixer.optimize=lambda *a,**kw: original_fast(*a,**kw,workers=args.workers)
    try:
        frames,fit=encode(samples,args.node,out,profile='auto',start_tick=0,ticks=15000,
            mixer_search='full' if args.full_mixer else 'fast',chip=args.chip,dynamics=args.dynamics)
    finally:
        subprocess.run=RUN
        noise_colour.optimize,mixer_fit._optimize=original_noise,original_mixer
        fast_mixer.optimize=original_fast
        mixer_fit.optimize=original_optimizer
        noise_colour.spectra_at=original_spectrum
    raw=b''.join(registers(f) for f in frames); packed=b''.join(f.serialize() for f in frames)
    width=fit['register_bytes_per_state'];state_bytes=fit['packed_state_bytes']
    packed_name=f'soundtrack.ay{state_bytes}.gz'
    assert len(frames)==15000 and raw==expected_registers(packed,state_bytes)
    (out/'registers.gz').write_bytes(gzip.compress(raw,mtime=0))
    (out/packed_name).write_bytes(gzip.compress(packed,mtime=0))
    save(out/'analysis.json',fit)
    print(json.dumps(dict(stage='full_continuous_preview',elapsed_seconds=time.perf_counter()-started)),flush=True)
    RUN([args.node,str(CORE/'render_ym2149.js'),str(out/'registers.gz'),str(out/'chip.f32'),'50',str(out/'chip-render.json'),str(width),
        'YM' if args.chip=='YM2149' else 'AY'],check=True)
    rendered=np.fromfile(out/'chip.f32','<f4').astype(float)
    assert len(rendered)==300*44100
    levels=[float(np.sqrt(np.mean(s*s))) for s in (original,rendered)]
    target=min(.12,*(.9*r/max(float(np.max(abs(s))),1e-12) for s,r in zip((original,rendered),levels)))
    import pcm_levels
    processed,_=pcm_levels.process(samples,ticks=15000,dynamics=args.dynamics)
    original=processed[:300*22050]
    quality.write_wav(out/'original-preview.wav',original,22050)
    quality.write_wav(out/'ay-preview.wav',rendered*fit['simulation_feedback']['fixed_model_gain'],44100)
    down=noise_colour.downsample(rendered)
    metrics=spectrogram.compare(spectrogram.features(original),spectrogram.features(down))
    (out/'chip.f32').unlink()
    parts=[]
    part_ticks=5000 if width==14 else 7500;part_count=15000//part_ticks
    for number,lo in enumerate(range(0,15000,part_ticks),1):
        part=out/f'part{number:02d}'; part.mkdir(exist_ok=True)
        regs=raw[lo*width:(lo+part_ticks)*width]; ay=packed[lo*state_bytes:(lo+part_ticks)*state_bytes]
        title=f'BIG BUCK BUNNY {number}/{part_count}'
        disk,meta=build_disk(regs,title=title,loop=False,assembly_dir=part/'assembly',register_bytes=width)
        (part/'audio-preview.trd').write_bytes(disk)
        (part/packed_name).write_bytes(gzip.compress(ay,mtime=0))
        (part/'registers.gz').write_bytes(gzip.compress(regs,mtime=0))
        save(part/'player.json',meta)
        native=native_check(extract_player(disk),meta,regs); save(part/'native.json',native)
        part_report=dict(complete=True,preview_only=True,source=str(args.source),source_sha256=source_hash,
            start_seconds=lo/50,duration_seconds=part_ticks/50,ticks=part_ticks,update_rate_hz=50,sound_quantum_ms=20,
            profile='auto',loop_playback=False,disk_timing_verified=False,hardware_tested=False,
            artifacts={x.relative_to(part).as_posix():dict(bytes=x.stat().st_size,sha256=sha(x.read_bytes())) for x in part.rglob('*') if x.is_file()})
        save(part/'report.json',part_report)
        parts.append(dict(number=number,start_tick=lo,end_tick=lo+part_ticks,duration_seconds=part_ticks/50,
            disk=(part/'audio-preview.trd').relative_to(out).as_posix(),trd_sha256=sha(disk),native=native))
    assert b''.join(gzip.decompress((out/f'part{i:02d}/registers.gz').read_bytes()) for i in range(1,part_count+1))==raw
    report=dict(complete=True,source=str(args.source),source_sha256=source_hash,ffmpeg_command=command,
        interval_seconds=[0,300],ticks=15000,update_rate_hz=50,sound_quantum_ms=20,profile='auto',
        input_normalization=normalization,
        source_processing=fit['input_normalization'],target_chip=args.chip,downmix=downmix,
        register_bytes_per_state=width,packed_state_bytes=state_bytes,packed_filename=packed_name,
        analysis_context_after_seconds=(len(samples)-len(original))/22050,continuous_analysis=True,
        continuous_model_preview=True,no_source_pcm_in_synthesis=True,
        fixed_model_gain=fit['simulation_feedback']['fixed_model_gain'],simulation_feedback=fit['simulation_feedback'],
        resumed_complete_noise_stage=bool(args.resume_noise),
        resumed_noise_proof=resume_proof,
        mixer_search='full-374' if args.full_mixer else 'analytic-20',
        registers_sha256=sha(raw),packed_sha256=sha(packed),parts=parts,scheduling_check=check,objective_check=objective,
        spectrogram_metrics=metrics,elapsed_seconds=time.perf_counter()-started,
        physical_hardware_tested=False,all_disks_fuse_verified=False,
        limits='Independent one-shot resident disks; a manual swap causes a pause. Full WAV has continuous chip phase. No video rebuild.')
    save(out/'report.json',report)
    print(json.dumps(dict(stage='built',ticks=15000,seconds=300,disks=part_count,elapsed_seconds=report['elapsed_seconds'])),flush=True)


if __name__=='__main__': main()
