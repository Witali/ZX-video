"""Measure the fixed analytic shortlist against five archived full searches."""
import gzip
import json
from pathlib import Path
import sys
import time
import numpy as np
import build
import fast_mixer
import noise_colour


def main():
    node=sys.argv[1]; output=Path(sys.argv[2]); output.mkdir(parents=True,exist_ok=True)
    archive=build.CORE/'analysis/auto_mixer/evidence'
    noise_colour.spectra_at=build.bounded_spectra(noise_colour.spectra_at)
    cases={}
    for name in ('entertainer','o-henry','movie-60','movie-170','movie-430'):
        root=archive/name; saved=np.load(root/'input.npz'); lo=int(saved['start_tick'])*441; count=int(saved['ticks'])
        pcm=saved['pcm'].astype(float)[lo:lo+count*441]
        states=json.loads(gzip.decompress((root/'music/channel-states.json.gz').read_bytes()))['states']
        raw=gzip.decompress((root/'music/registers.gz').read_bytes())
        baseline=np.frombuffer(raw,np.uint8).reshape(-1,11)
        start=time.perf_counter()
        result,info=fast_mixer.optimize(pcm,raw,node,
            tone_volumes=[s['tone_volumes'] for s in states],noise_shares=[s['noise_share'] for s in states],
            carriers=[s['noise_channel'] for s in states],work_parent=output)
        rows=np.frombuffer(result,np.uint8).reshape(-1,11)
        assert len(result)==len(raw) and np.array_equal(rows[:,:6],baseline[:,:6])
        assert np.all(rows[:,6]<=31) and np.all(rows[:,7]<=63) and np.all(rows[:,8:]<=15)
        errors=info['final_multiresolution_log_mae_db']
        assert min(errors.values())<=errors['seed']+1e-12
        full=json.loads(gzip.decompress((root/'auto/mixer-fit.json.gz').read_bytes()))
        folder=output/name; folder.mkdir(exist_ok=True)
        (folder/'registers.gz').write_bytes(gzip.compress(result,mtime=0))
        (folder/'fit.json.gz').write_bytes(gzip.compress(json.dumps(info).encode(),mtime=0))
        cases[name]=dict(ticks=count,candidates=20,elapsed_seconds=time.perf_counter()-start,
            seed_error_db=errors['seed'],shortlist_error_db=min(errors.values()),
            full_374_error_db=min(full['final_multiresolution_log_mae_db'].values()),
            final_decision=info['final_decision'],tone_periods_exact=True,registers_valid=True)
        print(name,json.dumps(cases[name]),flush=True)
    report=dict(complete=True,date='2026-10-13',cases=cases,
                limits='The shortlist can miss a full-search optimum. Seed fallback checked on every complete excerpt; no perceptual equivalence claim.')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__': main()
