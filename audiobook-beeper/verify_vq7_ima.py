"""Full VQ7-to-IMA native CPU proof; excludes ROM, ULA and output-RAM banking.

The decoder reads the real regrouped nine-bit stream from two input banks.
It emits nibbles to a test port; it does not claim an integrated TRD, final
resident IMA layout, loading progress or real PDM playback. The unchanged
baseline IMA encoder is included rather than estimated from a C routine.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import wave
from collections import Counter
import numpy as np
from z80 import Z80Machine
from build_lpc_disk import assemble
from ima_codec import STEPS
from verify_pcm import save


def verify(source,out,name):
    codec_name=name
    out.mkdir(parents=True,exist_ok=True)
    with wave.open(str(source/(name+'-preview.wav')),'rb') as w:
        pcm=bytearray(w.readframes(w.getnframes()))
    pcm[-128:]=bytes([128])*128
    packed=gzip.decompress((source/(name+'.ima.gz')).read_bytes())
    expected=np.empty(len(pcm),dtype='u1')
    data=np.frombuffer(packed,'u1');expected[::2]=data&15;expected[1::2]=data>>4
    bits=np.unpackbits(np.frombuffer(gzip.decompress((source/(name+'.data.gz')).read_bytes()),'u1'))
    vectors=(len(pcm)+6)//7
    ids=(bits[:vectors*9].reshape(-1,9)@(1<<np.arange(8,-1,-1))).astype(int)
    stream=bytearray()
    for start in range(0,len(ids),8):
        group=ids[start:start+8]
        stream.append(sum(int(code>>8)<<i for i,code in enumerate(group)))
        stream.extend((group&255).tolist())
    assert len(stream)<=32768
    raw_book=gzip.decompress((source/(name+'.book.gz')).read_bytes())
    book=np.full((512,8),0xa5,dtype='u1');book[:,:7]=np.frombuffer(raw_book,'u1').reshape(512,7)
    (out/'dictionary.bin').write_bytes(book.tobytes())
    (out/'compressed.bin').write_bytes(stream)
    (out/'ima-steps.bin').write_bytes(struct.pack('<89H',*STEPS))
    samples=len(pcm)-128
    first=(samples-1)%65536+1;segments=(samples+65535)//65536
    (out/'vq-config.inc').write_text(f'predictive: EQU {int(name.startswith("pvq"))}\nfirst_segment_samples: EQU {first}\nsegment_count: EQU {segments}\n')
    baseline=Path(__file__).with_name('lpc-preload.asm').read_text()
    encoder=baseline[baseline.index('QUANTIZE: MACRO'):baseline.index('\ndisk_position:')]
    (out/'ima-encoder.inc').write_text(encoder,encoding='utf-8',newline='\n')
    shutil.copy2(Path(__file__).with_name('probe-vq7-ima.asm'),out/'probe.asm')
    labels=assemble(out,'probe');blob=(out/'probe.bin').read_bytes()
    m=Z80Machine();m.memory[:]=b'\xa5'*65536;m.set_memory_block(0x8000,blob)
    current=None;pages=[];actual=[];count=0;pcm_times=[];ima_times=[];phase_start=0
    phases=Counter();budget=500_000_000
    def output(port,value):
        nonlocal current
        if port==0x7FFD:
            assert value in (19,23)
            current=value&7;pages.append(current)
            start=0 if current==3 else 16384
            chunk=stream[start:start+16384];m.set_memory_block(0xC000,chunk+bytes([0xa5])*(16384-len(chunk)))
        else:
            assert port&255==1
            actual.append(value)
    m.set_output_callback(output);m.pc=labels['start'];m.ticks_to_stop=budget
    watches={labels[k]:k for k in ('next_pcm','pcm_ready','guard_pcm_ready','encode_ima','ima_ready','guard_ima_ready','complete')}
    for address in watches:m.set_breakpoint(address)
    while True:
        if m.run()&m._TICKS_LIMIT_HIT:raise AssertionError('CPU probe timeout')
        if m.pc not in watches:continue  # the core also yields at frame boundaries
        name=watches[m.pc];now=budget-m.ticks_to_stop
        if name=='complete':break
        if name in ('next_pcm','encode_ima'):phase_start=now
        elif name in ('pcm_ready','guard_pcm_ready'):
            assert m.a==pcm[count],('PCM',count,m.a,pcm[count])
            count+=1
            if name=='pcm_ready':pcm_times.append(now-phase_start);phases['vq_decoder_tstates']+=now-phase_start
        elif name in ('ima_ready','guard_ima_ready'):
            assert m.a==expected[len(actual)],('IMA',len(actual),m.a,int(expected[len(actual)]))
            ima_times.append(now-phase_start);phases['ima_encoder_tstates']+=now-phase_start
        m.step_over_breakpoint()
    assert count==len(pcm) and np.array_equal(actual,expected)
    assert pages==[3,7]
    assert bytes(m.memory[0x9000:labels['code_end']])==blob[0x1000:],'dictionary/steps changed'
    assert m.memory[labels['ima_index']]==0 and int.from_bytes(m.memory[labels['ima_predictor']:labels['ima_predictor']+2],'little')==32768
    elapsed=budget-m.ticks_to_stop
    report=dict(scope=__doc__,complete=True,codec=codec_name,
        pcm_samples_verified=count,ima_nibbles_verified=len(actual),
        every_pcm_and_ima_exact=True,source_input_pages=pages,total_native_tstates=elapsed,
        cpu_only_seconds=elapsed/3546900,phases=dict(phases),
        decoder_call_excluded_histogram=dict(sorted(Counter(pcm_times).items())),
        ima_call_excluded_histogram=dict(sorted(Counter(ima_times).items())),
        vq_mean_tstates=float(np.mean(pcm_times)),ima_mean_tstates=float(np.mean(ima_times)),
        regrouped_payload_bytes=len(stream),stored_dictionary_bytes=len(raw_book),
        expanded_dictionary_ram_bytes=4096,container_allowance_bytes=32,
        pcm16_to_grouped_codec_ratio=2*len(pcm)/(len(stream)+len(raw_book)+32),
        dictionary_steps_readonly=True,original_ima_encoder_source_sha256=hashlib.sha256(encoder.encode()).hexdigest(),
        binary_sha256=hashlib.sha256(blob).hexdigest(),integrated_trd_verified=False,
        physical_hardware_tested=False)
    save(out/'report.json',report);print(json.dumps(report),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--codec',default='vq7x512',choices=['vq7x512','pvq7x512'])
    a=p.parse_args();verify(a.input,a.output,a.codec)
