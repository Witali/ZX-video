"""Whole-song error budget and frozen-clock PDM controls; no release claims."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np

from assess_snr import ratio
from build_pdm import write_wav,CPU_CLOCK
from convert_mulaw_audio import STABLE_FILTER
from direct_player import HOLDS,layout
from ima_codec import decode
from probe_reconstruction_error import wav8
from ram_cache import PROFILES
from verify_direct import reference
from verify_pcm import save


def sha(data):return hashlib.sha256(data).hexdigest()


def filtered(values,times,ffmpeg,scratch,*,rate=768000,chunk=500000):
    """Same piecewise-constant integration as reconstruct, in bounded chunks.

    Keep one cumulative area on actual pulse edges. Uniform-bin integration
    uses exactly the same edge positions/search rule; carrying the previous
    endpoint avoids a reset or missing bin between chunks. FFmpeg filters the
    complete signal in one invocation, with no per-chunk filter restart.
    """
    times=np.asarray(times,dtype=float);levels=np.asarray(values,dtype=float)*2-1
    assert len(times)==len(levels)+1 and times[0]==0 and np.all(np.diff(times)>0)
    area=np.r_[0,np.cumsum(levels*np.diff(times))];count=int(np.floor(times[-1]*rate/CPU_CLOCK))
    with tempfile.TemporaryDirectory(dir=scratch,prefix='render-') as temporary:
        source=Path(temporary)/'signal.f64';output=Path(temporary)/'filtered.f64'
        with source.open('wb') as stream:
            previous=0.
            for first in range(0,count,chunk):
                stop=min(first+chunk,count);edges=np.arange(first+1,stop+1,dtype=float)*CPU_CLOCK/rate
                ids=np.minimum(np.searchsorted(times,edges,side='right')-1,len(levels)-1)
                integral=area[ids]+levels[ids]*(edges-times[ids])
                bins=np.diff(np.r_[previous,integral])/(CPU_CLOCK/rate)
                stream.write(bins.astype('<f8').tobytes());previous=integral[-1]
        subprocess.run([ffmpeg,'-v','error','-nostdin','-y','-f','f64le','-ar',str(rate),'-ac','1',
                        '-i',str(source),'-af',STABLE_FILTER,'-ar','44100','-f','f64le',str(output)],check=True)
        return np.fromfile(output,'<f8')


def metrics(wanted,actual,*,field_hz=50):
    assert len(wanted)==len(actual)
    stop=len(actual)-4410;wanted=wanted[4410:stop];actual=actual[4410:stop];error=actual-wanted
    time=np.arange(4410,stop)/44100.;phase=2*np.pi*field_hz*time;power=error*error
    c=float(2*np.mean(power*np.cos(phase)));s=float(2*np.mean(power*np.sin(phase)))
    signal_power=float(np.mean(wanted*wanted))
    return dict(snr_db=ratio(wanted,error) if signal_power>1e-24 else None,signal_rms=float(np.sqrt(signal_power)),
                error_rms=float(np.sqrt(np.mean(power))),error_power=float(np.mean(power)),
                error_power_field_component=float(np.hypot(c,s)),field_hz=field_hz,
                scope='Whole filtered signal except fixed100-ms edges; no fitted gain/delay/clock')


def uniform(values,end):
    period=CPU_CLOCK/8000;count=int(np.ceil(end/period))
    return np.pad(values,(0,max(0,count-len(values))),constant_values=.5)[:count],np.r_[np.arange(count)*period,end]


def prepare_inputs(repository,out):
    """Authenticate the actual baseline and its cover-only successor."""
    repository=Path(repository);old=repository/'audiobook-beeper/experiments/seamless-trd/evidence'
    manifest=json.loads((old/'manifest.json').read_bytes());dest=out/'inputs';dest.mkdir(exist_ok=True)
    names=['song/player.json','song/source-preview.wav','song/soundtrack.ima.gz','song/audio.trd',
           'song/audio-quality.json','inputs/prepared-song.wav']
    for profile in ('pentagon512','pentagon1024'):
        names.extend(f'song/verification/{profile}/{name}' for name in ('times.u32.gz','report.json'))
    identities={}
    for name in names:
        data=(old/name).read_bytes();record=manifest['artifact_files'][name]
        assert sha(data)==record['sha256'] and len(data)==record['bytes'],name
        target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);identities[name]=sha(data)
    current=(repository/'ZX-music-Sea-Foam-RAM-auto.trd').read_bytes();control=(dest/'song/audio.trd').read_bytes()
    frame=json.loads((repository/'audiobook-beeper/experiments/progress-frame/verification.json').read_bytes())
    assert sha(current)==frame['after_sha256'] and sha(control)==frame['before_sha256']
    changed=np.flatnonzero(np.frombuffer(current,'u1')!=np.frombuffer(control,'u1')).tolist()
    assert changed==frame['changed_disk_bytes'] and len(changed)==12
    (dest/'current-main.trd').write_bytes(current);save(dest/'cover-only-proof.json',frame)
    identities['current-main.trd']=sha(current);save(dest/'identities.json',identities)
    return dest


def run(repository,out,ffmpeg,scratch):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);scratch=Path(scratch);scratch.mkdir(parents=True,exist_ok=True)
    inputs=prepare_inputs(repository,out);root=inputs/'song';meta=json.loads((root/'player.json').read_bytes())
    source=wav8(root/'source-preview.wav');packed=gzip.decompress((root/'soundtrack.ima.gz').read_bytes())
    assert sha(packed)==meta['packed_sha256'] and len(source)==720384
    times=np.frombuffer(gzip.decompress((root/'verification/pentagon512/times.u32.gz').read_bytes()),'<u4').astype(float)
    other=np.frombuffer(gzip.decompress((root/'verification/pentagon1024/times.u32.gz').read_bytes()),'<u4')
    assert np.array_equal(times,other),'the two complete Pentagon clocks differ'
    times*=CPU_CLOCK/PROFILES['pentagon512']['cpu'];end=times[-1]
    sample_edges=np.r_[times[::16],end];sample_count=len(sample_edges)-1
    assert sample_count>=720000,'must retain the entire main song'
    pcm,_=decode(packed);target=source/256.;decoded=(pcm.astype(float)+32768)/65536
    values,edges=uniform(target,end);fixed=filtered(values,edges,ffmpeg,scratch)
    cache=scratch/'fixed.npy';np.save(cache,fixed)
    controls=[]
    def control(name,values,edges,description):
        output=filtered(values,edges,ffmpeg,scratch);row=dict(name=name,scope=description,metrics=metrics(fixed,output))
        controls.append(row);print(json.dumps(dict(control=name,**row['metrics'])),flush=True)
        return output
    timing=control('timing_only',target[:sample_count],sample_edges,'Ideal multilevel source DAC on saved actual sample clock; no codec/PDM')
    v,e=uniform(decoded,end);control('codec_uniform',v,e,'IMA4 PCM16 on an ideal8-kHz multilevel DAC; no player/PDM')
    on_clock=control('codec_actual_clock',decoded[:sample_count],sample_edges,'IMA4 PCM16 on saved actual sample clock; no PDM')
    del timing
    # Rounded measured slot means are a table control, not a new executed
    # clock. Include every source-bearing hold, including sparse bank tails.
    holds=np.diff(times);means=[float(holds[k::16].mean()) for k in range(16)]
    weights=np.rint(np.asarray(means)*8).astype(int).tolist()
    variants=[('legacy',dict(meta['model'])),
              ('zero_origin',dict(meta['model'],pcm_origin=0)),
              ('duration_zero_origin',dict(meta['model'],holds=weights,pcm_origin=0,weight_units='eighth Spectrum-reference T-state')),
              ('duration_zero_origin_half_recent',dict(meta['model'],holds=weights,pcm_origin=0,extent=.5,weight_units='eighth Spectrum-reference T-state'))]
    candidates=[];baseline=None
    for name,model in variants:
        decoded_pcm,_,_,bits=reference(packed,cycles=1,model=model)
        assert np.array_equal(decoded_pcm,pcm)
        output=filtered(bits[:len(times)-1],times,ffmpeg,scratch)
        result=dict(name=name,model=model,fixed_clock=metrics(fixed,output),
                    pdm_only_diagnostic=metrics(on_clock,output),
                    frozen_clock_prediction=name!='legacy',source_unchanged=True)
        if name=='legacy':
            expected=json.loads((root/'audio-quality.json').read_bytes())['fixed_clock_snr_db']
            assert abs(result['fixed_clock']['snr_db']-expected)<1e-8,(result['fixed_clock']['snr_db'],expected)
            baseline=output
        try:
            layout_data=layout(packed[:256],model,meta['hot_indices'])
            result['layout']=dict(reachable_feedback_states=len(layout_data[2]),first_patterns=len(layout_data[3]),second_patterns=len(layout_data[4]),
                                  fits_stream_state_limit=len(layout_data[2])<=18)
        except AssertionError as error:result['layout']=dict(fits_stream_state_limit=False,error=str(error))
        candidates.append(result);np.save(scratch/(name+'.npy'),output)
        write_wav(out/(name+'-frozen-clock.wav'),output*.5)
        print(json.dumps(result),flush=True)
        save(out/'partial.json',dict(complete=False,controls=controls,candidates=candidates))
    assert baseline is not None
    write_wav(out/'reference.wav',fixed*.5)
    chosen=max((r for r in candidates if r['layout']['fits_stream_state_limit']),key=lambda r:r['pdm_only_diagnostic']['snr_db'])
    report=dict(complete=True,date='2026-10-14',baseline_main_sha256=sha((inputs/'current-main.trd').read_bytes()),
                baseline_played_sha256=meta['trd_sha256'],packed_sha256=meta['packed_sha256'],samples=len(source),main_song_samples=720000,
                identical_complete_pentagon_clocks=True,source_gain_bandwidth_length_unchanged=True,
                measurement_filter=STABLE_FILTER,integration_rate_hz=768000,edge_exclusion_seconds=.1,
                fitted_gain_delay_clock=False,player_hot_path_change_tstates=0,physical_hardware_tested=False,
                whole_signal_seconds=end/CPU_CLOCK,ordinary_sample_tstates=449,page_extra_tstates=14,bank_extra_tstates=243,
                controls=controls,candidates=candidates,slot_means_reference_tstates=means,
                selected_for_actual_execution=chosen['name'],selection_basis='Highest PDM-only diagnostic among layout-feasible table controls; actual own-clock verification still required',
                scope='Complete90-second song; selected table predictions reuse the unchanged baseline clock and are not new execution or release proofs')
    save(out/'report.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--scratch',required=True,type=Path);p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    a=p.parse_args();run(a.repository,a.output,a.ffmpeg,a.scratch)


if __name__=='__main__':main()
