"""Retarget authenticated register seeds to real AY DAC feedback and sparse noise.

Reuse previous component/colour proposals only as valid register seeds. The
complete source-versus-simulation feedback, noise policy and hardware envelope
search are calculated anew using the AY model and its 16-level DAC.
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
import simulation_refine
import noise_gate
import hardware_envelope


def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--node',required=True);args=parser.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    report=json.loads((args.baseline/'report.json').read_bytes())
    pcm=np.frombuffer(subprocess.run(report['ffmpeg_command'],capture_output=True,check=True).stdout,'<f4').astype(float)
    samples=pcm[:300*22050]*report['input_normalization']['gain_linear']
    assert sha(samples.astype('<f8').tobytes())==report['input_normalization']['normalized_pcm_sha256']
    initial=gzip.decompress((args.baseline/'registers.gz').read_bytes())
    assert sha(initial)==report['registers_sha256'] and len(initial)==15000*11
    states=json.loads(gzip.decompress((args.baseline/'channel-states.json.gz').read_bytes()))['states']
    started=time.perf_counter()
    refined,feedback=simulation_refine.optimize(samples,initial,args.node,work_parent=out)
    save(out/'simulation-feedback.json',feedback)
    (out/'feedback-registers.gz').write_bytes(gzip.compress(refined,mtime=0))
    toned,policy=noise_gate.optimize(samples,refined,args.node,noise_shares=[s['noise_share'] for s in states],
        work_parent=out,calibration_gain=feedback['fixed_model_gain'])
    save(out/'necessary-noise.json',policy)
    result,envelope=hardware_envelope.optimize(samples,toned,args.node,work_parent=out,calibration_gain=feedback['fixed_model_gain'])
    envelope.update(initial_registers_sha256=sha(toned),registers_sha256=sha(result),
        normalized_pcm_sha256=report['input_normalization']['normalized_pcm_sha256'])
    save(out/'hardware-envelope.json',envelope)
    (out/'pre-envelope-registers.gz').write_bytes(gzip.compress(toned,mtime=0))
    (out/'registers.gz').write_bytes(gzip.compress(result,mtime=0))
    save(out/'stage-report.json',dict(complete=True,target_chip='AY-3-8910/8912',distinct_envelope_levels=16,
        source_sha256=report['source_sha256'],normalized_pcm_sha256=report['input_normalization']['normalized_pcm_sha256'],
        seed_registers_sha256=sha(initial),seed_scope='previous YM-fitted component/colour controls; all final feedback rerun on AY',
        final_registers_sha256=sha(result),elapsed_seconds=time.perf_counter()-started,
        baseline=feedback['baseline'],final=envelope.get('final',policy['final']),
        noise_policy=policy,simulation_feedback=feedback,hardware_envelope=envelope))
    print(json.dumps(dict(complete=True,chip='AY',noise_before=policy['noise_ticks_before'],noise_after=policy['noise_ticks_after'],
        before=feedback['baseline'],after=envelope.get('final',policy['final']),elapsed_seconds=time.perf_counter()-started)),flush=True)


if __name__=='__main__':main()
