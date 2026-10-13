"""Whole-render feedback on the five existing, complete eight-second cases."""
import gzip
import json
from pathlib import Path
import sys
import time
import numpy as np

HERE=Path(__file__).resolve().parent
CORE=HERE.parents[1]
sys.path.insert(0,str(CORE))
import simulation_refine
import psychoacoustic


def main():
    node=sys.argv[1];output=Path(sys.argv[2]);output.mkdir(parents=True,exist_ok=True)
    archive=CORE/'analysis/auto_mixer/evidence'
    cases={}
    for name in ('entertainer','o-henry','movie-60','movie-170','movie-430'):
        saved=np.load(archive/name/'input.npz');lo=int(saved['start_tick'])*441;count=int(saved['ticks'])
        pcm=saved['pcm'].astype(float)[lo:lo+count*441]
        gain=10**(-1/20)/max(float(abs(pcm).max()),1e-12)
        raw=gzip.decompress((HERE/'shortlist-validation'/name/'registers.gz').read_bytes())
        start=time.perf_counter()
        result,info=simulation_refine.optimize(pcm*gain,raw,node,work_parent=output)
        rows=np.frombuffer(result,np.uint8).reshape(-1,11)
        assert info['final']['objective_db']<=info['baseline']['objective_db']+1e-12
        assert len(rows)==count and np.all(rows[:,8:]<=15) and np.all(rows[:,6]<=31)
        root=output/name;root.mkdir(exist_ok=True)
        (root/'registers.gz').write_bytes(gzip.compress(result,mtime=0))
        (root/'simulation-feedback.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8',newline='\n')
        cases[name]=dict(ticks=count,before=info['baseline'],after=info['final'],
            changed_volume_registers=info['changed_volume_registers'],changed_tone_periods=info['changed_tone_periods'],
            changed_noise_ticks=info['changed_noise_ticks'],elapsed_seconds=time.perf_counter()-start,
            registers_valid=True,complete_continuous_render=True)
        print(name,json.dumps(cases[name]),flush=True)
    report=dict(complete=True,date='2026-10-13',cases=cases,psychoacoustic=psychoacoustic.MODEL,
        scope='Canonical feedback only; previous complete analytic-20 streams, peak-normalized references; not new complete component/noise fitting or a listening grade.')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
