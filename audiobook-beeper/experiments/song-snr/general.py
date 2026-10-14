"""Source-independent PDM benchmark and complete universal dictionary bounds.

Parameters follow counted instructions, never a particular song's waveform or
measured average. This is host feasibility research, not a new player release.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

from build_pdm import CPU_CLOCK,write_wav
from direct_player import HOLDS
from ima_beam import encode
from ima_codec import decode,require_unclipped
from probe_feedback_packets import integral_table
from probe_reconstruction_error import wav8
from verify_direct import reference
from verify_pcm import save

from study import filtered,metrics,sha


def models():
    pentagon=HOLDS.copy();pentagon[7]+=26
    return [('legacy',dict(holds=HOLDS,beta=.5,extent=1.)),
            ('zero_only',dict(holds=HOLDS,beta=.5,extent=1.,pcm_origin=0)),
            ('duration_midpoint',dict(holds=pentagon,beta=.5,extent=1.)),
            ('duration_zero',dict(holds=pentagon,beta=.5,extent=1.,pcm_origin=0)),
            ('duration_zero_half_recent',dict(holds=pentagon,beta=.5,extent=.5,pcm_origin=0))]


def catalogue(model):
    """Close over all64 input bins, not merely observed bins in one source."""
    words,nxt,peak=integral_table(64,2,holds=model['holds'],beta=model['beta'],extent=model['extent'],pcm_origin=model.get('pcm_origin',.5))
    reachable={16}
    while True:
        expanded=reachable|set(map(int,nxt[:,sorted(reachable)].ravel()))
        if expanded==reachable:break
        reachable=expanded
    used=words[:,sorted(reachable)]
    first=len(np.unique(used>>8));second=len(np.unique(used&255))
    code=first*42+second*64;fixed=256+1024+1088;startup=0x340
    reserve=((startup+code+255)//256)*256+fixed
    return dict(reachable_feedback_states=len(reachable),first_patterns=first,second_patterns=second,
                unrolled_pattern_code_bytes=code,packet_bytes_per_bin=len(reachable)*6,
                current_protected_state_limit_passed=len(reachable)<=18,
                resident_bytes_before_worker=reserve,current_worker_start_bytes=14336,
                current_layout_fits=len(reachable)<=18 and reserve<=14336,
                q_clip=[0,15],table_internal_peak=peak,
                bound_scope='Every representable PCM bin and every reachable table state; source independent')


def signals(repository,out):
    n=16384;t=np.arange(n)/8000
    tone=lambda frequency,amplitude:128+128*amplitude*np.sin(2*np.pi*frequency*t)
    tests=[('silence','development',np.full(n,128.)),
           ('quiet440','development',tone(440,4/128)),
           ('loud3000','development',tone(3000,.75)),
           ('steps','development',np.where((np.arange(n)//256)%2,220.,36.)),
           ('quiet997','holdout',tone(997,2/128)),
           ('multitone','holdout',128+128*(.32*np.sin(2*np.pi*311*t)+.24*np.sin(2*np.pi*1709*t)+.14*np.sin(2*np.pi*3299*t)))]
    # Freeze the same parameter sets before opening these unrelated sources.
    for name,path in [('speech','audiobook-beeper/experiments/ima-waveform/source-preview.wav'),
                      ('entertainer','audiobook-beeper/experiments/ima-quality/music4/selected/source-preview.wav'),
                      ('sea_foam','audiobook-beeper/experiments/seamless-trd/evidence/song/source-preview.wav')]:
        tests.append((name,'holdout',wav8(Path(repository)/path)))
    inputs=out/'inputs';inputs.mkdir(exist_ok=True)
    result=[]
    for name,split,values in tests:
        pcm=np.clip(np.rint(values),0,255).astype('u1');synthetic=len(pcm)==n
        if synthetic:
            # Universal final guard; no content filtering/gain normalization.
            pcm=np.r_[pcm,np.full(512,128,'u1')]
        dest=inputs/(name+'.wav')
        from convert_audio import pcm_wav
        pcm_wav(dest,pcm)
        result.append(dict(name=name,split=split,pcm=pcm,path=dest,sha256=sha(pcm.tobytes()),samples=len(pcm),synthetic=synthetic))
    return result


def timeline(samples,profile):
    """Instruction-table schedules; no data-dependent ULA or ROM model.

   128 uses the existing423-T ordinary path. Pentagon retains counted26-T
    pacing. All controls include page crossings and current descriptor bank
    tails, in a full-RAM batch. Uniform multilevel references follow this
    same sample clock solely to isolate modulation/codec error.
    """
    from build_stream_trd import sections
    holds=np.tile(HOLDS,samples).astype(np.int64)
    if profile=='pentagon':holds[7::16]+=26;cpu=3584000;pages=24
    else:cpu=3546900;pages=0
    offset=0;remaining=samples//2
    while remaining:
        batch,remaining=sections(remaining,pages)
        for s in batch:
            for byte in range(256,s['bytes']+1,256):
                k=(2*(offset+byte)-3)*16+14
                if k<len(holds):holds[k]+=243 if byte==s['bytes'] else 14
            offset+=s['bytes']
    return np.r_[0,np.cumsum(holds)]*CPU_CLOCK/cpu


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--scratch',required=True,type=Path);p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);a.scratch.mkdir(parents=True,exist_ok=True)
    presets=models();bounds={name:catalogue(model) for name,model in presets}
    frozen=sha(json.dumps(presets,sort_keys=True).encode());save(out/'frozen-parameters.json',dict(models=presets,sha256=frozen,catalogues=bounds))
    corpus=signals(a.repository,out);rows=[]
    for source in corpus:
        pcm8=source.pop('pcm');name=source['name'];packed_path=out/'inputs'/(name+'.ima.gz')
        if packed_path.exists():packed=gzip.decompress(packed_path.read_bytes())
        elif name=='sea_foam':packed=gzip.decompress((a.repository/'audiobook-beeper/experiments/seamless-trd/evidence/song/soundtrack.ima.gz').read_bytes())
        else:packed=encode(pcm8,width=32,block_samples=64)
        assert len(packed)*2==len(pcm8);guard=require_unclipped(packed)
        packed_path.write_bytes(gzip.compress(packed,mtime=0));decoded,_=decode(packed)
        # Require representable zero guard without concealing unstable states.
        assert (decoded[-1],decode(packed)[1][-1])==(0,0)
        times=timeline(len(pcm8),'pentagon');samples=times[::16]
        held=filtered((decoded.astype(float)+32768)/65536,samples,a.ffmpeg,a.scratch)
        original=filtered(pcm8/256,samples,a.ffmpeg,a.scratch)
        source['path']=str(source['path'].relative_to(out));source['packed_sha256']=sha(packed);source['codec_diagnostic']=metrics(original,held)
        results=[]
        for label,model in presets:
            _,_,_,bits=reference(packed,cycles=1,model=model)
            output=filtered(bits[:len(times)-1],times,a.ffmpeg,a.scratch)
            m=metrics(held,output);total=metrics(original,output)
            if np.std(held[4410:-4410])<1e-9:m['snr_db']=None;total['snr_db']=None
            row=dict(model=label,pdm_only=m,total_on_shared_clock=total,layout_fits=bounds[label]['current_layout_fits'])
            results.append(row)
            if source['split']=='holdout' and label in ('legacy','duration_midpoint','duration_zero_half_recent'):
                write_wav(out/(name+'-'+label+'.wav'),output*.5)
        rows.append(dict(source=source,models=results,saturation_guard=guard))
        print(json.dumps(dict(source=name,models=[dict(model=r['model'],pdm_snr=r['pdm_only']['snr_db'],total_snr=r['total_on_shared_clock']['snr_db'],noise_rms=r['pdm_only']['error_rms']) for r in results])),flush=True)
        save(out/'partial.json',dict(complete=False,rows=rows))
    assert sha(json.dumps(presets,sort_keys=True).encode())==frozen
    report=dict(complete=True,date='2026-10-14',source_independent_parameters=True,frozen_parameter_sha256=frozen,
                source_specific_fitted_gain_delay_clock=False,models=presets,catalogues=bounds,rows=rows,
                scope='Whole-corpus host controls on instruction-derived Pentagon schedule; no ULA/new Z80 execution or release proof',
                ordinary_tstates=449,page_extra_tstates=14,bank_extra_tstates=243,player_hot_path_tstates_delta=0,
                reference_scope='Shared sample-clock diagnostics isolate codec/PDM; not fixed8-kHz release SNR',
                finite_corpus_is_not_a_universal_guarantee=True,physical_hardware_tested=False)
    save(out/'report.json',report)


if __name__=='__main__':main()
