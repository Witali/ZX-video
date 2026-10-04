"""Offline periodic-wave/noise experiment; native kernel includes transitions, not record loading."""
import gzip
import json
from pathlib import Path
import struct
import wave
import numpy as np
from build import run
from check_approx import snr
from check_primitives import machine,symbols,call,timing
from verify import ROOT,HERE,sha,image

ASM='''; Approximate 160-sample periodic-wave kernel, NOT a Speex decoder.
; Host supplies phase/step, 32 PCM8 wave entries at 9000, eight transition
; samples at 9020, and a page of signed noise at A000..AFFF. B is the sample
; counter, C the mixed wave value; AF/BC/DE/HL are clobbered. IRQ must be off.
.module periodic
.globl _kernel, _phase, _step, _noise_page, _noise_index
.area _DATA
_phase: .ds 2
_step: .ds 2
_noise_page: .ds 1
_noise_index: .ds 1
.area _CODE
_kernel::
ld b,#160
wave_loop:
ld hl,(_phase)
ld de,(_step)
add hl,de
ld (_phase),hl
; The top five phase bits address a 32-byte period. Integer lookup only.
ld a,h
rrca
rrca
rrca
and a,#31
ld l,a
ld h,#0x90
ld c,(hl)
ld a,(_noise_index)
inc a
ld (_noise_index),a
ld l,a
ld a,(_noise_page)
ld h,a
ld a,(hl)
add a,c
ld c,a
; The first eight samples are precomputed transition values in the record.
ld a,b
cp #153
jr c,wave_regular
ld a,#160
sub a,b
add a,#32
ld l,a
ld h,#0x90
ld c,(hl)
wave_regular:
ld a,c
out (0xfb),a
djnz wave_loop
ret
'''


def encode(source):
    rng=np.random.default_rng(711)
    noise=np.rint(rng.uniform(-1,1,256)[None,:]*np.linspace(0,31,16)[:,None]).astype('i1')
    records=[];restored=[];previous=128;noise_index=0
    for start in range(0,len(source),160):
        block=source[start:start+160].astype(float)-128
        best=None
        for period in range(24,145):
            step=round(65536/period)
            indices=((np.arange(160,dtype=np.int64)*step)&65535)>>11
            count=np.bincount(indices,minlength=32)
            book=np.rint(np.bincount(indices,weights=block,minlength=32)/np.maximum(count,1))
            book=np.clip(book,-96,96).astype(int)
            fit=book[indices];error=np.sum((fit-block)**2)
            if best is None or error<best[0]:best=(error,step,book,fit)
        error,step,book,fit=best
        # Add noise only where a periodic model explains less than 35% of power.
        power=float(np.sum(block**2))
        level=round(min(31,np.sqrt(error/160)*np.sqrt(3))*15/31) if error>0.65*power else 0
        ids=(noise_index+np.arange(1,161))&255;noise_index=int(ids[-1])
        values=fit+128+noise[level,ids].astype(int)
        assert np.all((values>=0)&(values<=255))
        values[:8]=(previous*(8-np.arange(1,9))+values[:8]*np.arange(1,9))//8
        previous=int(values[-1])
        records.append(struct.pack('<HB',step,level)+bytes((book+128).astype('u1'))+bytes(values[:8].astype('u1')))
        restored.extend(values.tolist())
    return b''.join(records),noise.tobytes(),bytes(restored)


