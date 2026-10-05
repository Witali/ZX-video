"""Whole-selected-clip numerical check and compact payload/WAV audit."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import wave

import numpy as np
from build_pdm import reconstruct,write_wav
from assess_snr import ratio,FILTER
from verify_pcm import save
from simulate import load,CPU

HERE=Path(__file__).resolve().parent
STABLE_FILTER=','.join(part+':precision=f64' for part in FILTER.split(','))


def filter_rate(signal,rate,ffmpeg):
    # At MHz integration rates, automatic float32 IIR filtering becomes
    # numerically unstable around the70-Hz high-pass pole. Keep EXACTLY
    # the same filter frequencies/order, but perform arithmetic in float64.
    result=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','f64le','-ar',str(rate),'-ac','1','-i','-',
                           '-af',STABLE_FILTER,'-ar','44100','-f','f64le','-'],
                          input=np.asarray(signal,dtype='<f8').tobytes(),capture_output=True,check=True)
    return np.frombuffer(result.stdout,'<f8')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--ffmpeg',required=True)
    p.add_argument('--input',type=Path,default=HERE.parent/'ima-3bit-overlap/qualified/source-preview.wav')
    a=p.parse_args();out=a.output
    report=json.loads((out/'report.json').read_bytes());assert report['complete']
    selected=report['selected'];name=selected['format'];n=report['source_samples']
    checks=[]
    for row in report['rows']:
        if 'streaming' in row:
            assert row['streaming']['expanded_pcm_audio_buffer_bytes']==0
            assert row['every_bit_matches_expanded_control']
    for law in ('mulaw','alaw'):
        payload=(out/('soundtrack.'+law)).read_bytes()
        assert len(payload)==n
        assert payload==gzip.decompress((out/(law+'-payload.u8.gz')).read_bytes())
        table=gzip.decompress((out/(law+'-decode-table.s16le.gz')).read_bytes());assert len(table)==512
        checks.append(dict(law=law,payload_bytes=len(payload),bytes_per_sample=1,pcm_audio_buffer_bytes=0,
                           table_bytes=len(table),payload_sha256=hashlib.sha256(payload).hexdigest()))
    source,_=load(a.input);bits=np.unpackbits(np.frombuffer(gzip.decompress((out/(name+'-pdm128.bits.gz')).read_bytes()),'u1'))
    assert len(bits)==n*16
    times=np.arange(len(bits)+1)*CPU/128000
    rate=768000
    actual=filter_rate(reconstruct(bits,times,rate),rate,a.ffmpeg)
    ref=filter_rate(reconstruct((source.astype(float)+32768)/65536,np.arange(n+1)*CPU/8000,rate),rate,a.ffmpeg)
    write_wav(out/'reference-verified-preview.wav',ref*.5)
    snr=ratio(ref[4410:-4410],actual[4410:-4410]-ref[4410:-4410])
    # The old automatic-float32 score is retained as a diagnostic, not a
    # convergence reference after its high-rate instability was observed.
    delta=snr-selected['total_snr_db'];assert np.isfinite(snr)
    save(out/'f64-progress.json',dict(selected_768k_snr_db=snr,delta_from_legacy_f32_192k_db=delta))
    coarse=192000
    coarse_signal=filter_rate(reconstruct(bits,times,coarse),coarse,a.ffmpeg)
    coarse_ref=filter_rate(reconstruct((source.astype(float)+32768)/65536,np.arange(n+1)*CPU/8000,coarse),coarse,a.ffmpeg)
    coarse_snr=ratio(coarse_ref[4410:-4410],coarse_signal[4410:-4410]-coarse_ref[4410:-4410])
    comparisons=[]
    for encoding in ('pcm8','mulaw','alaw'):
        observed=np.unpackbits(np.frombuffer(gzip.decompress((out/(encoding+'-pdm128.bits.gz')).read_bytes()),'u1'))
        signal=filter_rate(reconstruct(observed,times,rate),rate,a.ffmpeg)
        assert np.max(abs(signal))*.5<1
        write_wav(out/(encoding+'-verified-preview.wav'),signal*.5)
        comparisons.append(dict(format=encoding,integration_rate_hz=rate,
                                snr_db=ratio(ref[4410:-4410],signal[4410:-4410]-ref[4410:-4410])))
    best=max(comparisons,key=lambda row:row['snr_db'] if row['format']!='pcm8' else -np.inf)
    assert best['format']==name,'rerun the finer check for the new high-precision winner'
    finer=1536000
    signal=filter_rate(reconstruct(bits,times,finer),finer,a.ffmpeg)
    finer_ref=filter_rate(reconstruct((source.astype(float)+32768)/65536,np.arange(n+1)*CPU/8000,finer),finer,a.ffmpeg)
    finer_snr=ratio(finer_ref[4410:-4410],signal[4410:-4410]-finer_ref[4410:-4410])
    save(out/'numerical-progress.json',dict(all_formats_768k=comparisons,selected_768k_snr_db=snr,
         selected_1536k_snr_db=finer_snr,delta_db=finer_snr-snr))
    assert abs(finer_snr-snr)<.05
    wavs=[]
    for f in sorted(out.glob('*preview.wav')):
        with wave.open(str(f),'rb') as w:
            assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,44100)
            samples=np.frombuffer(w.readframes(w.getnframes()),'<i2')
        assert not np.any((samples==32767)|(samples==-32767)|(samples==-32768))
        wavs.append(dict(file=f.name,samples=len(samples),full_scale_samples=0))
    save(out/'verification.json',dict(scope=__doc__,complete=True,payloads=checks,wavs=wavs,
         verification_filter=STABLE_FILTER,
         numerical_check=dict(format=name,entire_clip_samples=n,old_integration_rate_hz=192000,
                              integration_rate_hz=rate,old_snr_db=selected['total_snr_db'],
                              snr_db=snr,delta_db=delta,target_30_db_passed=snr>=30),
         all_formats_768k=comparisons,
         selected_high_precision=best,
         coarse_f64=dict(integration_rate_hz=coarse,snr_db=coarse_snr),
         finer_selected=dict(integration_rate_hz=finer,snr_db=finer_snr,
                             delta_from_768k_db=finer_snr-snr,target_30_db_passed=finer_snr>=30),
         same_source_duration=True,z80_ported=False,hardware_measured=False))
    print(json.dumps(dict(numerical_snr_db=snr,finer_snr_db=finer_snr,all_formats=comparisons,payloads=checks)))


if __name__=='__main__':main()
