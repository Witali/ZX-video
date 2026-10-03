"""Execute the actual LPC preloader; ROM disk reads are byte-copy stubs only."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import wave

import numpy as np
from z80 import Z80Machine
from lpc_preload import table, multiply
from verify_pcm import save


def primitives(blob, labels):
    m=Z80Machine();m.set_memory_block(0x8000,blob)
    stop=0x7FFF;m.set_breakpoint(stop)
    def invoke(name):
        m.sp=0x5FF0;m.memory[0x5FF0:0x5FF2]=bytes([255,127]);m.pc=labels[name]
        m.ticks_to_stop=10_000_000
        while m.pc!=stop:
            assert not m.run() & m._TICKS_LIMIT_HIT
        return 10_000_000-m.ticks_to_stop
    times=[];cases=0
    rng=np.random.default_rng(1977)
    for k in (-32604,-27853,-128,-1,0,1,127,128,27853,32604):
        m.de=k&65535;m.a=0x60;times.append(invoke('build_table'))
        actual=np.array([m.memory[0x6000+i]+256*m.memory[0x6100+i] for i in range(256)],dtype=np.uint16).view(np.int16)
        wanted=table(k);assert np.array_equal(actual,wanted),(k,'table')
        for x in [-16384,-129,-128,-1,0,1,127,128,16383,*rng.integers(-16384,16384,64)]:
            m.hl=int(x)&65535;m.a=0x60
            invoke('mul_table')
            result=m.hl if m.hl<32768 else m.hl-65536
            assert result==multiply(wanted,int(x)),(k,x,result,multiply(wanted,int(x)))
            assert abs(result-(k*int(x)//32768))<=2
            cases+=1
    return dict(table_coefficients=10,multiply_cases=cases,every_result_exact=True,
                table_native_tstates_min=min(times),table_native_tstates_max=max(times))


def verify(path):
    meta=json.loads((path/'player.json').read_bytes());info=meta['lpc_preload'];labels=info['labels']
    blob=(path/'assembly/lpc-preload.bin').read_bytes();disk=(path/'audiobook-preview.trd').read_bytes()
    packed=gzip.decompress((path/'soundtrack.ima.gz').read_bytes())
    with wave.open(str(path/'source-preview.wav'),'rb') as w: pcm=w.readframes(w.getnframes())
    arithmetic=primitives(blob,labels)
    m=Z80Machine();m.memory[:]=b'\xa5'*65536;m.set_memory_block(0x8000,blob)
    banks={i:bytearray(b'\xa5'*16384) for i in range(8)}
    current=0;page_events=[];reads=[];pcm_count=byte_count=0;load=[];unpack=[]
    def page(bank):
        nonlocal current
        if current==2:
            m.memory[0xB800:0xC000]=m.memory[0xF800:0x10000]
            banks[2][:]=m.memory[0x8000:0xC000]
        else:banks[current][:]=m.memory[0xC000:0x10000]
        current=bank
        if bank==2:banks[2][:]=m.memory[0x8000:0xC000]
        m.set_memory_block(0xC000,banks[bank]);page_events.append(bank)
    def output(port,value):
        if port==0x7FFD:
            assert 16<=value<=23,(port,value)
            page(value&7)
        else:assert port==254 and value==0,(port,value)
    budget=3_000_000_000
    m.set_output_callback(output);m.pc=0x8000;m.ticks_to_stop=budget
    watches={labels[k]:k for k in ('pcm_ready','guard_pcm_ready','ima_byte_ready','load_progress_event','unpack_progress_event','unpack_complete')}
    for address in (*watches,0x3D13):m.set_breakpoint(address)
    while True:
        if m.run() & m._TICKS_LIMIT_HIT:raise AssertionError(('preloader exceeded native budget',hex(m.pc),pcm_count,byte_count,len(reads),load,unpack))
        if m.pc==0x3D13:
            assert m.bc==0x0105
            sector=(m.d*16)+m.e;destination=m.hl
            assert 0xC000<=destination<=0xFF00
            data=disk[sector*256:(sector+1)*256];assert len(data)==256
            m.set_memory_block(destination,data);reads.append((sector,current,destination))
            m.pc=int.from_bytes(m.memory[m.sp:m.sp+2],'little');m.sp+=2
            continue
        name=watches.get(m.pc)
        if name=='unpack_complete':break
        if name in ('pcm_ready','guard_pcm_ready'):
            assert m.a==pcm[pcm_count],('PCM',pcm_count,m.a,pcm[pcm_count],hex(m.pc))
            pcm_count+=1
        elif name=='ima_byte_ready':
            assert m.a==packed[byte_count],('IMA',byte_count,m.a,packed[byte_count])
            byte_count+=1
        elif name=='load_progress_event':
            step=m.memory[labels['load_progress']];load.append(step)
            assert bytes(m.memory[0x5940:0x5960])==bytes([0x64])*step+bytes([0x49])*(32-step)
        elif name=='unpack_progress_event':
            step=m.memory[labels['unpack_progress']];unpack.append(step)
            assert byte_count==(len(packed)*step+31)//32,(step,byte_count)
            assert bytes(m.memory[0x5A00:0x5A20])==bytes([0x64])*step+bytes([0x49])*(32-step)
        if name:m.step_over_breakpoint()
    elapsed=budget-m.ticks_to_stop
    page(current)
    assert pcm_count==len(pcm) and byte_count==len(packed)
    assert load==unpack==list(range(1,33))
    assert len(reads)==info['load_sectors']
    restored=b''.join(bytes(banks[s['bank']][s['address']-0xC000:]) for s in meta['sections'])
    assert restored==packed,'resident RAM differs after paging'
    assert bytes(m.memory[0x8000:labels['disk_position']])==blob[:labels['disk_position']-0x8000],'code overwritten'
    (path/'prepared-screen.scr').write_bytes(m.memory[0x4000:0x5B00])
    report=dict(complete=True,arithmetic=arithmetic,pcm_samples_verified=pcm_count,ima_bytes_verified=byte_count,
                full_resident_ima_exact=True,preloader_code_unchanged=True,progress_load=load,progress_unpack=unpack,
                disk_sectors=len(reads),disk_reads_only_before_conversion=True,native_tstates=elapsed,
                cpu_only_seconds_at_3546900=elapsed/3546900,scope='Actual Z80 synthesis/IMA; excludes ROM, disk latency and ULA waits',
                physical_hardware_tested=False,ima_sha256=hashlib.sha256(restored).hexdigest())
    save(path/'preload-native.json',report);print(json.dumps(report),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path)
    verify(p.parse_args().directory)
