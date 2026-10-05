"""Bounded independent model checks and complete quality measurement for approximate feedback."""
import json
import math
from pathlib import Path
import random
import struct
import wave
from check_primitives import machine,symbols,call,audit
from verify import native,ROOT,sha


def snr(reference, actual):
    power=sum(x*x for x in reference);error=sum((x-y)**2 for x,y in zip(reference,actual))
    return 10*math.log10(power/error) if error else None


def filter_checks(folder):
    s=symbols(folder);m=machine(folder);rng=random.Random(712);count=0
    def wrap(x):return ((x+2**31)&0xffffffff)-2**31
    for batch in range(24):
        coefficients=[rng.randrange(-8192,8193) for _ in range(10)]
        source=[rng.randrange(-32767,32768) for _ in range(40)]
        memory=[rng.randrange(-1000000,1000000) for _ in range(10)]
        m.memory[s['_zx_lpc']:s['_zx_lpc']+20]=struct.pack('<10h',*coefficients)
        m.memory[s['_zx_memory']:s['_zx_memory']+40]=struct.pack('<10i',*memory)
        m.memory[0xc000:0xc050]=struct.pack('<40h',*source)
        expected=[]
        for x in source:
            y=max(-32767,min(32767,x+(wrap(memory[0]+4096)>>13)))
            n=(-y//256)*256
            memory=[wrap(memory[j+1]+coefficients[j]*n) for j in range(9)]+[wrap(coefficients[9]*n)]
            expected.append(y)
        actual=[]
        m.set_output_callback(lambda p,v:actual.append(int.from_bytes(m.memory[s['_last_pcm16']:s['_last_pcm16']+2],'little',signed=True)))
        call(m,s['_zx_speex_filter'],hl=0xc000,budget=1000000)
        assert actual==expected,(batch,actual,expected)
        assert bytes(m.memory[s['_zx_memory']:s['_zx_memory']+40])==struct.pack('<10i',*memory)
        count+=40
    return dict(samples=count,independent_approximate_filter_model=True)


def main():
    out=ROOT/'build/speex-port';variant='pure-r10-approx';folder=out/variant
    checks=dict(filter=filter_checks(folder))
    report=native(out,variant,require_exact=False)
    checks['audit']=audit(folder,(out/'input.spxraw').read_bytes(),(folder/'actual.pcm16').read_bytes())
    reference=struct.unpack('<186880h',(out/'reference.pcm16').read_bytes())
    exact=[(x>>8) for x in reference]
    actual=[x-128 for x in (folder/'actual.pcm8').read_bytes()]
    source_path=Path('C:/Work/ZX-video/audiobook-beeper/experiments/ima-waveform/source-preview.wav')
    with wave.open(str(source_path),'rb') as w:
        assert w.getparams()[:3]==(1,1,8000)
        source_bytes=w.readframes(w.getnframes())
    assert sha(source_bytes)==json.loads((out/'host-report.json').read_text())['source_sha256']
    source=[x-128 for x in source_bytes]
    # Encoder lookahead also contributes to end-to-end delay. Measure against
    # exact decoding once, then use that same lag for both candidates.
    window=min(32000,len(source)-320)
    lag=min(range(321),key=lambda k:sum((source[i]-exact[i+k])**2 for i in range(window)))
    quality=dict(source_pcm8_sha256=sha(source_bytes),alignment_delay_samples=lag,
                 alignment_method='Minimum raw squared error on first 32000 samples, lag 0..320, exact decoder only',
                 approximate_vs_exact_snr_db=snr(exact,actual),
                 exact_vs_source_snr_db=snr(source[:len(source)-lag],exact[lag:]),
                 approximate_vs_source_snr_db=snr(source[:len(source)-lag],actual[lag:]),
                 changed_pcm8_samples=sum(x!=y for x,y in zip(exact,actual)),
                 rail_samples=sum(x in (-128,127) for x in actual),
                 mean_signed_pcm8=sum(actual)/len(actual),metrics='Raw PCM8 SNR; no gain fitting, filtering or perceptual-quality claim')
    for name,data in [('source',source_bytes),('exact',bytes(x+128 for x in exact)),('approximate',bytes(x+128 for x in actual))]:
        with wave.open(str(folder/(name+'.wav')),'wb') as w:
            w.setparams((1,1,8000,0,'NONE','not compressed'));w.writeframes(data)
    checks['quality']=quality
    (folder/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(quality,flush=True)


if __name__=='__main__':main()
