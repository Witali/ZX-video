"""Independent full-stream Speex reference and actual Z80 port-event checks."""
import argparse
from collections import Counter
import ctypes as C
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import wave

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def sha(b):return hashlib.sha256(b).hexdigest()
def host_fixture(out,source,host=None):
    host=host or out/'host'
    ref=C.CDLL(str(host/'reference.dll'));dec=C.CDLL(str(host/'decoder.dll'))
    with wave.open(str(source),'rb') as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,1,8000)
        pcm=w.readframes(w.getnframes())
    assert len(pcm)%160==0
    ref.reference_reset();dec.zx_speex_reset()
    packed=bytearray();expected=bytearray()
    for start in range(0,len(pcm),160):
        data=(C.c_short*160)(*[(x-128)*256 for x in pcm[start:start+160]])
        packet=(C.c_char*20)();a=(C.c_short*160)();b=(C.c_short*160)()
        assert ref.reference_encode(data,packet)==20
        assert ref.reference_decode(packet,a)==0
        assert dec.zx_speex_decode(packet,b)==0
        if list(a)!=list(b):
            mismatch=next(i for i in range(160) if a[i]!=b[i])
            raise AssertionError(('host PCM16',start+mismatch,a[mismatch],b[mismatch],list(a)[:16],list(b)[:16]))
        packed.extend(bytes(packet));expected.extend(bytes(a))
    (out/'input.spxraw').write_bytes(packed)
    (out/'reference.pcm16').write_bytes(expected)
    report=dict(source_sha256=sha(pcm),frames=len(pcm)//160,samples=len(pcm),payload_bytes=len(packed),
                payload_sha256=sha(packed),reference_pcm16_sha256=sha(expected),host_every_pcm16_exact=True)
    (out/'host-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report,flush=True)
    return report

def image(path):
    data={}
    for line in path.read_text().splitlines():
        row=bytes.fromhex(line[1:]);assert sum(row)%256==0
        if row[3]==0:
            address=int.from_bytes(row[1:3],'big')
            data.update((address+i,v) for i,v in enumerate(row[4:4+row[0]]))
    return data

def native(out,variant='pure-r4',binary=None,require_exact=True):
    from z80 import Z80Machine
    folder=out/variant
    folder.mkdir(parents=True,exist_ok=True)
    binary=binary or folder
    mapping=(binary/'player.map').read_text()
    symbols={name:int(addr,16) for addr,name in re.findall(r'([0-9A-F]{8})\s+(_\w+)\s',mapping)}
    memory=image(binary/'player.ihx');payload=(out/'input.spxraw').read_bytes()
    assert len(payload)%20==0 and 0<len(payload)<=4915*20
    samples=struct.unpack('<'+'h'*((out/'reference.pcm16').stat().st_size//2),(out/'reference.pcm16').read_bytes())
    expected=bytes((x>>8)+128 for x in samples)
    m=Z80Machine();m.memory[:]=b'\xa5'*65536
    for a,v in memory.items():m.memory[a]=v
    # Pure assembly must initialize its own state; poison RAM to expose omissions.
    # The historical compiled-C benchmark needs the usual static zero fill.
    bss_start=int(re.search(r'([0-9A-F]{8})\s+s__DATA',mapping)[1],16)
    bss_size=int(re.search(r'([0-9A-F]{8})\s+l__DATA',mapping)[1],16)
    state_fill=0xa5 if variant.startswith('pure-') else 0
    m.memory[bss_start:bss_start+bss_size]=bytes([state_fill])*bss_size
    assert max(memory)<bss_start and bss_start+bss_size<0xbf00
    m.memory[symbols['_packet_count']:symbols['_packet_count']+2]=(len(payload)//20).to_bytes(2,'little')
    def bad_write(address,value):
        raise AssertionError(('write outside state/stack',hex(m.pc),hex(address),value))
    m.mark_addrs(0,65536,m.WRITE_MARK)
    m.unmark_addrs(bss_start,bss_size,m.WRITE_MARK)
    m.unmark_addrs(0xbf00,256,m.WRITE_MARK)
    # Allow only declared immediate operand bytes, never an entire code region.
    smc={v for k,v in symbols.items() if re.fullmatch(r'_smc\d+',k)}
    for address in smc:
        assert address in memory and memory[address-1]==0x2e
        m.unmark_addrs(address,1,m.WRITE_MARK)
    dynamic=[]
    for name in ('innovation','coefficient'):
        if '_'+name+'_start' in symbols:
            lo=symbols['_'+name+'_start'];hi=symbols['_'+name+'_end']
            assert 0x7200<=lo<hi<=0x8000
            m.unmark_addrs(lo,hi-lo,m.WRITE_MARK);dynamic.append((lo,hi))
    m.set_write_callback(bad_write)
    current=0;events=[];pages=[];actual16=[];actual8=[]
    order=(0,1,3,4,6,7) if variant.startswith('pure-') else (0,1)
    banks={order[i//16384]:payload[i:i+16384].ljust(16384,b'\xa5') for i in range(0,len(payload),16384)}
    m.set_memory_block(0xc000,banks[0])
    budget=2_000_000_000
    m.ticks_to_stop=budget
    elapsed=0;last_remaining=budget;last_frame_tick=m.frame_tick
    def clock():
        # ticks_to_stop clamps at zero inside an instruction. Recover its
        # overshoot from the independent modulo-100000 frame clock.
        nonlocal elapsed,last_remaining,last_frame_tick
        approx=last_remaining-m.ticks_to_stop
        delta=approx+(m.frame_tick-last_frame_tick-approx)%100000
        elapsed+=delta
        last_remaining=m.ticks_to_stop;last_frame_tick=m.frame_tick
        return elapsed
    phases=Counter();phase_starts={};returns={}
    def output(port,value):
        nonlocal current
        if port==0x7ffd:
            assert bytes(m.memory[0xc000:])==banks[current],'input changed'
            current=value&7;pages.append(current)
            assert current in banks
            m.set_memory_block(0xc000,banks[current])
        else:
            assert port&255==0xfb,(hex(port),value)
            index=len(events)
            assert index<len(expected),'extra output'
            pcm_address=symbols['_last_pcm16'] if '_last_pcm16' in symbols else symbols['_pcm']+2*(index%160)
            want=struct.pack('<h',samples[index])
            actual16.append(int.from_bytes(m.memory[pcm_address:pcm_address+2],'little',signed=True))
            actual8.append(value)
            if require_exact:
                assert bytes(m.memory[pcm_address:pcm_address+2])==want,('Z80 PCM16',index,bytes(m.memory[pcm_address:pcm_address+2]).hex(),want.hex())
                assert value==expected[index],('Z80 PCM8',index,value,expected[index])
            events.append(clock())
    m.set_output_callback(output);m.pc=symbols['_entry'];m.sp=0xbffe
    m.set_breakpoint(symbols['_complete'])
    watches={symbols[k]:k for k in ('_zx_speex_filter','_zx_speex_lpc') if k in symbols}
    for address in watches:m.set_breakpoint(address)
    while True:
        event=m.run()
        if m.pc==symbols['_complete']:break
        tick=clock()
        if m.pc in watches:
            name=watches[m.pc];phase_starts[name]=tick
            ret=int.from_bytes(m.memory[m.sp:m.sp+2],'little')
            returns[ret]=name;m.set_breakpoint(ret);m.step_over_breakpoint()
        elif m.pc in returns:
            name=returns[m.pc];phases[name]+=tick-phase_starts[name];m.step_over_breakpoint()
        if event&m._TICKS_LIMIT_HIT:
            clock();m.ticks_to_stop=budget;last_remaining=budget
            assert elapsed<100_000_000_000,'CPU timeout'
    total=clock()
    assert len(events)==len(expected)
    assert int.from_bytes(m.memory[symbols['_status']:symbols['_status']+2],'little')==0
    assert all(m.memory[a]==v for a,v in memory.items() if a not in smc),'static code/table changed'
    assert bytes(m.memory[0xc000:])==banks[current],'input changed'
    intervals=[b-a for a,b in zip(events,events[1:])]
    report=dict(complete=True,samples=len(events),every_pcm8_exact=bytes(actual8)==expected,every_pcm16_exact=tuple(actual16)==samples,total_tstates=total,
                seconds_at_3_5_mhz=total/3500000,mean_total_tstates_per_sample=total/len(events),
                first_out_tstates=events[0],last_out_tstates=events[-1],
                min_out_interval=min(intervals),max_out_interval=max(intervals),
                out_intervals_histogram=dict(sorted(Counter(intervals).items())),
                nominal_late_samples=sum(2*(t-events[0])>875*i for i,t in enumerate(events)),
                max_lateness_tstates=max(t-events[0]-437.5*i for i,t in enumerate(events)),
                real_time=total<=len(events)*437.5 and max(intervals)<=438,
                pages=pages,code_rodata_bytes=len(memory),bss_bytes=bss_size,
                code_bytes=sum(a>=0x8000 for a in memory),tables_bytes=sum(a<0x8000 for a in memory),
                all_cpu_writes_inside_declared_regions=True,input_static_code_static_tables_unchanged=True,
                writable_immediate_addresses=sorted(smc),
                pcm16_output_buffer='_last_pcm16' not in symbols,
                initial_state_fill=state_fill,
                dynamic_table_reserved_bytes=sum(hi-lo for lo,hi in dynamic),
                dynamic_table_regions=dynamic,
                table_arena_span_bytes=max([a+1 for a in memory if a<0x8000]+[hi for lo,hi in dynamic]+[0x4000])-0x4000,
                phases_tstates=dict(phases),
                binary_sha256=sha(bytes(memory[a] for a in sorted(memory))),
                clock_hz=3500000,ula_contention_included=False,physical_hardware_tested=False)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (folder/'out-times.u64.gz').write_bytes(gzip.compress(struct.pack('<'+'Q'*len(events),*events),mtime=0))
    if not require_exact:
        (folder/'actual.pcm16').write_bytes(struct.pack('<'+'h'*len(actual16),*actual16))
        (folder/'actual.pcm8').write_bytes(bytes(actual8))
    print({k:v for k,v in report.items() if k!='out_intervals_histogram'},flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'build/speex-port')
    p.add_argument('--source',type=Path,default=Path('C:/Work/ZX-video/audiobook-beeper/experiments/ima-waveform/source-preview.wav'))
    p.add_argument('--host-only',action='store_true');p.add_argument('--native-only',action='store_true')
    p.add_argument('--restore-fixture',action='store_true',help='Restore the saved speech packets and independent PCM16 reference')
    p.add_argument('--variant',default='pure-r4');a=p.parse_args()
    if a.restore_fixture:
        a.output.mkdir(parents=True,exist_ok=True)
        for name in ('input.spxraw','reference.pcm16'):
            (a.output/name).write_bytes(gzip.decompress((HERE/'evidence'/(name+'.gz')).read_bytes()))
    if not a.native_only:host_fixture(a.output,a.source)
    if not a.host_only:native(a.output,a.variant)
