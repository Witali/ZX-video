"""Full-reference error budget for the 30-dB target, keeping IMA and duration.

These controls are diagnostic, not executable players or universal upper
bounds. Keep the established listening filter, gain, clock and edge policy.
Archive each measured stage; do not change the source or remove noisy passages.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from assess_snr import FILTER, ratio
from build_pdm import reconstruct, write_wav
from ima_beam import encode
from ima_codec import decode
from probe_reconstruction_error import wav8, filtered
from verify_direct import reference, sample_positions
from verify_pcm import save

HERE=Path(__file__).resolve().parent
MODULES=HERE.parents[1]
CPU=3546900


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def feedback(levels,beta,gain,holds=None):
    """High-precision control without the Spectrum table's state quantization.

    q preserves pulse-area error; recent supplies the extra feedback term.
    Weights are known hold lengths. This is NOT a finite-state Z80 solution.
    For uniform holds beta=1 reduces to exact second-difference feedback.
    """
    weights=np.ones(len(levels)) if holds is None else holds/np.mean(holds)
    out=np.empty(len(levels),dtype='u1');q=recent=peak=0.
    for i,(level,w) in enumerate(zip(levels,weights)):
        x=.5+gain*(level-.5)
        u=x+q/w+beta*recent;bit=int(u>=.5)
        recent=u-bit;q+=w*(x-bit);out[i]=bit
        peak=max(peak,abs(q),abs(recent))
        if peak>8:raise ValueError('overload in diagnostic feedback model')
    return out,peak


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--ffmpeg',required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'report.json').exists():raise ValueError('use a new output directory')
    base=HERE.parent/'ima-3bit-overlap/qualified'
    source=wav8(base/'source-preview.wav');n=len(source)
    rows=[];report=dict(date='2026-10-05',scope=__doc__,target_snr_db=30,
        source_samples=n,source_seconds=n/8000,source_pcm_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
        filter=FILTER,edge_exclusion_seconds=.1,reference='Unchanged prepared unsigned PCM8 / 8000 Hz',
        fitted_gain=False,fitted_delay=False,bandwidth_reduced=False,player_changed=False,
        producers={name:sha(MODULES/name) for name in ('assess_snr.py','build_pdm.py','ima_beam.py',
                   'ima_codec.py','probe_reconstruction_error.py','verify_direct.py')},
        script_sha256=sha(Path(__file__)),ffmpeg_sha256=sha(Path(a.ffmpeg)),rows=rows)
    def add(name,signal,target,scope,**more):
        output=filtered(signal,a.ffmpeg);ref=filtered(target,a.ffmpeg)
        assert len(output)==len(ref)
        cut=slice(4410,-4410);error=output[cut]-ref[cut]
        row=dict(name=name,snr_db=ratio(ref[cut],error),scope=scope,
                 signal_rms=float(np.sqrt(np.mean(ref[cut]**2))),
                 error_rms=float(np.sqrt(np.mean(error**2))),**more)
        rows.append(row);save(out/'report.json',report);print(json.dumps(row),flush=True)
        return output,ref
    # A/B isolation on each already executed disk's OWN measured clock.
    for codec,path in [('ima3',base),('ima4',HERE.parent/'ima-quality/speech4/selected')]:
        meta=json.loads((path/'player.json').read_bytes());assert np.array_equal(source,wav8(path/'source-preview.wav'))
        packed=gzip.decompress((path/'soundtrack.ima.gz').read_bytes())
        pcm,_,_,bits=reference(packed,model=meta['model'],idle_pairs=meta['loop_idle_pairs'])
        count=meta['outputs_per_cycle'];times=np.frombuffer(gzip.decompress((path/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:count+1]
        times-=times[0];bounds=times[sample_positions(meta)]
        count_fixed=int(np.ceil(times[-1]/(CPU/8000)))
        fixed=np.r_[np.arange(count_fixed)*(CPU/8000),times[-1]]
        original=reconstruct(np.pad(source/256,(0,max(0,count_fixed-n)),constant_values=.5)[:count_fixed],fixed)
        target=wav8(path/'compensated-pcm.wav');bins=meta['model'].get('pcm_bins',64)
        for stage,values in [('timing_control',target/256),('decoded_pcm16',(pcm.astype(float)+32768)/65536),
                              ('packet_input_midpoints',(np.floor((pcm.astype(float)+32768)/(65536/bins))+.5)/bins)]:
            add(codec+'_'+stage,reconstruct(values,bounds),original,
                'Ideal multilevel DAC on saved disk sample clock; diagnostic, not codec limit',
                saved_trd_sha256=sha(path/'audiobook-preview.trd'))
        output,ref=add(codec+'_actual_pdm',reconstruct(bits[:count],times),original,
                    'Recomputed first loop of previously fully checked Fuse disk',
                    saved_trd_sha256=sha(path/'audiobook-preview.trd'))
        expected=json.loads((path/'quality.json').read_bytes())['two_loop_clock_aware_snr_db'][0]
        assert abs(rows[-1]['snr_db']-expected)<1e-8
        write_wav(out/(codec+'-actual.wav'),output)
    # Fresh PCM-domain encodings avoid confusing waveform precompensation
    # with the intrinsic error of IMA. A bounded beam is not a global optimum.
    ideal_bounds=np.arange(n+1)*CPU/8000
    ideal_source=reconstruct(source/256,ideal_bounds)
    decoded={}
    for codec,codes in [('ima3',range(0,16,2)),('ima4',None)]:
        started=time.monotonic();packed=encode(source,width=64,allowed_codes=codes)
        pcm,_=decode(packed);decoded[codec]=(pcm.astype(float)+32768)/65536
        (out/(codec+'-pcm-search.ima.gz')).write_bytes(gzip.compress(packed,mtime=0))
        add(codec+'_pcm_beam64',reconstruct(decoded[codec],ideal_bounds),ideal_source,
            'Fresh PCM-error search, ideal multilevel DAC and fixed 8-kHz clock; no PDM/player',
            beam_width=64,block_samples=64,encode_seconds=time.monotonic()-started,
            packed_sha256=hashlib.sha256(packed).hexdigest(),disk_audio_bytes=n*(3 if codec=='ima3' else 4)//8)
    # Full-precision feedback controls isolate the table's input/state loss.
    # No higher bit rate, shorter source or alternative storage is proposed.
    times=np.arange(n*16+1)*CPU/128000
    for codec,levels in [('pcm_control',source/256),*decoded.items()]:
        held=np.repeat(levels,16)
        for beta,gain in ((.5,1.),(1.,.5)):
            bits,peak=feedback(held,beta,gain)
            add(f'{codec}_feedback_{beta:g}',reconstruct(bits,times),ideal_source*gain,
                'Ideal uniform 128-kHz host control with full-precision state; not executable on Z80',
                beta=beta,declared_gain=gain,state_peak=peak)
    save(out/'report.json',report)


if __name__=='__main__':main()
