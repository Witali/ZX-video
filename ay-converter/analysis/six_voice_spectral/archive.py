"""Retain the complete spectral follow-up, including rejected control streams."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import wave
import numpy as np

HERE=Path(__file__).resolve().parent
CORE=HERE.parents[1]
sys.path.insert(0,str(CORE))
import experimental_six_voice as synth
import quality
import noise_colour
from analyze import diagnostic, read


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load_controls(path):
    with np.load(path) as stored:return {k:stored[k] for k in stored.files}


def replay(folder,wav_name,controls_name,feedback):
    controls=load_controls(folder/controls_name)
    assert synth.validate(controls)==1500
    audio=synth.render(controls,feedback['voice_gain'],**feedback['render_options'])
    assert len(audio)==1323000 and np.isfinite(audio).all() and abs(audio).max()<1
    with tempfile.TemporaryDirectory(dir=HERE,prefix='replay-') as temporary:
        output=Path(temporary)/'replay.wav'
        quality.write_wav(output,audio,44100)
        assert output.read_bytes()==(folder/wav_name).read_bytes(),str(folder)
    return controls


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('--plots',type=Path,required=True)
    parser.add_argument('--trial-root',type=Path,action='append',required=True)
    parser.add_argument('--log',type=Path,required=True)
    parser.add_argument('--tests',type=Path,required=True)
    args=parser.parse_args()
    target=HERE/'evidence'
    if target.exists():raise ValueError('archive already exists')
    report=json.loads((args.build/'report.json').read_bytes())
    spectral=json.loads((args.plots/'spectral-report.json').read_bytes())
    reference=Path(report['reference'])
    assert report['complete'] and report['seconds']==30 and report['ticks']==1500
    assert sha(reference)==report['reference_sha256']==spectral['reference_sha256']
    assert sha(args.build/'reference.wav')==sha(reference)
    assert sha(args.build/'six-voice-preview.wav')==spectral['candidate_wav_sha256']
    for name,digest in report['producer_sources_sha256_lf'].items():
        assert hashlib.sha256((CORE/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest,name
    selected=replay(args.build,'six-voice-preview.wav','selectable-controls.npz',report['results']['selectable']['feedback'])
    baseline=CORE/'analysis/six_voice_clicks/evidence'
    old=json.loads((baseline/'report.json').read_bytes())
    replay(baseline,'six-voice-preview.wav','selectable-controls.npz',old['results']['selectable']['feedback'])
    source=synth.read_reference(reference)
    all_trials=[]
    for root in args.trial_root:
        history=json.loads((root/'trials.json').read_bytes())
        assert history['source_sha256']==sha(reference)
        for entry in history['trials']:
            folder=root/entry['name']
            controls=replay(folder,'preview.wav','controls.npz',entry['feedback'])
            details=diagnostic(source,read(folder/'preview.wav'))
            good=True
            for size,metric in details['unpooled'].items():
                previous=spectral['baseline']['unpooled'][size]
                good &= all(metric[key]>=previous[key] for key in ('magnitude_cosine','sqrt_magnitude_cosine'))
                good &= all(metric[key]<=previous[key] for key in ('log_magnitude_mae_db','spectral_convergence'))
            good &= details['metrics']['level_mae_db']<=spectral['baseline']['metrics']['level_mae_db']
            good &= details['sub_50hz_power_fraction']<.01
            entry=dict(entry,trial_id=root.name+'/'+entry['name'],wave_sha256=sha(folder/'preview.wav'),
                       controls_sha256=sha(folder/'controls.npz'),controls_only_replay_exact=True,
                       independent_diagnostics=details,all_scale_improvement_guard=bool(good),
                       temporary_folder=str(folder.resolve()))
            all_trials.append(entry)
    assert len(all_trials)==16
    eligible=[entry for entry in all_trials if entry['all_scale_improvement_guard']]
    assert eligible
    best=min(eligible,key=lambda entry:entry['metrics']['objective_db'])
    assert best['wave_sha256']==sha(args.build/'six-voice-preview.wav'),best['trial_id']
    # The lowest weighted log objective alone is insufficient: stronger
    # inverse weighting can worsen dominant partials on a long STFT window.
    decision=dict(date='2026-10-13',complete=True,trials=all_trials,selected_trial=best['trial_id'],
                  selection='Lowest combined objective among trials improving magnitude/root cosine, log error and spectral convergence at all three scales, level MAE, and sub-50-Hz power below 1%.',
                  listening_acceptance_pending=True,global_optimum_claimed=False)
    shutil.copytree(args.build,target)
    for filename in ('spectrogram-full.png','spectrogram-detail.png','source-result-full.png','source-result-detail.png','spectral-report.json'):
        shutil.copyfile(args.plots/filename,target/filename)
    shutil.copyfile(args.log,target/'run.log')
    shutil.copyfile(args.tests,target/'tests.log')
    for entry in all_trials:
        folder=Path(entry.pop('temporary_folder'))
        saved=target/'trials'/entry['trial_id']
        saved.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(folder/'controls.npz',saved/'controls.npz')
    (target/'trials.json').write_text(json.dumps(decision,indent=2)+'\n',encoding='utf-8',newline='\n')
    segments=[]
    for path in (baseline/'six-voice-preview.wav',target/'six-voice-preview.wav'):
        with wave.open(str(path),'rb') as stream:
            assert (stream.getframerate(),stream.getnchannels(),stream.getsampwidth(),stream.getnframes())==(44100,1,2,1323000)
            segments.append(stream.readframes(stream.getnframes()))
    combined=segments[0]+bytes(88200)+segments[1]
    with wave.open(str(target/'before-after.wav'),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(44100);stream.writeframes(combined)
    with wave.open(str(target/'before-after.wav'),'rb') as stream:
        assert stream.getnframes()==61*44100 and stream.readframes(stream.getnframes())==combined
    proof=dict(complete=True,date='2026-10-13',seconds=30,ticks=1500,samples=1323000,voices=6,
               controls_only_replay_exact=True,baseline_replay_exact=True,all_16_trial_replays_exact=True,
               reference_bytes_exact=True,producer_hashes_checked=True,before_after_pcm_segments_exact=True,
               peak=report['results']['selectable']['peak'],clipped_samples=0,
               source_pcm_added_to_output=False,balanced_output_mixer=True,
               no_time_pitch_or_local_gain_warp=True,real_chip_or_z80_validation=False)
    (target/'verification.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8',newline='\n')
    files={p.relative_to(target).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in target.rglob('*') if p.is_file()}
    (target/'manifest.json').write_text(json.dumps(dict(files=files),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(verification=proof,selected_trial=best['trial_id'],trials=len(all_trials))),flush=True)


if __name__=='__main__':main()
