"""Apply canonical chip feedback to an authenticated complete initial build.

Reuse only the identical normalized PCM and initial registers. Rebuild both
independent disks and invalidate their previous timing proof after any change.
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
import numpy as np

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[1]
sys.path.insert(0, str(CORE))
import simulation_refine
import noise_colour
import spectrogram
import quality
from ay_format import AyFrame, registers
from music_player import build_disk
from verify_preview import native_check, extract_player, expected_registers


def sha(data): return hashlib.sha256(data).hexdigest()
def save(path, value): path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--node',required=True)
    args = parser.parse_args()
    root = args.baseline; out = args.output
    if out.exists() and any(out.iterdir()): raise ValueError('output must be empty')
    out.mkdir(parents=True,exist_ok=True)
    report = json.loads((root/'report.json').read_bytes())
    with Path(report['source']).open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==report['source_sha256']
    pcm = np.frombuffer(subprocess.run(report['ffmpeg_command'],capture_output=True,check=True).stdout,'<f4').astype(float)
    samples = pcm[:300*22050]*report['input_normalization']['gain_linear']
    assert sha(samples.astype('<f8').tobytes())==report['input_normalization']['normalized_pcm_sha256']
    initial = gzip.decompress((root/'registers.gz').read_bytes())
    assert sha(initial)==report['registers_sha256'] and len(initial)==165000
    baseline = out/'baseline'; baseline.mkdir()
    for name in ('report.json','analysis.json','mixer-fit.json.gz','registers.gz'):
        shutil.copyfile(root/name,baseline/name)
    for number in (1,2):
        proof = json.loads((root/f'part{number:02d}/verification.json').read_bytes())
        assert proof['complete'] and proof['fuse']['complete'] and proof['fuse']['every_register_exact']
        save(baseline/f'part{number:02d}-verification.json',proof)
    started = time.perf_counter()
    raw, feedback = simulation_refine.optimize(samples,initial,args.node,work_parent=out)
    save(out/'simulation-feedback.json',feedback)
    rows = np.frombuffer(raw,np.uint8).reshape(-1,11)
    frames = [AyFrame(tuple(int(row[c*2])+(int(row[c*2+1])<<8) for c in range(3)),
        tuple(map(int,row[8:])),int(row[6]),int(row[7])) for row in rows]
    packed = b''.join(frame.serialize() for frame in frames)
    assert raw==expected_registers(packed) and raw==b''.join(registers(f) for f in frames)
    (out/'registers.gz').write_bytes(gzip.compress(raw,mtime=0))
    (out/'soundtrack.ay9.gz').write_bytes(gzip.compress(packed,mtime=0))
    for name in ('noise-fit.json.gz','input-normalization.json','scheduling-check.json','objective-check.json'):
        shutil.copyfile(root/name,out/name)
    shutil.copyfile(root/'mixer-fit.json.gz',out/'mixer-fit.json.gz')
    states = json.loads(gzip.decompress((root/'channel-states.json.gz').read_bytes()))
    for state,frame in zip(states['states'],frames):
        state.update(periods=list(frame.periods),volumes=list(frame.volumes),mixer=frame.mixer,noise_period=frame.noise_period)
    (out/'channel-states.json.gz').write_bytes(gzip.compress(json.dumps(states,separators=(',',':')).encode(),mtime=0))
    events = json.loads((root/'note-events.json').read_bytes())
    for event in events['events']:
        values=[frames[t].periods[event['voice']] for t in range(event['start_tick'],event['end_tick'])]
        event.update(rendered_period_range=[min(values),max(values)],pitch_held=len(set(values))==1)
    save(out/'note-events.json',events)
    fit = json.loads((root/'analysis.json').read_bytes())
    fit.update(simulation_feedback=feedback,model='persistent_components_and_perceptual_chip_feedback_v5')
    save(out/'analysis.json',fit)
    subprocess.run([args.node,str(CORE/'render_ym2149.js'),str(out/'registers.gz'),str(out/'chip.f32'),'50',str(out/'chip-render.json')],check=True)
    rendered = np.fromfile(out/'chip.f32','<f4').astype(float)
    quality.write_wav(out/'original-preview.wav',samples,22050)
    quality.write_wav(out/'ay-preview.wav',rendered*feedback['fixed_model_gain'],44100)
    metrics=spectrogram.compare(spectrogram.features(samples),spectrogram.features(noise_colour.downsample(rendered)))
    (out/'chip.f32').unlink()
    # Save a fair before/after audition under the same fixed output gain.
    subprocess.run([args.node,str(CORE/'render_ym2149.js'),str(root/'registers.gz'),str(out/'before.f32'),'50',str(baseline/'chip-render.json')],check=True)
    quality.write_wav(baseline/'ay-before.wav',np.fromfile(out/'before.f32','<f4').astype(float)*feedback['fixed_model_gain'],44100)
    (out/'before.f32').unlink()
    parts=[]
    for number,lo in enumerate((0,7500),1):
        part=out/f'part{number:02d}';part.mkdir()
        regs=raw[lo*11:(lo+7500)*11]; ay=packed[lo*9:(lo+7500)*9]
        disk,meta=build_disk(regs,title=f'BIG BUCK BUNNY {number}/2',loop=False,assembly_dir=part/'assembly')
        (part/'audio-preview.trd').write_bytes(disk)
        (part/'registers.gz').write_bytes(gzip.compress(regs,mtime=0))
        (part/'soundtrack.ay9.gz').write_bytes(gzip.compress(ay,mtime=0))
        save(part/'player.json',meta)
        native=native_check(extract_player(disk),meta,regs);save(part/'native.json',native)
        save(part/'report.json',dict(complete=True,preview_only=True,ticks=7500,duration_seconds=150,
            start_seconds=lo/50,profile='auto',loop_playback=False,disk_timing_verified=False,hardware_tested=False))
        parts.append(dict(number=number,start_tick=lo,end_tick=lo+7500,duration_seconds=150,
            disk=(part/'audio-preview.trd').relative_to(out).as_posix(),trd_sha256=sha(disk),native=native))
    report.pop('global_preview_rms',None)
    report.update(registers_sha256=sha(raw),packed_sha256=sha(packed),parts=parts,
        fixed_model_gain=feedback['fixed_model_gain'],simulation_feedback=feedback,spectrogram_metrics=metrics,
        reused_initial_fit=dict(source_and_pcm_hash_exact=True,initial_registers_sha256=sha(initial),
            previous_complete_native_and_fuse=True,scope='component/noise/analytic-mixer fit; canonical feedback computed anew'),
        initial_fit_elapsed_seconds=report['elapsed_seconds'],feedback_and_rebuild_elapsed_seconds=time.perf_counter()-started,
        all_disks_fuse_verified=False)
    save(out/'report.json',report)
    print(json.dumps(dict(stage='rebuilt',complete=True,seconds=300,disks=2,
        before=feedback['baseline'],after=feedback['final'],changed_volumes=feedback['changed_volume_registers'],
        changed_periods=feedback['changed_tone_periods'],changed_noise=feedback['changed_noise_ticks'])),flush=True)


if __name__=='__main__': main()
