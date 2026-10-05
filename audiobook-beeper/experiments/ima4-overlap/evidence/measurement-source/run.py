"""Matched IMA4 overlap experiment; keep IMA3 and both Z80 kernels unchanged."""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
MODULES=HERE.parents[1]
sys.path.insert(0,str(MODULES))
from convert_audio import calibrate, validate, write_candidate, pcm_wav, independent_ima_check, snapshot_sources
from convert_ima3_audio import stage
from probe_reconstruction_error import wav8
from precompensate_voice import compensate
from verify_direct import reference, sample_positions
from probe_feedback_packets import model_table, integral_table
from convert_mulaw_audio import filter_signal
from build_pdm import write_wav
from assess_snr import ratio
from verify_pdm import save
from analyze_ima_boundaries import read_wav, boundary_metrics

PREVIOUS=HERE.parent/'ima-quality'
CLOCK=PREVIOUS/'speech4/selected'
CACHED=PREVIOUS/'paused/speech4-refined'


def read(path):return json.loads(path.read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def authenticate_cached(out):
    """Import a frozen completed candidate, never mark its partial disk test done.

    Do not bypass the old run.py resume identity. Later SD2 support changed
    producer hashes. Check the unchanged search AST/native kernel and the
    exact legacy table dispatch, retain the original identity, then rebuild
    and fully execute the candidate under the current verifier.
    """
    identity=read(CACHED/'identity.json');host=read(CACHED/'encode-1/report.json')
    assert sha(CLOCK/'output-times.u32.gz')==identity['baseline_clock']
    assert sha(CLOCK/'source-preview.wav')==identity['source']
    assert host['beam_width']==512 and host['block_size']==128 and host['commit_size']==64
    assert host['control_regularization']==.03 and not host['ima3_subset']
    for name,digest in read(CACHED/'encode-1/stage-complete.json').items():
        assert sha(CACHED/'encode-1'/name)==digest,name
    packed=gzip.decompress((CACHED/'encode-1/soundtrack.ima.gz').read_bytes())
    assert hashlib.sha256(packed).hexdigest()==host['packed_sha256']
    snapshots=PREVIOUS/'final-producer-source'
    old=gzip.decompress((snapshots/'ima_waveform_encoder.py.gz').read_bytes()).decode()
    new=(MODULES/'ima_waveform_encoder.py').read_text()
    def functions(source):
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(source).body
                if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    before,after=functions(old),functions(new)
    checked=['encode_waveform','_best_unique','WaveformModel']
    assert all(before[name]==after[name] for name in checked)
    unchanged=['waveform_kernel.py','quality_search.py','ima_codec.py','ima_beam.py',
               'probe_reconstruction_error.py','build_pdm.py','assess_snr.py']
    for name in unchanged:
        assert (MODULES/name).read_bytes().replace(b'\r\n',b'\n')==gzip.decompress((snapshots/(name+'.gz')).read_bytes())
    model=read(CLOCK/'player.json')['model']
    assert model.get('family')!='sigma_delta2' and not model.get('reset_feedback_in_guard')
    assert model.get('output_gain',1.)==1.
    current=model_table(model)
    legacy=integral_table(model.get('pcm_bins',64),2,holds=model['holds'],beta=model['beta'],extent=model['extent'],q_clip=tuple(model.get('q_clip',(0,15))))
    for a,b in zip(current[:2],legacy[:2]):np.testing.assert_array_equal(a,b)
    out.mkdir(parents=True,exist_ok=True)
    save(out/'cached-input-audit.json',dict(complete=True,original_identity=identity,host=host,
        exact_search_ast=checked,unchanged_modules=unchanged,legacy_tables_exact=True,
        output_gain=1,old_disk_verification_reused=False,
        distinction='Frozen authenticated input candidate; not a resume under mismatched producer hashes'))
    return packed


def qualify(out, packed, fuse, ffmpeg, old_phase=None):
    out.mkdir(parents=True,exist_ok=False);snapshot_sources(out)
    source=wav8(CLOCK/'source-preview.wav');base=read(CLOCK/'player.json')
    if old_phase:
        previous=read(old_phase/'player.json')
        disk,meta=write_candidate(out/'verified',packed,source,previous['hot_indices'],
                                 previous['loop_idle_pairs'],previous['loop_idle_pad_tstates'])
        assert disk==(old_phase/'audiobook-preview.trd').read_bytes(), 'rebuild changed the frozen candidate'
        selected=out/'verified'
    else:
        selected,meta=calibrate(out/'calibration',packed,source,fuse,base['hot_indices'])
    quality=validate(selected,fuse,ffmpeg)
    t=np.frombuffer(gzip.decompress((selected/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
    pcm_wav(selected/'compensated-pcm.wav',compensate(source,t[sample_positions(meta)],period=3546900/8000))
    for path in selected.iterdir():
        if path.is_file():shutil.copy2(path,out/path.name)
    shutil.copytree(selected/'assembly',out/'assembly')
    save(out/'independent-ima.json',independent_ima_check(packed,ffmpeg))
    result=dict(complete=True,quality=quality,selected=str(selected.relative_to(out)),
                trd_sha256=sha(out/'audiobook-preview.trd'),native_hot_path_tstates=423,hot_path_delta_tstates=0)
    save(out/'report.json',result);return result


def stable_score(folder, dest, ffmpeg):
    """Same fixed 8-kHz source, full real clock, f64 filter; no fitted alignment."""
    dest.mkdir(parents=True,exist_ok=True)
    meta=read(folder/'player.json');n=meta['outputs_per_cycle'];source=wav8(folder/'source-preview.wav')
    packed=gzip.decompress((folder/'soundtrack.ima.gz').read_bytes())
    bits=reference(packed,cycles=2,model=meta['model'],idle_pairs=meta['loop_idle_pairs'])[3]
    times=np.frombuffer(gzip.decompress((folder/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
    rows=[]
    for cycle in range(2):
        t=times[cycle*n:(cycle+1)*n+1].copy();t-=t[0]
        period=3546900/8000;count=int(np.ceil(t[-1]/period));edges=np.r_[np.arange(count)*period,t[-1]]
        values=np.pad(source/256,(0,max(0,count-len(source))),constant_values=.5)[:count]
        original=filter_signal(values,edges,ffmpeg,768000)
        actual=filter_signal(bits[cycle*n:(cycle+1)*n],t,ffmpeg,768000)
        cut=slice(4410,-4410);snr=ratio(original[cut],actual[cut]-original[cut])
        rows.append(snr)
        if cycle==0:
            write_wav(dest/'reference.wav',original*.5);write_wav(dest/'output.wav',actual*.5)
    result=dict(complete=True,two_loop_snr_db=rows,minimum_snr_db=min(rows),integration_rate_hz=768000,
        reference_rate_hz=8000,fitted_delay_gain_or_time_stretch=False,listening_gain=.5,
        scope='Exact real Fuse holds; fixed source clock; float64 unchanged 70/4500/4500 Hz filter, 100-ms edge exclusions')
    save(dest/'report.json',result);return result


def finish(out,fuse,ffmpeg):
    folders=dict(previous=CLOCK,overlap=out/'disk-overlap',no_overlap=out/'disk-no-overlap')
    metrics={name:stable_score(path,out/'stable'/name,ffmpeg) for name,path in folders.items()}
    boundaries={}
    for name,path in folders.items():
        meta=read(path/'player.json')
        times=np.frombuffer(gzip.decompress((path/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:meta['outputs_per_cycle']+1]
        boundaries[name]=[boundary_metrics(read_wav(out/'stable'/name/'reference.wav'),
            read_wav(out/'stable'/name/'output.wav'),times,period) for period in (64,128)]
    save(out/'boundary-diagnostics.json',dict(scope='First-loop boundary energy; diagnostic only, not a universal flutter gate',cases=boundaries))
    eligible=[name for name,path in folders.items() if read(path/'quality.json')['speed_within_two_percent']]
    winner=max(eligible,key=lambda name:metrics[name]['minimum_snr_db'])
    selected=folders[winner];dest=out/'selected';dest.mkdir(exist_ok=True)
    for path in selected.iterdir():
        if path.is_file():shutil.copy2(path,dest/path.name)
    shutil.copytree(selected/'assembly',dest/'assembly',dirs_exist_ok=True)
    if not (out/'recording/report.json').exists():
        subprocess.run([sys.executable,str(MODULES/'record_pcm.py'),str(dest),'--fuse',str(fuse),
                        '--output',str(out/'recording')],check=True)
    recording=read(out/'recording/report.json')
    assert recording['source_trd_sha256']==sha(dest/'audiobook-preview.trd')
    assert recording['recording_complete'] and recording['paging_latches_match'] and recording['secondary_paging_unchanged']
    result=dict(complete=True,samples=186880,source_sha256=hashlib.sha256(wav8(CLOCK/'source-preview.wav').tobytes()).hexdigest(),
        selected=winner,stable_quality=metrics,
        previous_legacy_snr_db=read(CLOCK/'quality.json')['minimum_snr_db'],
        candidate_legacy_snr_db={name:read(path/'quality.json')['minimum_snr_db'] for name,path in folders.items()},
        matched_host_settings=dict(width=512,horizon=128,regularization=.03,commits=[64,128]),
        unchanged_player_ordinary_tstates=423,hot_path_delta_tstates=0,
        speed_error_percent=read(dest/'quality.json')['mean_speed_error_percent'],
        trd_sha256=sha(dest/'audiobook-preview.trd'),recording=recording,physical_hardware_tested=False)
    save(out/'report.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='recording'}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True);p.add_argument('--fuse',type=Path,required=True)
    p.add_argument('--stage',choices=('all','overlap','control','finish'),default='all')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    identity=dict(source=sha(CLOCK/'source-preview.wav'),clock=sha(CLOCK/'output-times.u32.gz'),
        fuse=sha(a.fuse),ffmpeg=sha(Path(a.ffmpeg)),width=512,horizon=128,regularization=.03,commits=[64,128],
        producers={name:sha(MODULES/name) for name in ('ima_waveform_encoder.py','waveform_kernel.py',
            'direct_player.py','direct-player.asm','quality_search.py','verify_direct.py','verify_packet.py',
            'probe_packet_area.py','probe_feedback_packets.py','analyze_voice_jitter.py')})
    marker=out/'identity.json'
    if marker.exists():
        if read(marker)!=identity:raise ValueError('experiment source, clock, tools or producers changed')
    else:save(marker,identity)
    if a.stage in ('all','overlap'):
        packed=authenticate_cached(out)
        calibration=CACHED/'disk-encode-1/calibration';index=read(calibration/'calibration.json')['selected']
        stage(out/'disk-overlap',lambda path:qualify(path,packed,a.fuse,a.ffmpeg,calibration/f'phase-{index:02d}'))
    if a.stage in ('all','control'):
        host=out/'encode-no-overlap'
        if not (host/'report.json').exists():
            subprocess.run([sys.executable,str(MODULES/'ima_waveform_encoder.py'),'--input',str(CLOCK),
                '--output',str(host),'--width','512','--regularization','.03','--block-size','128',
                '--commit-size','128','--ffmpeg',a.ffmpeg],check=True)
        report=read(host/'report.json');packed=gzip.decompress((host/'soundtrack.ima.gz').read_bytes())
        assert Path(report['input']).resolve()==CLOCK.resolve()
        assert report['source_sha256']==hashlib.sha256(wav8(CLOCK/'source-preview.wav').tobytes()).hexdigest()
        assert (report['beam_width'],report['block_size'],report['commit_size'],report['control_regularization'])==(512,128,128,.03)
        assert report['packed_sha256']==hashlib.sha256(packed).hexdigest() and not report['ima3_subset']
        stage(out/'disk-no-overlap',lambda path:qualify(path,packed,a.fuse,a.ffmpeg))
    if a.stage in ('all','finish'):finish(out,a.fuse,a.ffmpeg)


if __name__=='__main__':main()
