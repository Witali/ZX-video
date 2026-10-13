"""Fit running hardware envelopes on the complete authenticated 300-s stream."""
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
import hardware_envelope


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--node',required=True)
    parser.add_argument('--resume-wave',type=Path,help='authenticated completed envelope-wave search before the disjoint ramp followup')
    args=parser.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    report=json.loads((args.baseline/'report.json').read_bytes())
    pcm=np.frombuffer(subprocess.run(report['ffmpeg_command'],capture_output=True,check=True).stdout,'<f4').astype(float)
    samples=pcm[:300*22050]*report['input_normalization']['gain_linear']
    assert hashlib.sha256(samples.astype('<f8').tobytes()).hexdigest()==report['input_normalization']['normalized_pcm_sha256']
    raw=gzip.decompress((args.baseline/'registers.gz').read_bytes())
    assert hashlib.sha256(raw).hexdigest()==report['registers_sha256']
    start=time.perf_counter()
    if args.resume_wave:
        info=json.loads((args.resume_wave/'hardware-envelope.json').read_bytes())
        result=gzip.decompress((args.resume_wave/'registers.gz').read_bytes())
        assert info['selected'] and info['initial_registers_sha256']==hashlib.sha256(raw).hexdigest()
        assert info['normalized_pcm_sha256']==report['input_normalization']['normalized_pcm_sha256']
        assert info['registers_sha256']==hashlib.sha256(result).hexdigest()
        result,ramps=hardware_envelope.add_ramps(samples,raw,result,args.node,work_parent=out,
            calibration_gain=report['fixed_model_gain'])
        info['ramp_followup']=ramps
        if ramps['selected']:
            rows=np.frombuffer(result,np.uint8).reshape(-1,14)
            info.update(final=ramps['final'],final_decision=info['final_decision']+' + '+ramps['final_decision'],
                blocks=info['blocks']+ramps['blocks'],envelope_channel_ticks=int(np.count_nonzero(rows[:,8:11]&16)),
                shape_restarts=int(np.count_nonzero(rows[:,13]!=255)))
        info['resumed_wave_search_authenticated']=True
    else:
        result,info=hardware_envelope.optimize(samples,raw,args.node,work_parent=out,
            calibration_gain=report['fixed_model_gain'])
    info.update(elapsed_seconds=time.perf_counter()-start,initial_registers_sha256=hashlib.sha256(raw).hexdigest(),
        registers_sha256=hashlib.sha256(result).hexdigest(),normalized_pcm_sha256=report['input_normalization']['normalized_pcm_sha256'])
    (out/'registers.gz').write_bytes(gzip.compress(result,mtime=0))
    (out/'hardware-envelope.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,selected=info['selected'],decision=info['final_decision'],
        baseline=info['baseline'],final=info['final'],envelope_channel_ticks=info['envelope_channel_ticks'],
        shape_restarts=info['shape_restarts'],elapsed_seconds=info['elapsed_seconds'])),flush=True)


if __name__=='__main__':main()
