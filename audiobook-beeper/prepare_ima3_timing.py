"""Compensate a measured IMA3 disk clock on the PC, then rebuild and recalibrate."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import time
import wave
import numpy as np
from build_ima3_disk import write_candidate
from convert_audio import calibrate, pcm_wav
from ima_codec import decode, require_unclipped
from precompensate_voice import compensate
from probe_dense_codecs import encode3
from verify_direct import sample_positions
from verify_pcm import save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot',required=True,type=Path); p.add_argument('--output',required=True,type=Path)
    p.add_argument('--fuse',required=True,type=Path); a=p.parse_args()
    if a.output.exists() and any(a.output.iterdir()): p.error('output must be empty')
    a.output.mkdir(parents=True)
    meta=json.loads((a.pilot/'player.json').read_bytes())
    with wave.open(str(a.pilot/'source-preview.wav'),'rb') as w:
        assert w.getsampwidth()==w.getnchannels()==1 and w.getframerate()==8000
        source=np.frombuffer(w.readframes(w.getnframes()),'u1')
    times=np.frombuffer(gzip.decompress((a.pilot/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
    target=compensate(source,times[sample_positions(meta)],period=3546900/8000)
    pcm_wav(a.output/'compensated-pcm.wav',target)
    started=time.monotonic(); codes,expected=encode3(target,(-1,-1,2,6))
    nibbles=codes<<1; packed=(nibbles[::2]|(nibbles[1::2]<<4)).tobytes()
    actual,index=decode(packed)
    assert np.array_equal(actual,expected)
    assert (actual[-1],index[-1])==(0,0),'compensated stream must settle naturally'
    require_unclipped(packed)
    report=dict(pilot=str(a.pilot),samples=len(source),source_sha256=hashlib.sha256(source).hexdigest(),
        compensated_sha256=hashlib.sha256(target).hexdigest(),encoding_seconds=time.monotonic()-started,
        host_only=True,player_tstate_delta=0,hot_rows_frozen=True,complete=False)
    save(a.output/'precompensation.json',report); print(json.dumps(report),flush=True)
    selected,new_meta=calibrate(a.output/'calibration',packed,source,a.fuse,meta['hot_indices'],writer=write_candidate)
    for name in ('player.json','audiobook-preview.trd','soundtrack.ima.gz','soundtrack.ima3.gz','source-preview.wav','phase-probe.json'):
        shutil.copy2(selected/name,a.output/name)
    shutil.copytree(selected/'assembly',a.output/'assembly')
    report.update(complete=True,selected=str(selected.relative_to(a.output)),
                  full_playback_validation_required=True)
    save(a.output/'precompensation.json',report)


if __name__=='__main__': main()
