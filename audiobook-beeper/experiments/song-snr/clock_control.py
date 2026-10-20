"""Generic deterministic-clock compensation and joint IMA/PDM host controls.

The source remains the original uniform8-kHz PCM. Only the encoding prior is
resampled onto an instruction-derived Pentagon schedule. Final scores use the
unrounded schedule, unchanged listening filter and no fitted delay/gain. Host
predictions must be followed by complete own-clock player execution.
"""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import time

import numpy as np

from build_pdm import CPU_CLOCK,write_wav
from ima_beam import encode
from ima_codec import require_unclipped
from ima_waveform_encoder import WaveformModel,encode_waveform
from precompensate_voice import compensate
from probe_feedback_packets import integral_table
from probe_reconstruction_error import wav8
from verify_direct import reference
from verify_pcm import save

from general import models,timeline
from study import filtered,metrics,sha,uniform


PARAMETERS=dict(profile='pentagon',source_rate_hz=8000,lanczos_radius=16,
                pcm_beam_width=32,pcm_block_samples=64,waveform_beam_width=32,
                horizon_samples=128,commit_samples=64,regularization=.1,
                model_name='duration_zero_half_recent',search_query_grid_tstates=1/80,
                source_specific_fitted_clock_gain_delay=False)


def prepare(source,times,model,*,backend='python'):
    """Build analytic search features from the complete closed packet table.

    Pentagon times are expressed in Spectrum-reference T states. Rounding only
    search quadrature queries to the existing1/80-T lookup grid introduces at
    most1.763 ns; the final renderer and all clocks remain unrounded. The
    explicit native backend preserves every float64 row and query result;
    Python remains the independent default and needs no C compiler.
    """
    if backend not in ('python','native'):
        raise ValueError('preparation backend must be python or native')
    if backend=='native':
        from native_waveform_prepare import reference,unique_holds
    count=len(source)-128
    assert np.all(source[-128:]==128),'settling tail must contain no source content'
    holds=np.diff(times)[:count*16].reshape(count,16)
    unique,ids=(unique_holds(holds) if backend=='native' else
                np.unique(holds,axis=0,return_inverse=True))
    words,nxt,_=integral_table(64,2,holds=model['holds'],beta=model['beta'],
                              extent=model['extent'],pcm_origin=model.get('pcm_origin',.5))
    shifts=np.arange(15,-1,-1)
    signed=((words.ravel()[:,None]>>shifts)&1).astype(float)*2-1
    analog=WaveformModel();features=[]
    for row in unique:
        a,b,l,r=analog.packet(row)
        features.append((a,l,signed@r.T,signed@b.T,row/(CPU_CLOCK/8000)))
    queries=((times[:count*16]+times[1:count*16+1])/2).reshape(count,16)
    rounded=np.rint(queries*80)/80
    desired=(reference(analog,source,rounded) if backend=='native' else
             analog.reference(source,rounded))
    return desired,features,ids,nxt,float(np.max(abs(queries-rounded))/CPU_CLOCK)


def score(source,packed,model,times,ffmpeg,scratch):
    # Match the actual pipeline: final33 settling outputs never reach OUT.
    count=(len(source)-3)*16+15;edges=times[:count]
    _,_,_,bits=reference(packed,cycles=1,model=model)
    actual=filtered(bits[:count-1],edges,ffmpeg,scratch)
    values,fixed_edges=uniform(source/256,edges[-1])
    wanted=filtered(values,fixed_edges,ffmpeg,scratch)
    return metrics(wanted,actual),wanted,actual


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('evidence',type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--scratch',required=True,type=Path)
    p.add_argument('--source',action='append');p.add_argument('--method',choices=('compensation','joint'),default='compensation')
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'));p.add_argument('--resume',action='store_true')
    a=p.parse_args();root=a.evidence.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    a.scratch.mkdir(parents=True,exist_ok=True)
    model=dict(models())[PARAMETERS['model_name']]
    frozen=dict(parameters=PARAMETERS,model=model,method=a.method)
    save(out/'parameters.json',dict(**frozen,sha256=sha(json.dumps(frozen,sort_keys=True).encode())))
    names=a.source or ['silence','quiet440','loud3000','steps','quiet997','multitone','speech','entertainer','sea_foam']
    rows=[]
    for name in names:
        dest=out/name;dest.mkdir(exist_ok=True)
        if a.resume and (dest/'host.json').exists():
            rows.append(json.loads((dest/'host.json').read_bytes()));continue
        started=time.monotonic();source=wav8(root/'general/inputs'/(name+'.wav'))
        times=timeline(len(source),'pentagon')
        target=compensate(source,times[::16],radius=PARAMETERS['lanczos_radius'],period=CPU_CLOCK/8000)
        assert np.all(target[-128:]==128),'last guard cannot overwrite content'
        statistics={};quantization=0.
        if a.method=='joint':
            desired,features,ids,nxt,quantization=prepare(source,times,model)
            print(json.dumps(dict(source=name,prepared=True,packet_shapes=len(features))),flush=True)
            packed=encode_waveform(target,desired,features,ids,nxt,width=PARAMETERS['waveform_beam_width'],
                    block_size=PARAMETERS['horizon_samples'],commit_size=PARAMETERS['commit_samples'],
                    regularization=PARAMETERS['regularization'],statistics=statistics)
        else:packed=encode(target,width=PARAMETERS['pcm_beam_width'],block_samples=PARAMETERS['pcm_block_samples'])
        guard=require_unclipped(packed);assert len(packed)*2==len(source)
        encoding_seconds=time.monotonic()-started
        (dest/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
        (dest/'source-preview.wav').write_bytes((root/'general/inputs'/(name+'.wav')).read_bytes())
        from convert_audio import pcm_wav
        pcm_wav(dest/'compensated-pcm.wav',target)
        result,wanted,actual=score(source,packed,model,times,a.ffmpeg,a.scratch)
        baseline=gzip.decompress((root/'general/inputs'/(name+'.ima.gz')).read_bytes())
        before,_,_=score(source,baseline,dict(models())['legacy'],times,a.ffmpeg,a.scratch)
        write_wav(dest/'host-actual.wav',actual*.5);write_wav(dest/'reference.wav',wanted*.5)
        np.save(a.scratch/(name+'-'+a.method+'-actual.npy'),actual)
        np.save(a.scratch/(name+'-reference.npy'),wanted)
        row=dict(source=name,method=a.method,parameters=PARAMETERS,model=model,
                 source_samples=len(source),source_sha256=sha(source.tobytes()),packed_sha256=sha(packed),
                 fixed_clock=result,baseline_fixed_clock=before,
                 change_db=None if result['snr_db'] is None else result['snr_db']-before['snr_db'],
                 encoding_seconds=encoding_seconds,elapsed_seconds=time.monotonic()-started,
                 statistics=statistics,max_search_query_quantization_seconds=quantization,
                 original_content_preserved=True,saturation_guard=guard,host_prediction=True,
                 scope='Entire source on instruction-derived Pentagon timeline, not new emulator execution',
                 ordinary_tstates=449,page_extra_tstates=14,bank_extra_tstates=243,hot_path_delta_tstates=0)
        save(dest/'host.json',row);rows.append(row)
        print(json.dumps(dict(source=name,method=a.method,snr_db=result['snr_db'],before_db=before['snr_db'],
                              noise_rms=result['error_rms'],encoding_seconds=encoding_seconds)),flush=True)
        save(out/'partial.json',dict(complete=False,rows=rows))
    save(out/'report.json',dict(complete=True,rows=rows,source_independent_parameters=True,emulator_verified=False))


if __name__=='__main__':main()
