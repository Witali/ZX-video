"""Authenticate and archive a complete repaired six-voice audition."""
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


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('--comparison',type=Path,required=True)
    parser.add_argument('--log',type=Path,required=True)
    parser.add_argument('--tests',type=Path,required=True)
    args=parser.parse_args()
    report=json.loads((args.build/'report.json').read_bytes())
    comparison=json.loads(args.comparison.read_bytes())
    assert report['complete'] and report['voices']==6 and report['ticks']==1500 and report['seconds']==30
    reference=Path(report['reference'])
    assert sha(reference)==report['reference_sha256']==comparison['reference_sha256']
    assert comparison['baseline_wav_replay_exact'] and comparison['candidate']['controls_only_replay_exact']
    for name,digest in report['producer_sources_sha256_lf'].items():
        assert hashlib.sha256((CORE/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest,name
    with np.load(args.build/'selectable-controls.npz') as stored:
        controls={k:stored[k] for k in stored.files}
    assert synth.validate(controls)==1500
    # Reconstruction receives controls, model settings and one constant gain;
    # it neither loads nor mixes any samples from the source recording.
    rendered=synth.render(controls,report['results']['selectable']['feedback']['voice_gain'],**report['render_options'])
    assert len(rendered)==1323000 and np.isfinite(rendered).all() and abs(rendered).max()<1
    with tempfile.TemporaryDirectory(dir=HERE,prefix='archive-replay-') as temporary:
        replay=Path(temporary)/'replay.wav'
        quality.write_wav(replay,rendered,44100)
        assert replay.read_bytes()==(args.build/'six-voice-preview.wav').read_bytes()
    baseline=CORE/'analysis/six_voice/evidence/six-voice-preview.wav'
    target=HERE/'evidence'
    if target.exists():raise ValueError('archive already exists')
    shutil.copytree(args.build,target)
    shutil.copyfile(reference,target/'reference.wav')
    shutil.copyfile(args.comparison,target/'comparison.json')
    shutil.copyfile(args.log,target/'run.log')
    shutil.copyfile(args.tests,target/'tests.log')
    before_after=[]
    for path in (baseline,target/'six-voice-preview.wav'):
        with wave.open(str(path),'rb') as audio:
            assert (audio.getframerate(),audio.getnchannels(),audio.getsampwidth(),audio.getnframes())==(44100,1,2,1323000)
            before_after.append(audio.readframes(audio.getnframes()))
    with wave.open(str(target/'six-voice-before-after.wav'),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(44100)
        audio.writeframes(before_after[0]+bytes(44100*2)+before_after[1])
    with wave.open(str(target/'six-voice-before-after.wav'),'rb') as audio:
        assert audio.getnframes()==61*44100
        joined=audio.readframes(audio.getnframes())
        assert joined[:len(before_after[0])]==before_after[0]
        assert joined[len(before_after[0]):len(before_after[0])+88200]==bytes(88200)
        assert joined[-len(before_after[1]):]==before_after[1]
    proof=dict(complete=True,date='2026-10-13',seconds=30,ticks=1500,samples=1323000,
               controls_only_replay_exact=True,reference_bytes_exact=sha(target/'reference.wav')==sha(reference),
               baseline_wav_sha256=sha(baseline),candidate_wav_sha256=sha(target/'six-voice-preview.wav'),
               before_after_seconds=61,before_after_segments_seconds=[[0,30],[31,61]],
               before_after_pcm_segments_exact=True,clipped_samples=0,producer_hashes_checked=True,
               source_interval_seconds=[60,90],hypothetical_transition_envelope=True,
               real_chip_or_z80_validation=False,listening_acceptance_pending=True)
    (target/'verification.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8',newline='\n')
    files={p.relative_to(target).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in target.rglob('*') if p.is_file()}
    (target/'manifest.json').write_text(json.dumps(dict(files=files),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(proof))


if __name__=='__main__':main()
