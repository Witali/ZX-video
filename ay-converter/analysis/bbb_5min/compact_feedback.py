"""Fit actual AY registers to centre-priority, compressed five-minute PCM.

The preceding fully checked AY registers are a starting seed, never a reused
fit for changed PCM. Feedback is recomputed against the complete new reference.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
HERE=Path(__file__).resolve().parent;CORE=HERE.parents[1];sys.path.insert(0,str(CORE))
import pcm_levels
import audio_input
import simulation_refine
import quality


def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--node',required=True);parser.add_argument('--seed-fit',type=Path);args=parser.parse_args()
    root=args.baseline;out=args.output;out.mkdir(parents=True,exist_ok=True)
    report=json.loads((root/'report.json').read_bytes())
    command=report['ffmpeg_command'].copy();command[-1:-1]=['-af',audio_input.PAN_51]
    pcm=np.frombuffer(subprocess.run(command,capture_output=True,check=True).stdout,'<f4').astype(float)
    prepared,normalization=pcm_levels.process(pcm,ticks=15000,dynamics='compact')
    source=prepared[:300*22050]
    save(out/'source-processing.json',dict(downmix=audio_input.PAN_51,normalization=normalization,
        source_sha256=report['source_sha256'],reference_pcm_sha256=sha(source.astype('<f8').tobytes()),ffmpeg_command=command))
    quality.write_wav(out/'reference-preview.wav',source,22050)
    seed=args.seed_fit or root
    raw=gzip.decompress((seed/'registers.gz').read_bytes())
    previous=json.loads((seed/'stage-report.json').read_bytes()) if args.seed_fit else None
    assert sha(raw)==(previous['final_registers_sha256'] if previous else report['registers_sha256'])
    started=time.perf_counter()
    result,feedback=simulation_refine.optimize(source,raw,args.node,work_parent=out,register_bytes=report['register_bytes_per_state'],
        rounds=1 if previous else 3,tuning_cents=0 if previous else 25,
        calibration_gain=previous['feedback']['fixed_model_gain'] if previous else None)
    save(out/'final-feedback.json',feedback)
    (out/'registers.gz').write_bytes(gzip.compress(result,mtime=0))
    subprocess.run([args.node,str(CORE/'render_ym2149.js'),str(out/'registers.gz'),str(out/'audio.f32'),
        '50',str(out/'chip-render.json'),str(report['register_bytes_per_state'])],check=True)
    quality.write_wav(out/'ay-preview.wav',np.fromfile(out/'audio.f32','<f4').astype(float)*feedback['fixed_model_gain'],44100)
    (out/'audio.f32').unlink()
    save(out/'stage-report.json',dict(complete=True,source_processing=normalization,
        seed_registers_sha256=sha(raw),final_registers_sha256=sha(result),feedback=feedback,previous_feedback=previous['feedback'] if previous else None,
        register_bytes_per_state=report['register_bytes_per_state'],normalized_pcm_sha256=sha(source.astype('<f8').tobytes()),elapsed_seconds=time.perf_counter()-started,
        scope='Canonical full-render feedback against a newly downmixed and compressed reference; previous AY control stream reused only as an initial register seed.'))
    print(json.dumps(dict(complete=True,source_before=normalization['source_levels'],source_after=normalization['processed_levels'],
        before=feedback['baseline'],after=feedback['final'])),flush=True)


if __name__=='__main__':main()
