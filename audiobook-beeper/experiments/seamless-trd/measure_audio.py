"""Render the complete verified512K song timeline; retain strict fixed clock."""
import argparse
import gzip
import json
from pathlib import Path
import shutil

import numpy as np

from assess_snr import ratio
from build_pdm import write_wav
from convert_mulaw_audio import filter_signal,STABLE_FILTER
from probe_reconstruction_error import wav8
from ram_cache import PROFILES
from verify_direct import reference
from verify_pcm import save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path)
    a=p.parse_args();root=a.directory.resolve();meta=json.loads((root/'player.json').read_bytes())
    verified=json.loads((root/'verification/pentagon512/report.json').read_bytes())
    assert verified['complete'] and verified['reloads']==0 and verified['trd_sha256']==meta['trd_sha256']
    packed=gzip.decompress((root/'soundtrack.ima.gz').read_bytes());_,_,_,bits=reference(packed,cycles=1,model=meta['model'])
    times=np.frombuffer(gzip.decompress((root/'verification/pentagon512/times.u32.gz').read_bytes()),'<u4').astype(float)
    assert len(times)==verified['bits_verified']
    edges=times*3546900/PROFILES['pentagon512']['cpu'];ffmpeg=shutil.which('ffmpeg');assert ffmpeg
    output=filter_signal(bits[:len(times)-1],edges,ffmpeg,768000)
    source=wav8(root/'source-preview.wav');period=3546900/8000
    n=int(np.ceil(edges[-1]/period));fixed_edges=np.r_[np.arange(n)*period,edges[-1]]
    values=np.pad(source/256,(0,max(0,n-len(source))),constant_values=.5)[:n]
    fixed=filter_signal(values,fixed_edges,ffmpeg,768000)
    # No fitted clock, delay, gain, skipped block boundary or shortened source.
    window=slice(4410,-4410);score=ratio(fixed[window],output[window]-fixed[window])
    write_wav(root/'output-pentagon512.wav',output)
    save(root/'audio-quality.json',dict(complete=True,source_scope='whole90-second main song plus final guard',
                                      fixed_clock_snr_db=score,strict_20db_gate_passed=score>=20,
                                      fitted_clock_delay_gain=False,filter=STABLE_FILTER,integration_rate_hz=768000,
                                      scope='Listening preview in unchanged original PDM model; not a20-dB quality release',
                                      verified_trd_sha256=meta['trd_sha256']))
    print(score,flush=True)


if __name__=='__main__':main()