def main():
    out=ROOT/'build/speex-port/wavetable';out.mkdir(parents=True,exist_ok=True)
    source_path=Path('C:/Work/ZX-video/audiobook-beeper/experiments/ima-waveform/source-preview.wav')
    with wave.open(str(source_path),'rb') as w:source=w.readframes(w.getnframes())
    assert sha(source)==json.loads((ROOT/'build/speex-port/host-report.json').read_text())['source_sha256']
    stream,noise,expected=encode(np.frombuffer(source,'u1'))
    assert len(stream)==(len(source)//160)*43
    (out/'wave.records').write_bytes(stream);(out/'noise.bin').write_bytes(noise)
    (out/'decoder.s').write_text(ASM,newline='\n')
    compiler=Path('C:/Work/ZX-video/.tmp/z80-c-compilers/sdcc/bin/sdcc.exe')
    run([str(compiler.with_name('sdasz80.exe')),'-plosgff','decoder.rel','decoder.s'],out/'asm.log',out)
    run([str(compiler),'-mz80','--no-std-crt0','--code-loc','0x8000','--data-loc','0xb000','decoder.rel','-o','player.ihx'],out/'link.log',out)
    m=machine(out);s=symbols(out);m.set_memory_block(0xa000,noise)
    m.mark_addrs(0,65536,m.WRITE_MARK)
    m.unmark_addrs(0xb000,6,m.WRITE_MARK);m.unmark_addrs(0xbf00,256,m.WRITE_MARK)
    def bad_write(address,value):raise AssertionError(('kernel write',address,value))
    m.set_write_callback(bad_write)
    actual=[];costs=[];m.memory[s['_noise_index']]=0
    def emit(port,value):
        assert port&255==0xfb
        actual.append(value)
    m.set_output_callback(emit)
    for start in range(0,len(stream),43):
        record=stream[start:start+43];step,level=struct.unpack('<HB',record[:3])
        m.memory[s['_phase']:s['_phase']+2]=((-step)&65535).to_bytes(2,'little')
        m.memory[s['_step']:s['_step']+2]=step.to_bytes(2,'little')
        m.memory[s['_noise_page']]=0xa0+level
        m.set_memory_block(0x9000,record[3:])
        costs.append(call(m,s['_kernel'],budget=100000))
    assert bytes(actual)==expected
    # Audit one complete kernel, including eight transition and 152 regular samples.
    m.sp=0xbffc;m.memory[m.sp:m.sp+2]=b'\x00\x7f';m.pc=s['_kernel'];audit_t=0;instructions=0
    m.set_output_callback(lambda p,v:None)
    while m.pc!=0x7f00:
        want=timing(m);before=m.frame_tick;m.ticks_to_stop=1;m.run()
        assert (m.frame_tick-before)%100000==want
        audit_t+=want;instructions+=1
    assert set(costs)=={audit_t}
    with wave.open(str(out/'periodic.wav'),'wb') as w:
        w.setparams((1,1,8000,0,'NONE','not compressed'));w.writeframes(expected)
    report=dict(samples=len(actual),source_pcm8_sha256=sha(source),record_bytes=43,
                payload_bytes=len(stream),noise_dictionary_bytes=len(noise),
                total_stored_bytes=len(stream)+len(noise),compression_vs_pcm8=len(source)/(len(stream)+len(noise)),
                table_ram_bytes=4096+40,state_bytes=6,
                code_bytes=len(image(out/'player.ihx')),all_kernel_writes_guarded=True,
                raw_source_snr_db=snr([x-128 for x in source],[x-128 for x in expected]),
                kernel_tstates=sum(costs),kernel_tstates_per_sample=sum(costs)/len(actual),
                per_block_kernel_tstates=audit_t,audited_instructions=instructions,
                every_kernel_instruction_matches_zilog=True,every_native_pcm8_matches_scalar_model=True,
                stream_loading_on_z80=False,uniform_pacing=False,ula_contention_included=False,
                physical_hardware_tested=False,real_time_verified=False,
                record_sha256=sha(stream),noise_sha256=sha(noise),pcm8_sha256=sha(expected),
                decision='Reject as selected playback: periodic/noise waveform error is large; native scope is kernel only, excluding record loading.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    target=HERE/'rounds/11';target.mkdir(exist_ok=True)
    for name in ('decoder.s','player.ihx','player.map','report.json'):(target/name).write_bytes((out/name).read_bytes())
    (target/'wave.records.gz').write_bytes(gzip.compress(stream,mtime=0))
    (target/'noise.bin.gz').write_bytes(gzip.compress(noise,mtime=0))
    print(report,flush=True)


if __name__=='__main__':main()
