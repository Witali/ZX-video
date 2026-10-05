"""Independent codec/recurrence checks and numerical convergence, PC only."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from assess import feedback,CPU
from assess_snr import FILTER,ratio
from build_pdm import reconstruct,write_wav
from convert_audio import independent_ima_check
from ima_codec import decode
from ima3_direct_player import pack3
from probe_reconstruction_error import wav8,filtered
from verify_pcm import save

HERE=Path(__file__).resolve().parent


def filter_rate(signal,rate,ffmpeg):
    r=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(rate),'-ac','1','-i','-',
                      '-af',FILTER,'-ar','44100','-f','f32le','-'],input=signal.astype('<f4').tobytes(),capture_output=True,check=True)
    return np.frombuffer(r.stdout,'<f4').astype(float)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assessment',type=Path,required=True)
    p.add_argument('--simulation',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True)
    a=p.parse_args();out=a.simulation
    report=json.loads((out/'report.json').read_bytes())
    source=wav8(HERE.parent/'ima-3bit-overlap/qualified/source-preview.wav')
    codec_proofs=[];controls=[]
    for codec in ('ima3','ima4'):
        for suffix,root in [('pcm-search',a.assessment),('filtered128',out)]:
            path=root/(codec+'-'+suffix+'.ima.gz');packed=gzip.decompress(path.read_bytes())
            proof=independent_ima_check(packed,a.ffmpeg)
            if codec=='ima3':assert len(pack3(packed))==len(source)*3//8
            codec_proofs.append(dict(file=str(path),sha256=hashlib.sha256(packed).hexdigest(),**proof))
        best=report['best_by_codec'][codec]
        path=(out/(codec+'-filtered128.ima.gz') if 'filtered128' in best['name'] else a.assessment/(codec+'-pcm-search.ima.gz'))
        pcm,_=decode(gzip.decompress(path.read_bytes()));levels=(pcm.astype(float)+32768)/65536
        beta,gain=best['beta'],best['declared_gain']
        bits,_=feedback(np.repeat(levels,16),beta,gain)
        # Compare every decision with an independent two-history integer
        # recurrence. Dyadic gains/betas and PCM16 fit exact rational units.
        # beta=.5/.75 needs growing denominators. For the selected SD2
        # variant, independently verify its ACTUAL gain and every decision.
        # A half-gain SD2 control is used only if a damped variant wins.
        check_gain=gain if beta==1 else .5
        sd_bits=bits if beta==1 else feedback(np.repeat(levels,16),1.,check_gain)[0]
        scale=1<<18;previous=older=0
        for i,value in enumerate(pcm):
            x=scale//2+int(int(value)*4*check_gain)
            for j in range(16):
                u=x+2*previous-older;bit=int(u>=scale//2)
                older,previous=previous,u-scale*bit
                assert bit==int(sd_bits[i*16+j])
        # Full selected output is reproduced without adjusted gain or phase.
        t=np.arange(len(bits)+1)*CPU/128000
        actual=filtered(reconstruct(bits,t),a.ffmpeg)
        reference=filtered(reconstruct(source/256,np.arange(len(source)+1)*CPU/8000)*gain,a.ffmpeg)
        measured=ratio(reference[4410:-4410],actual[4410:-4410]-reference[4410:-4410])
        assert abs(measured-best['snr_db'])<1e-8
        decoded=filtered(reconstruct(levels,np.arange(len(source)+1)*CPU/8000)*gain,a.ffmpeg)
        modulator_only=ratio(decoded[4410:-4410],actual[4410:-4410]-decoded[4410:-4410])
        # Fixed common listening attenuation prevents transient clipping in
        # PCM16 WAVs. It does not enter the float-domain SNR measurement.
        wav_gain=.5
        assert max(np.max(abs(actual)),np.max(abs(reference)))*wav_gain<1
        write_wav(out/(codec+'-best-preview.wav'),actual*wav_gain)
        write_wav(out/(codec+'-reference-same-gain.wav'),reference*wav_gain)
        # Repeat exactly the first five seconds with a four-times finer
        # area integration grid and corresponding FFmpeg input rate.
        count=40000;short=bits[:count*16];tt=t[:len(short)+1];rows=[]
        for rate in (192000,768000):
            sig=filter_rate(reconstruct(short,tt,rate),rate,a.ffmpeg)
            ref=filter_rate(reconstruct(source[:count]/256,np.arange(count+1)*CPU/8000,rate)*gain,rate,a.ffmpeg)
            rows.append(dict(integration_rate_hz=rate,snr_db=ratio(ref[4410:-4410],sig[4410:-4410]-ref[4410:-4410])))
        delta=rows[1]['snr_db']-rows[0]['snr_db']
        assert abs(delta)<.2,(codec,rows)
        controls.append(dict(codec=codec,selected=best['name'],full_snr_db=measured,
                             modulator_only_snr_db=modulator_only,
                             independent_sd2_gain=check_gain,
                             selected_output_bits_checked=bool(beta==1),
                             listening_wav_gain=wav_gain,unscaled_output_peak=float(np.max(abs(actual))),
                             every_sd2_decision_matches_integer_reference=True,
                             decisions_checked=len(sd_bits),numerical_check_first_five_seconds=rows,
                             finer_integration_snr_delta_db=delta))
    # Additional diagnostic, explicitly not a proposed no-IMA format. It
    # isolates how much of the best full-scale result is lost in coding.
    bits,peak=feedback(np.repeat(source/256,16),1.,1.)
    actual=filtered(reconstruct(bits,np.arange(len(bits)+1)*CPU/128000),a.ffmpeg)
    ref=filtered(reconstruct(source/256,np.arange(len(source)+1)*CPU/8000),a.ffmpeg)
    ideal_pcm_control=dict(snr_db=ratio(ref[4410:-4410],actual[4410:-4410]-ref[4410:-4410]),
                          declared_gain=1.,beta=1.,peak_state=peak,
                          scope='Diagnostic only, no IMA; user constraint still requires IMA storage')
    save(out/'verification.json',dict(scope=__doc__,complete=True,codec_checks=codec_proofs,controls=controls,
                                    ideal_pcm_control=ideal_pcm_control,
                                    z80_ported=False,physical_hardware_tested=False))


if __name__=='__main__':main()
