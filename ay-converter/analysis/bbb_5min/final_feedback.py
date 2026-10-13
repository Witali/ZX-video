"""Final canonical fixed-gain feedback after conservative noise and envelopes."""
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
HERE=Path(__file__).resolve().parent;CORE=HERE.parents[1];sys.path.insert(0,str(CORE))
import simulation_refine


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path);parser.add_argument('fit',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--node',required=True);args=parser.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    report=json.loads((args.baseline/'report.json').read_bytes());stage=json.loads((args.fit/'stage-report.json').read_bytes())
    pcm=np.frombuffer(subprocess.run(report['ffmpeg_command'],capture_output=True,check=True).stdout,'<f4').astype(float)
    samples=pcm[:300*22050]*report['input_normalization']['gain_linear']
    assert hashlib.sha256(samples.astype('<f8').tobytes()).hexdigest()==stage['normalized_pcm_sha256']
    raw=gzip.decompress((args.fit/'registers.gz').read_bytes())
    assert hashlib.sha256(raw).hexdigest()==stage['final_registers_sha256']
    width=stage['hardware_envelope'].get('register_bytes',11);start=time.perf_counter()
    result,feedback=simulation_refine.optimize(samples,raw,args.node,work_parent=out,
        register_bytes=width,calibration_gain=stage['simulation_feedback']['fixed_model_gain'])
    for name in ('simulation-feedback.json','necessary-noise.json','hardware-envelope.json','pre-envelope-registers.gz'):
        shutil.copyfile(args.fit/name,out/name)
    (out/'registers.gz').write_bytes(gzip.compress(result,mtime=0))
    (out/'before-final-registers.gz').write_bytes(gzip.compress(raw,mtime=0))
    (out/'final-feedback.json').write_text(json.dumps(feedback,indent=2)+'\n',encoding='utf-8',newline='\n')
    stage.update(final_feedback=feedback,final=feedback['final'],final_registers_sha256=hashlib.sha256(result).hexdigest(),
        final_feedback_elapsed_seconds=time.perf_counter()-start,register_bytes_per_state=width)
    (out/'stage-report.json').write_text(json.dumps(stage,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,before=feedback['baseline'],after=feedback['final'],elapsed_seconds=time.perf_counter()-start)),flush=True)


if __name__=='__main__':main()
