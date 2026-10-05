"""Compare PCM8, G.711 mu-law and A-law with high-precision SD2 on the PC.

No new Z80 or TRD. Same reference, time span, filtering and pulse rate for
each comparison. Preserve full decoded PCM16; report truncation separately.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import wave

import numpy as np
from assess_snr import FILTER,ratio
from build_pdm import reconstruct,write_wav
from g711_codec import encode,decode,decode_table,verify_tables
from probe_reconstruction_error import filtered
from verify_pcm import save
from stream_model import modulate

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'snr30-ima'))
from assess import feedback,CPU


def load(path):
    with wave.open(str(path),'rb') as w:
        if (w.getnchannels(),w.getframerate())!=(1,8000) or w.getsampwidth() not in (1,2):
            raise ValueError('input must be mono PCM8 or PCM16 WAV at 8000 Hz')
        width=w.getsampwidth();data=w.readframes(w.getnframes())
    return ((np.frombuffer(data,'u1').astype(np.int32)-128)*256 if width==1 else
            np.frombuffer(data,'<i2').astype(np.int32)),width*8


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=HERE.parent/'ima-3bit-overlap/qualified/source-preview.wav')
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--ffmpeg',required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise ValueError('output must be empty')
    source,width=load(a.input);n=len(source);bounds=np.arange(n+1)*CPU/8000
    reference=filtered(reconstruct((source.astype(float)+32768)/65536,bounds),a.ffmpeg)
    cut=slice(4410,-4410);rows=[]
    proof=verify_tables(a.ffmpeg)
    identity=dict(input_file_sha256=hashlib.sha256(a.input.read_bytes()).hexdigest(),
                  source_pcm16_sha256=hashlib.sha256(source.astype('<i2').tobytes()).hexdigest(),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  codec_sha256=hashlib.sha256((HERE.parents[1]/'g711_codec.py').read_bytes()).hexdigest(),
                  feedback_sha256=hashlib.sha256((HERE.parent/'snr30-ima/assess.py').read_bytes()).hexdigest(),
                  streaming_sha256=hashlib.sha256((HERE/'stream_model.py').read_bytes()).hexdigest(),
                  ffmpeg_sha256=hashlib.sha256(Path(a.ffmpeg).read_bytes()).hexdigest())
    report=dict(date='2026-10-05',scope=__doc__,source_samples=n,source_seconds=n/8000,input_bits=width,
                identity=identity,reference='The identical prepared input PCM; no fitted gain/delay or narrower filter',
                filter=FILTER,edge_exclusions_seconds=.1,listening_wav_gain=.5,
                table_checks=proof,rows=rows,z80_ported=False,physical_hardware_tested=False)
    # Quantize only when a PCM16 input is supplied. The default PCM8
    # reference is retained exactly, so its codec-only error is zero.
    pcm8=np.clip(np.rint(source/256),-128,127).astype(np.int32)*256
    streams={'pcm8':pcm8};payloads={'pcm8':((pcm8//256)+128).astype('u1').tobytes()}
    (out/'soundtrack.pcm8').write_bytes(payloads['pcm8'])
    for law in ('mulaw','alaw'):
        payload=encode(source,law,a.ffmpeg);decoded=decode(payload,law).astype(np.int32)
        (out/(law+'-payload.u8.gz')).write_bytes(gzip.compress(payload,mtime=0))
        (out/('soundtrack.'+law)).write_bytes(payload)
        (out/(law+'-decode-table.s16le.gz')).write_bytes(gzip.compress(decode_table(law).tobytes(),mtime=0))
        # Independent whole-stream check in addition to all256 table codes.
        check=subprocess.run([a.ffmpeg,'-v','error','-nostdin','-f',law,'-ar','8000','-ac','1','-i','-',
                              '-f','s16le','-'],input=payload,capture_output=True,check=True)
        assert np.array_equal(decoded,np.frombuffer(check.stdout,'<i2'))
        streams[law]=decoded;payloads[law]=payload
    write_wav(out/'reference-preview.wav',reference*.5)
    for name,pcm in streams.items():
        levels=(pcm.astype(float)+32768)/65536
        ideal=filtered(reconstruct(levels,bounds),a.ffmpeg)
        codec_snr=ratio(reference[cut],ideal[cut]-reference[cut])
        for rate in (128000,64000):
            slots=rate//8000
            bits,streaming=modulate(payloads[name],name,slots)
            # Independent earlier floating model is used only as a check;
            # the actual simulated producer consumes compact bytes directly.
            expected,peak=feedback(np.repeat(levels,slots),1.,1.)
            assert np.array_equal(bits,expected)
            # Independent exact two-history recurrence, every selected128k bit.
            if rate==128000:
                recent=older=0
                for i,value in enumerate(pcm):
                    x=int(value)+32768
                    for j in range(slots):
                        u=x+2*recent-older;bit=int(u>=32768)
                        older,recent=recent,u-bit*65536
                        assert bit==bits[i*slots+j]
            times=np.arange(len(bits)+1)*CPU/rate
            actual=filtered(reconstruct(bits,times),a.ffmpeg)
            total=ratio(reference[cut],actual[cut]-reference[cut])
            assert np.max(abs(actual))*.5<1
            row=dict(format=name,pdm_rate_hz=rate,source_bits=8,bytes_per_sample=1,
                     source_bitrate_bps=64000,payload_bytes=n,codec_only_snr_db=codec_snr,
                     total_snr_db=total,modulator_only_snr_db=ratio(ideal[cut],actual[cut]-ideal[cut]),
                     state_peak=peak,declared_modulator_gain=1.,
                     streaming=streaming,every_bit_matches_expanded_control=True,
                     all_modulator_bits_integer_checked=rate==128000,output_peak=float(np.max(abs(actual))))
            rows.append(row);save(out/'report.json',report);print(json.dumps(row),flush=True)
            write_wav(out/(name+f'-sd2-{rate//1000}k-preview.wav'),actual*.5)
            if rate==128000:
                (out/(name+'-pdm128.bits.gz')).write_bytes(gzip.compress(np.packbits(bits).tobytes(),mtime=0))
        if name!='pcm8':
            # This is a separate loss-of-precision diagnostic, not the
            # main G.711 decoder: truncate decoded PCM16 to its high byte.
            reduced=(pcm//256)*256
            bits,_=feedback(np.repeat((reduced.astype(float)+32768)/65536,16),1.,1.)
            actual=filtered(reconstruct(bits,np.arange(len(bits)+1)*CPU/128000),a.ffmpeg)
            rows.append(dict(format=name,pdm_rate_hz=128000,diagnostic='decoded PCM16 truncated to PCM8 before PDM',
                             total_snr_db=ratio(reference[cut],actual[cut]-reference[cut])))
            save(out/'report.json',report)
    candidates=[r for r in rows if r['format'] in ('mulaw','alaw') and r['pdm_rate_hz']==128000 and 'diagnostic' not in r]
    report['selected']=max(candidates,key=lambda r:r['total_snr_db'])
    report['target_met_in_ideal_pc_model']=report['selected']['total_snr_db']>=30
    report['complete']=True
    save(out/'report.json',report)


if __name__=='__main__':main()
