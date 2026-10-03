"""Codec-only 10:1 study, relative to mono 8000-Hz PCM16 storage.

Reuse the complete prepared PCM8 control signal to keep comparisons stable.
Counting its PCM16 representation does not add source precision. Include
per-recording dictionaries and a 32-byte container allowance. No PDM or
Spectrum startup claim follows from these host rate/distortion measurements.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import time
import wave

import numpy as np
from probe_dense_codecs import vq, pack_codes, filtered
from assess_snr import ratio, FILTER
from convert_audio import pcm_wav
from ima_codec import decode
from lpc_preload import encode_ima
from verify_pcm import save


def shape_gain(source, dimension=10, count=256):
    """Per-recording shapes with fixed integer gains; no speech model."""
    padded=np.pad(source,(0,(-len(source))%dimension),constant_values=128)
    x=padded.reshape(-1,dimension).astype(float)-128
    peak=np.maximum(np.max(abs(x),axis=1),1)
    normalized=np.clip(np.rint(x*120/peak[:,None])+128,0,255).astype('u1')
    _,raw,_,iterations=vq(normalized.ravel(),dimension,count,32)
    shapes=raw.astype(np.int32)-128
    gains=np.r_[0,np.rint(np.geomspace(2,136,15))].astype(int)
    # Tables are fixed by the codec and included in the storage comparison,
    # even though a decoder could generate them at startup instead.
    values=np.arange(256)-128
    tables=np.clip(((gains[:,None]*values[None,:]+64)//128)+128,0,255).astype('u1')
    expanded=tables[:,raw].reshape(-1,dimension).astype(np.float32)
    norm=np.sum(expanded*expanded,axis=1)
    ids=np.empty(len(x),dtype=int)
    for start in range(0,len(x),512):
        block=(x[start:start+512]+128).astype(np.float32)
        ids[start:start+len(block)]=np.argmin(norm[None,:]-2*block@expanded.T,axis=1)
    decoded=expanded[ids].astype('u1').ravel()[:len(source)]
    return ids,raw,tables,decoded,iterations


def predictive7(source):
    """Seven residual samples, with actual reconstructed feedback."""
    x=np.pad(source,(0,(-len(source))%7),constant_values=128).reshape(-1,7).astype(int)-128
    base=np.r_[0,x[:-1,-1]]//2
    training=np.clip(x-base[:,None],-128,127)
    _,raw,_,iterations=vq((training+128).astype('u1').ravel(),7,512,32)
    book=raw.astype(int)-128; lo=book.min(axis=1);hi=book.max(axis=1)
    last=0;ids=[];restored=[]
    for row in x:
        base=last//2;valid=(lo+base>=-128)&(hi+base<=127)
        assert valid.any()
        errors=np.sum((book+base-row)**2,axis=1)
        index=int(np.argmin(np.where(valid,errors,2**30)))
        values=book[index]+base;last=int(values[-1])
        ids.append(index);restored.extend(values+128)
    return np.asarray(ids),book.astype('i1'),np.asarray(restored[:len(source)],'u1'),iterations


def run(source_path, out, ffmpeg):
    out.mkdir(parents=True, exist_ok=True)
    with wave.open(str(source_path), 'rb') as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 1, 8000)
        source = np.frombuffer(w.readframes(w.getnframes()), 'u1').copy()
    pcm_wav(out/'original-preview.wav', source)
    signal = (source.astype(float)-128)/128
    ref = filtered(signal, ffmpeg)
    rows = []

    def result(name, decoded, payload, book=b'', **extra):
        actual = filtered((decoded.astype(float)-128)/128, ffmpeg)
        edge = 4410
        # Decoder filter latency is disclosed and aligned only by a constant
        # integer delay, never by changing pitch, duration or gain.
        scores = [(ratio(ref[edge:-edge], actual[edge+d:len(actual)-edge+d]-ref[edge:-edge]), d)
                  for d in range(-44, 45)]
        best, delay = max(scores)
        container = b'TTO1' + struct.pack('<III', len(source), len(payload), len(book)) + bytes(16)
        total = len(container)+len(payload)+len(book)
        (out/(name+'.data.gz')).write_bytes(gzip.compress(payload, mtime=0))
        if book: (out/(name+'.book.gz')).write_bytes(gzip.compress(book, mtime=0))
        pcm_wav(out/(name+'-preview.wav'), decoded)
        row = dict(name=name, payload_bytes=len(payload), dictionary_bytes=len(book),
                   container_bytes=len(container), total_bytes=total,
                   pcm16_to_codec_ratio=2*len(source)/total,
                   total_bitrate_bps=total*8/(len(source)/8000),
                   meets_10_to_1=total<=2*len(source)/10,
                   codec_only_snr_db=ratio(ref[edge:-edge], actual[edge:-edge]-ref[edge:-edge]),
                   constant_delay_aligned_snr_db=best, alignment_44100hz_samples=delay,
                   native_z80_tested=False, integrated_pdm_tested=False, **extra)
        # The requested player consumes IMA. Include its extra distortion,
        # independently of the codec-only preview. Keep the silent guard.
        guarded = decoded.copy(); guarded[-128:] = 128
        try:
            ima = encode_ima(guarded)
            recovered, _ = decode(ima)
            after = np.clip((recovered.astype(np.int32)+32768)>>8, 0, 255).astype('u1')
            converted = filtered((after.astype(float)-128)/128, ffmpeg)
            row['after_ima_codec_snr_db'] = ratio(ref[edge:-edge], converted[edge:-edge]-ref[edge:-edge])
            (out/(name+'.ima.gz')).write_bytes(gzip.compress(ima, mtime=0))
            pcm_wav(out/(name+'-ima-preview.wav'), after)
        except (ValueError, AssertionError) as error:
            row['ima_guard_rejected'] = str(error)
        rows.append(row)
        save(out/'report.json', dict(scope=__doc__, complete=False, rows=rows))
        print(json.dumps(row), flush=True)

    # Established simple waveform codecs, decoded independently by FFmpeg.
    for rate in (8000, 12000):
        name=f'dfpwm-{rate}'
        encoded=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','u8','-ar','8000','-ac','1','-i','-',
            '-ar',str(rate),'-c:a','dfpwm','-f','dfpwm','-'], input=source.tobytes(), capture_output=True,check=True).stdout
        restored=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','dfpwm','-ar',str(rate),'-ac','1','-i','-',
            '-ar','8000','-f','u8','-'],input=encoded,capture_output=True,check=True).stdout
        decoded=np.frombuffer(restored,'u1')[:len(source)]
        assert len(decoded)==len(source)
        result(name,decoded,encoded,encoded_sample_rate=rate,encoder='FFmpeg DFPWM1a')
    # FFmpeg G.726 rejects a 6000-Hz / 12000-bit/s mode. Do not relabel
    # a nonstandard clock as a supported G.726 rate to meet the target.
    for rate in (8000,):
        encoded=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','u8','-ar','8000','-ac','1','-i','-',
            '-ar',str(rate),'-c:a','g726','-b:a',str(rate*2),'-f','g726','-'],input=source.tobytes(),capture_output=True,check=True).stdout
        restored=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','g726','-code_size','2','-ar',str(rate),'-ac','1','-i','-',
            '-ar','8000','-f','u8','-'],input=encoded,capture_output=True,check=True).stdout
        result('g726-'+str(rate*2),np.frombuffer(restored,'u1')[:len(source)],encoded,
               encoder='FFmpeg G.726 two-bit ADPCM',encoded_sample_rate=rate,
               standard_8000hz_clock=rate==8000)

    # Bounded sweep. Each recording carries its own byte-quantized book.
    for dimension, count in ((6,256),(7,512),(8,512),(8,1024),(10,512)):
        start=time.monotonic()
        ids,book,decoded,iterations=vq(source,dimension,count,iterations=32)
        bits=int(math.log2(count)); payload=pack_codes(ids,bits)
        result(f'vq{dimension}x{count}',decoded,payload,book.tobytes(),
               dimensions=dimension,entries=count,index_bits=bits,iterations=iterations,
               encoder_seconds=time.monotonic()-start,book_training='same recording, dictionary transmitted')
    ids,book,tables,decoded,iterations=shape_gain(source)
    result('sgvq10x256',decoded,pack_codes(ids,12),book.tobytes()+tables.tobytes(),
           dimensions=10,entries=256,index_bits=12,iterations=iterations,
           shape_book_bytes=book.nbytes,gain_table_bytes=tables.nbytes,
           book_training='same recording shapes; 16 fixed integer gains')
    ids,book,decoded,iterations=predictive7(source)
    result('pvq7x512',decoded,pack_codes(ids,9),book.tobytes(),
           dimensions=7,entries=512,index_bits=9,iterations=iterations,
           predictor='floor(last signed PCM8 /2)',book_training='same recording residuals')
    save(out/'report.json',dict(scope=__doc__,complete=True,date='2026-10-03',
        source_sha256=hashlib.sha256(source.tobytes()).hexdigest(),samples=len(source),
        seconds=len(source)/8000,reference_storage_bytes=2*len(source),
        reference_storage='mono 8000-Hz PCM16; signal retains the prepared PCM8 precision',
        compression_target=10,filter=FILTER,rows=rows,
        ffmpeg_version=subprocess.run([ffmpeg,'-version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True)
    args=p.parse_args();run(args.source,args.output,args.ffmpeg)
