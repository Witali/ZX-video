"""Authenticate and retain the bounded hypothetical six-voice listening run."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import wave
import numpy as np

HERE=Path(__file__).resolve().parent;CORE=HERE.parents[1];sys.path.insert(0,str(CORE))
import experimental_six_voice as synth
import quality


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path);parser.add_argument('--log',type=Path,required=True)
    parser.add_argument('--tests',type=Path,required=True);args=parser.parse_args()
    report=json.loads((args.build/'report.json').read_bytes())
    assert report['complete'] and report['voices']==6 and report['seconds']==30 and report['ticks']==1500
    reference=Path(report['reference']);assert sha(reference.read_bytes())==report['reference_sha256']
    for name,digest in report['producer_sources_sha256_lf'].items():
        assert sha((CORE/name).read_bytes().replace(b'\r\n',b'\n'))==digest,name
    verified={}
    with tempfile.TemporaryDirectory(dir=args.build.parent,prefix='six-voice-replay-') as temporary:
        for variant in ('selectable','square'):
            result=report['results'][variant]
            with np.load(args.build/f'{variant}-controls.npz') as stored:
                controls={name:stored[name] for name in stored.files}
            assert synth.validate(controls)==1500
            if variant=='square':assert not controls['shapes'].any()
            rendered=synth.render(controls,result['feedback']['voice_gain'])
            assert len(rendered)==30*44100 and np.isfinite(rendered).all() and abs(rendered).max()<1
            replay=Path(temporary)/result['wav'];quality.write_wav(replay,rendered,44100)
            assert replay.read_bytes()==(args.build/result['wav']).read_bytes(),variant
            with wave.open(str(replay),'rb') as audio:
                assert audio.getnframes()==30*44100 and audio.getnchannels()==1 and audio.getsampwidth()==2
                pcm=np.frombuffer(audio.readframes(audio.getnframes()),'<i2')
            verified[variant]=dict(controls_only_replay_exact=True,samples=len(pcm),seconds=30,
                peak=float(abs(pcm.astype(float)).max()/32768),clipped_samples=int(np.count_nonzero(abs(pcm.astype(int))>=32767)),sha256=sha(replay.read_bytes()))
            assert not verified[variant]['clipped_samples']
    baseline=Path(report['results']['previous_AY']['wav'])
    assert sha(baseline.read_bytes())==report['results']['previous_AY']['sha256']
    target=HERE/'evidence'
    if target.exists():raise ValueError('archive already exists')
    shutil.copytree(args.build,target)
    # Publish the exact prepared input bytes; do not apply a second PCM16
    # round-trip to an already quantized reference recording.
    shutil.copyfile(reference,target/'reference.wav');shutil.copyfile(baseline,target/'previous-ay.wav')
    shutil.copyfile(args.log,target/'run.log');shutil.copyfile(args.tests,target/'tests.log')
    result=dict(complete=True,date='2026-10-13',source_interval_seconds=[60,90],seconds=30,ticks=1500,
        reference_bytes_exact=True,previous_ay_bytes_exact=True,waves=verified,
        hypothetical_hardware=True,no_z80_or_release_changes=True,
        scope='Six hypothetical continuous oscillators with selectable waveform, AY-like period/DAC/control grid and one noise generator. Fixed-volume mode only, not a real chip or full feature-equivalence proof.')
    (target/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    files={p.relative_to(target).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in target.rglob('*') if p.is_file()}
    (target/'manifest.json').write_text(json.dumps(dict(files=files),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result))


if __name__=='__main__':main()
