"""Package final real-AY feedback as continuous audio and independent disks."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
HERE=Path(__file__).resolve().parent;CORE=HERE.parents[1];sys.path.insert(0,str(CORE))
from ay_format import AyFrame,registers
from music_player import build_disk
from verify_preview import expected_registers,native_check,extract_player
import quality
import noise_colour
import spectrogram
import noise_gate
import pcm_levels


def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path);parser.add_argument('fit',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--node',required=True);args=parser.parse_args()
    root=args.baseline;out=args.output
    if out.exists() and any(out.iterdir()):raise ValueError('output must be empty')
    out.mkdir(parents=True,exist_ok=True)
    report=json.loads((root/'report.json').read_bytes());stage=json.loads((args.fit/'stage-report.json').read_bytes())
    compact='source_processing' in stage
    processing=json.loads((args.fit/'source-processing.json').read_bytes()) if compact else None
    command=processing['ffmpeg_command'] if compact else report['ffmpeg_command']
    pcm=np.frombuffer(subprocess.run(command,capture_output=True,check=True).stdout,'<f4').astype(float)
    source=(pcm_levels.process(pcm,ticks=15000,dynamics='compact')[0][:300*22050] if compact
            else pcm[:300*22050]*report['input_normalization']['gain_linear'])
    assert sha(source.astype('<f8').tobytes())==stage['normalized_pcm_sha256']
    raw=gzip.decompress((args.fit/'registers.gz').read_bytes());width=stage['register_bytes_per_state']
    assert sha(raw)==stage['final_registers_sha256'] and len(raw)==15000*width
    rows=np.frombuffer(raw,np.uint8).reshape(-1,width)
    state_bytes=12 if width==14 else 9;packed_name=f'soundtrack.ay{state_bytes}.gz'
    frames=[AyFrame(tuple(int(row[c*2])+(int(row[c*2+1])<<8) for c in range(3)),
        tuple(map(int,row[8:11])),int(row[6]),int(row[7]),
        int(row[11])+(int(row[12])<<8) if width==14 else 0,int(row[13]) if width==14 else 255,state_bytes) for row in rows]
    packed=b''.join(frame.serialize() for frame in frames)
    assert expected_registers(packed,state_bytes)==raw and b''.join(registers(f) for f in frames)==raw
    for name in ('registers.gz','stage-report.json','final-feedback.json'):
        shutil.copyfile(args.fit/name,out/name)
    for name in ('simulation-feedback.json','hardware-envelope.json','necessary-noise.json'):
        shutil.copyfile((root if compact else args.fit)/name,out/name)
    if compact:
        stage.update(simulation_feedback=stage['previous_feedback'] or stage['feedback'],final_feedback=stage['feedback'],final=stage['feedback']['final'],
            noise_policy=report['necessary_noise'],hardware_envelope=report['hardware_envelope'],
            seed_scope=stage['scope'],final_feedback_elapsed_seconds=0)
        shutil.copyfile(args.fit/'source-processing.json',out/'source-processing.json')
        save(out/'simulation-feedback.json',stage['simulation_feedback'])
    (out/packed_name).write_bytes(gzip.compress(packed,mtime=0))
    for name in ('input-normalization.json','noise-fit.json.gz','mixer-fit.json.gz','scheduling-check.json','objective-check.json'):
        shutil.copyfile(root/name,out/name)
    if compact:save(out/'input-normalization.json',processing['normalization'])
    states=json.loads(gzip.decompress((root/'channel-states.json.gz').read_bytes()))
    for state,frame in zip(states['states'],frames):
        state.update(periods=list(frame.periods),volumes=list(frame.volumes),mixer=frame.mixer,noise_period=frame.noise_period,
            noise_channel=next((c for c in range(3) if frame.volumes[c] and not frame.mixer&(1<<(c+3))),-1),
            envelope_period=frame.envelope_period,envelope_shape_write=frame.envelope_shape,
            envelope_channels=[c for c in range(3) if frame.volumes[c]&16])
    (out/'channel-states.json.gz').write_bytes(gzip.compress(json.dumps(states,separators=(',',':')).encode(),mtime=0))
    events=json.loads((root/'note-events.json').read_bytes())
    for event in events['events']:
        values=[frames[t].periods[event['voice']] for t in range(event['start_tick'],event['end_tick'])]
        event.update(rendered_period_range=[min(values),max(values)],pitch_held=len(set(values))==1,
            envelope_control_ticks=sum(bool(frames[t].volumes[event['voice']]&16) for t in range(event['start_tick'],event['end_tick'])))
    save(out/'note-events.json',events)
    fit=json.loads((root/'analysis.json').read_bytes())
    fit.update(simulation_feedback=stage['simulation_feedback'],necessary_noise=stage['noise_policy'],
        hardware_envelope=stage['hardware_envelope'],final_feedback=stage['final_feedback'],
        model='real_AY_perceptual_feedback_and_running_envelopes_v7',packed_state_bytes=state_bytes,
        register_bytes_per_state=width,target_chip='AY-3-8910/8912',distinct_hardware_envelope_levels=16,
        noise_ticks=int(noise_gate.active_noise(rows).sum()),seed_scope=stage['seed_scope'])
    save(out/'analysis.json',fit)
    gain=stage['simulation_feedback']['fixed_model_gain']
    subprocess.run([args.node,str(CORE/'render_ym2149.js'),str(out/'registers.gz'),str(out/'chip.f32'),
        '50',str(out/'chip-render.json'),str(width)],check=True)
    rendered=np.fromfile(out/'chip.f32','<f4').astype(float)
    assert len(rendered)==300*44100 and abs(rendered).max()*gain<=.999
    quality.write_wav(out/'ay-preview.wav',rendered*gain,44100)
    quality.write_wav(out/'original-preview.wav',source,22050)
    metrics=spectrogram.compare(spectrogram.features(source),spectrogram.features(noise_colour.downsample(rendered)))
    preview=dict(source_rms=float(np.sqrt(np.mean(source**2))),source_peak=float(abs(source).max()),
        model_rms=float(np.sqrt(np.mean((rendered*gain)**2))),model_peak=float(abs(rendered*gain).max()),
        one_fixed_calibration=True,no_local_pcm_gain=True)
    (out/'chip.f32').unlink()
    before=out/'baseline';before.mkdir()
    save(before/'normalized-seed-report.json',report)
    shutil.copyfile(root/'registers.gz',before/'seed-registers.gz')
    if compact:
        shutil.copyfile(root/'ay-preview.wav',before/'ay-before-compression.wav')
        for i in (1,2,3):shutil.copyfile(root/f'part{i:02d}/verification.json',before/f'uncompressed-ay-part{i:02d}-verification.json')
    else:
        subprocess.run([args.node,str(CORE/'render_ym2149.js'),str(root/'registers.gz'),str(out/'before.f32'),
            '50',str(before/'ay-seed-render.json')],check=True)
        quality.write_wav(before/'ay-before-feedback.wav',np.fromfile(out/'before.f32','<f4').astype(float)*gain,44100)
        (out/'before.f32').unlink()
    ym=root.parent/'bbb-five-minute-envelope'
    if (ym/'report.json').exists():
        save(before/'superseded-ym-envelope-report.json',json.loads((ym/'report.json').read_bytes()))
        for i in (1,2,3):shutil.copyfile(ym/f'part{i:02d}/verification.json',before/f'superseded-ym-part{i:02d}-verification.json')
    parts=[];part_ticks=5000 if width==14 else 7500;number_parts=15000//part_ticks
    for number,lo in enumerate(range(0,15000,part_ticks),1):
        part=out/f'part{number:02d}';part.mkdir()
        regs=raw[lo*width:(lo+part_ticks)*width];ay=packed[lo*state_bytes:(lo+part_ticks)*state_bytes]
        # Cold disks enter without an already active envelope phase.
        assert not any(regs[8+c]&16 for c in range(3)) or (width==14 and regs[13]!=255)
        disk,metadata=build_disk(regs,title=f'BIG BUCK BUNNY {number}/{number_parts}',loop=False,assembly_dir=part/'assembly',register_bytes=width)
        (part/'audio-preview.trd').write_bytes(disk)
        (part/'registers.gz').write_bytes(gzip.compress(regs,mtime=0))
        (part/packed_name).write_bytes(gzip.compress(ay,mtime=0))
        save(part/'player.json',metadata)
        native=native_check(extract_player(disk),metadata,regs);save(part/'native.json',native)
        save(part/'report.json',dict(complete=True,preview_only=True,ticks=part_ticks,duration_seconds=part_ticks/50,
            start_seconds=lo/50,profile='auto',loop_playback=False,disk_timing_verified=False,hardware_tested=False,
            artifacts={p.relative_to(part).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in part.rglob('*') if p.is_file()}))
        parts.append(dict(number=number,start_tick=lo,end_tick=lo+part_ticks,duration_seconds=part_ticks/50,
            disk=(part/'audio-preview.trd').relative_to(out).as_posix(),trd_sha256=sha(disk),native=native))
    report.pop('global_preview_rms',None)
    report.update(parts=parts,registers_sha256=sha(raw),packed_sha256=sha(packed),packed_state_bytes=state_bytes,
        packed_filename=packed_name,register_bytes_per_state=width,target_chip='AY-3-8910/8912',distinct_envelope_levels=16,
        simulation_feedback=stage['simulation_feedback'],necessary_noise=stage['noise_policy'],hardware_envelope=stage['hardware_envelope'],
        final_feedback=stage['final_feedback'],final_metrics=stage['final'],spectrogram_metrics=metrics,preview_levels=preview,
        fixed_model_gain=gain,seed_reuse=stage['seed_scope'],all_disks_fuse_verified=False,
        final_fit_elapsed_seconds=stage['elapsed_seconds']+stage['final_feedback_elapsed_seconds'],
        limits='Independently bootable one-shot resident disks. Manual disk swaps pause sound; the full 300-s WAV is continuous. No complete film rebuild or physical-hardware claim.')
    if compact:
        report.update(source_processing=processing,input_normalization=processing['normalization'],ffmpeg_command=command,
            downmix=processing['downmix'],dynamics='compact',previous_compressed_feedback=stage['previous_feedback'],
            reference_preview='original-preview.wav contains the downmixed, compressed reference used by the fitter',
            hardware_control_scope='Previous fully verified AY controls retained as seeds; final waveform feedback recomputed for the changed PCM.')
    save(out/'report.json',report)
    print(json.dumps(dict(complete=True,seconds=300,ticks=15000,disks=number_parts,noise_ticks=fit['noise_ticks'],
        native_register_writes=sum(p['native']['register_writes'] for p in parts))),flush=True)


if __name__=='__main__':main()
