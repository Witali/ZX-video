"""Build and verify full banked PVQ3x1024 PCM8 playback at a nominal 3.5 MHz."""
from collections import Counter
import gzip
import json
from pathlib import Path
import struct
import wave
import numpy as np
from build import run
from check_approx import snr
from check_primitives import symbols,timing
from verify import ROOT,HERE,sha,image
from z80 import Z80Machine

ORDER=(0,1,3,4,6,7)
CHUNK=16380  # 3276 complete five-byte groups; no group crosses a bank edge.


def delay(t):
    """Preserve A, BC, DE and HL; only flags and private stack may change."""
    assert t>=0
    for pairs in range(t//21,-1,-1):
        for compares in range(4):
            rest=t-pairs*21-compares*7
            if rest>=0 and rest%4==0:
                return (f'; Delay {t} T: PUSH/POP AF=21, CP n=7, NOP=4.\n'+
                        'push af\npop af\n'*pairs+'cp #0\n'*compares+'nop\n'*(rest//4))
    raise ValueError(('unrepresentable delay',t))


def data_bytes(data):
    return '\n'.join('.db '+','.join(map(str,data[i:i+16])) for i in range(0,len(data),16))+'\n'


def assembly(samples,book,paced,*,tight=False):
    groups,tail=divmod(samples,12)
    assert 0<samples and groups<=65535
    code='''; PVQ3x1024, three signed residuals per vector, PCM8 DAC port FB.
; Valid encoder output has no sum overflow. IRQ disabled; nominal 3.5-MHz
; schedule excludes ULA contention. Code/tables/stack live above 8000.
; DE input cursor, C four packed high fields, B predictor, HL dictionary
; address, IXH previous sample, IY remaining complete 12-sample groups.
.module pvq_port
.globl _entry, _complete, _bank_index, _after_page
.area _DATA
_bank_index: .ds 1
.area _CODE
_entry::
di
ld sp,#0xbffe
xor a,a
ld (_bank_index),a
ld a,#16
ld bc,#0x7ffd
out (c),a
ld ix,#0x8000
ld de,#0xc000
'''+f'ld iy,#{groups}\n'
    if not groups:code+='jp tail_start\n'
    vector='''; Form the aligned four-byte row from the low byte and two high bits.
ld a,(de)
inc de
ld l,a
ld h,#0x88
ld a,(hl)
inc h
ld h,(hl)
ld l,a
ld a,c
and a,#3
rlca
rlca
or a,h
ld h,a
srl c
srl c
; floor(last_signed/2)+128, exactly matching the encoder's recurrence.
ld a,ixh
srl a
add a,#64
ld b,a
'''
    sample='ld a,(hl)\ninc l\nadd a,b\nld ixh,a\n'
    def block(n,prefix):
        text=prefix+'_start:\ncall ensure_bank\nld a,(de)\ninc de\nld c,a\n'
        for i in range(n):
            if i%3==0:text+=vector
            if tight:
                # Only the last reconstructed value becomes the next predictor.
                # The next vector reloads HL, so its final INC L is also dead.
                text+='; Keep history only at vector end; no dead final pointer increment.\nld a,(hl)\n'
                if i%3!=2:text+='inc l\n'
                text+='add a,b\n'
                if i%3==2:text+='ld ixh,a\n'
            else:text+=sample
            # Includes previous group control on slot zero, CALL/RET and OUT.
            base=363 if i==0 else 150 if i%3==0 else 34
            if tight:base-=4 if i%3==2 else 8
            if paced:text+=delay(438-i%2-base)
            text+=f'.globl _{prefix}_out{i}\n_{prefix}_out{i}::\nout (0xfb),a\n'
        return text
    code+=block(12,'group')
    code+='dec iy\nld a,iyh\nor a,iyl\njp nz,group_start\n'
    if tail:code+=block(tail,'tail')
    else:code+='tail_start:\n'
    code+='''_complete::
halt
jp _complete
; Exactly 143 T including RET on every path. A bank holds 3276 groups;
; four unused bytes prevent a vector/header from straddling the boundary.
; Clobbers AF/BC/HL, replaces DE only when a bank switch is needed.
ensure_bank:
ld a,d
cp #255
jr nz,page_fast
ld a,e
cp #252
jr nz,page_slow
ld a,(_bank_index)
inc a
ld (_bank_index),a
ld l,a
ld h,#0x8a
ld a,(hl)
or a,#16
ld bc,#0x7ffd
out (c),a
ld de,#0xc000
jp _after_page
_after_page::
ret
page_fast:
'''+delay(110)+'''ret
page_slow:
'''+delay(92)+'''ret
.globl _code_end
_code_end::
.area _TABLES (ABS)
.org 0x8800
'''+data_bytes(bytes((i*4)&255 for i in range(256)))
    code+='.org 0x8900\n'+data_bytes(bytes(0x90+(i>>6) for i in range(256)))
    code+='.org 0x8a00\n'+data_bytes(bytes(ORDER))
    expanded=np.full((1024,4),165,dtype='u1');expanded[:,:3]=book.view('u1')
    code+='.org 0x9000\n'+data_bytes(expanded.tobytes())
    # sdasz80 does not accept index-half mnemonics. Emit their normal Z80
    # encodings explicitly; each takes the base register opcode's 4 T + prefix 4 T.
    for mnemonic,opcode in [('ld a,ixh','0xdd,0x7c'),('ld ixh,a','0xdd,0x67'),
                            ('ld a,iyh','0xfd,0x7c'),('or a,iyl','0xfd,0xb5')]:
        code=code.replace(mnemonic+'\n',f'.db {opcode} ; {mnemonic}, 8 T (index-half instruction)\n')
    return code


def build(folder,samples,book,paced,*,tight=False):
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'decoder.s').write_text(assembly(samples,book,paced,tight=tight),newline='\n')
    cc=Path('C:/Work/ZX-video/.tmp/z80-c-compilers/sdcc/bin/sdcc.exe')
    run([str(cc.with_name('sdasz80.exe')),'-plosgff','decoder.rel','decoder.s'],folder/'asm.log',folder)
    run([str(cc),'-mz80','--no-std-crt0','--code-loc','0x8000','--data-loc','0xb000','decoder.rel','-o','player.ihx'],folder/'link.log',folder)
    assert symbols(folder)['_code_end']<=0x8800,'code overlaps lookup tables'


def prepare(folder,stream):
    s=symbols(folder);m=Z80Machine();m.memory[:]=b'\xa5'*65536
    mem=image(folder/'player.ihx')
    for a,v in mem.items():m.memory[a]=v
    assert len(stream)<=6*CHUNK
    banks={ORDER[i//CHUNK]:stream[i:i+CHUNK].ljust(16384,b'\xa5') for i in range(0,len(stream),CHUNK)}
    m.mark_addrs(0,65536,m.WRITE_MARK)
    m.unmark_addrs(s['_bank_index'],1,m.WRITE_MARK);m.unmark_addrs(0xbf00,256,m.WRITE_MARK)
    def bad_write(a,v):raise AssertionError(('PVQ write outside state/stack',hex(m.pc),hex(a),v))
    m.set_write_callback(bad_write);m.pc=s['_entry'];m.sp=0xbffe
    return m,s,mem,banks


def execute(folder,stream,expected,paced,audit_first=False):
    m,s,mem,banks=prepare(folder,stream);events=[];actual=[];pages=[];current=None
    budget=200_000_000;m.ticks_to_stop=budget
    audits=Counter();audited_t=0;instructions=0
    def emit(port,value):
        nonlocal current
        if port==0x7ffd:
            if current is not None:assert bytes(m.memory[0xc000:])==banks[current]
            current=value&7;assert current in banks
            m.set_memory_block(0xc000,banks[current]);pages.append(current)
        else:
            assert port&255==0xfb
            i=len(actual);assert i<len(expected) and value==expected[i],(i,value,expected[i] if i<len(expected) else None)
            actual.append(value);events.append(budget-m.ticks_to_stop)
    m.set_output_callback(emit);m.set_breakpoint(s['_complete'])
    if audit_first:
        # Audit startup plus 24 outputs, and another 24 spanning the first bank
        # switch. Prefix-yield handling matches the exact Speex timing auditor.
        def audit_until(outputs):
            nonlocal instructions,audited_t
            while len(actual)<outputs and m.pc!=s['_complete']:
                pc=m.pc;want=timing(m);before=m.frame_tick
                m.ticks_to_stop=5 if m.memory[pc] in (0xdd,0xfd) else 1
                m.run();got=(m.frame_tick-before)%100000
                if m.memory[pc] in (0xdd,0xfd) and got==4 and m.pc==(pc+1)&65535:
                    before=m.frame_tick;m.ticks_to_stop=1;m.run();got+=(m.frame_tick-before)%100000
                assert got==want,(hex(pc),got,want)
                audits[got]+=1;audited_t+=got;instructions+=1
        audit_until(min(24,len(expected)))
        boundary=(CHUNK//5)*12
        if len(expected)>boundary+12:
            address=s['_group_out0'];m.set_breakpoint(address)
            while len(actual)<boundary-12:
                m.ticks_to_stop=budget;m.run()
                if m.pc==address:m.step_over_breakpoint()
            m.clear_breakpoint(address)
            audit_until(boundary+12)
            assert len(pages)>=2
        return dict(instructions=instructions,tstates=audited_t,
                    covers_first_bank_switch=len(expected)>boundary+12,
                    every_instruction_matches_timing_model=True,histogram=dict(sorted(audits.items())))
    while m.pc!=s['_complete']:
        event=m.run();assert not(event&m._TICKS_LIMIT_HIT),'native timeout'
    assert len(actual)==len(expected)
    assert bytes(m.memory[0xc000:])==banks[current]
    assert all(m.memory[a]==v for a,v in mem.items())
    intervals=[b-a for a,b in zip(events,events[1:])]
    if paced:
        assert intervals==[438-i%2 for i in range(1,len(events))]
        assert all(t-events[0]==437*i+i//2 for i,t in enumerate(events))
    by_slot={str(i):dict(Counter(intervals[j-1] for j in range(1,len(events)) if j%12==i)) for i in range(12)}
    report=dict(samples=len(actual),total_cpu_tstates=budget-m.ticks_to_stop,
                first_out_tstates=events[0],last_out_tstates=events[-1],
                min_interval=min(intervals) if intervals else None,max_interval=max(intervals) if intervals else None,
                intervals_by_slot=by_slot,pages=pages,all_pcm8_exact_to_vq_reference=True,
                all_memory_writes_guarded=True,input_code_tables_unchanged=True,
                nominal_437_438_schedule_verified=paced,ula_contention_included=False,physical_hardware_tested=False,
                code_bytes=s['_code_end']-0x8000,table_ram_bytes=512+6+4096,state_bytes=1,stack_reserved_bytes=256,
                binary_sha256=sha(bytes(mem[a] for a in sorted(mem))))
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (folder/'out-times.u64.gz').write_bytes(gzip.compress(struct.pack('<'+'Q'*len(events),*events),mtime=0))
    return report


def main():
    out=ROOT/'build/speex-port/pvq';out.mkdir(parents=True,exist_ok=True)
    inputs=ROOT/'audiobook-beeper/experiments/dense-codecs'
    source_path=Path('C:/Work/ZX-video/audiobook-beeper/experiments/ima-waveform/source-preview.wav')
    with wave.open(str(source_path),'rb') as w:source=w.readframes(w.getnframes())
    assert sha(source)==json.loads((inputs/'report.json').read_text())['source_sha256']
    book_bytes=gzip.decompress((inputs/'pvq3x1024-half.book.gz').read_bytes())
    book=np.frombuffer(book_bytes,'i1').reshape(1024,3)
    packed=gzip.decompress((inputs/'pvq3x1024-half.data.gz').read_bytes())
    count=(len(source)+2)//3
    codes=(np.unpackbits(np.frombuffer(packed,'u1'))[:count*10].reshape(-1,10)@(1<<np.arange(9,-1,-1))).astype(int)
    codes=np.pad(codes,(0,(-len(codes))%4))
    stream=bytearray();expected=[];last=128
    for start in range(0,len(codes),4):
        group=codes[start:start+4]
        stream.append(sum(int(code>>8)<<(2*i) for i,code in enumerate(group)))
        stream.extend((group&255).tolist())
    for code in codes[:count]:
        values=book[code].astype(int)+(last//2+64)
        assert np.all((values>=0)&(values<=255))
        expected.extend(values.tolist());last=int(values[-1])
    expected=bytes(expected[:len(source)]);stream=bytes(stream)
    # Fixed 32-byte file header; player constants are produced from these fields.
    header=struct.pack('<4sBBBBIII',b'PVQ8',1,3,10,0,8000,len(source),len(stream)).ljust(32,b'\0')
    encoded=header+book_bytes+stream;(out/'audio.pvq').write_bytes(encoded)
    results={}
    for name,paced in [('unpaced',False),('paced',True)]:
        folder=out/name;build(folder,len(expected),book,paced)
        results[name]=execute(folder,stream,expected,paced)
        print(name,{k:v for k,v in results[name].items() if k!='intervals_by_slot'},flush=True)
    results['instruction_audit']=execute(out/'paced',stream,expected,True,audit_first=True)
    tails=[]
    for n in (1,2,3,11,12,13):
        folder=out/f'tail-{n}';build(folder,n,book,True)
        tails.append(execute(folder,stream[:((n+11)//12)*5],expected[:n],True))
    results['tail_checks']=[dict(samples=r['samples'],all_pcm8_exact=r['all_pcm8_exact_to_vq_reference'],schedule_exact=r['nominal_437_438_schedule_verified']) for r in tails]
    results.update(source_pcm8_sha256=sha(source),original_bitpacked_sha256=sha(packed),dictionary_sha256=sha(book_bytes),
                   encoded_sha256=sha(encoded),pcm8_sha256=sha(expected),samples=len(source),
                   payload_bytes=len(stream),dictionary_stored_bytes=len(book_bytes),header_bytes=32,
                   total_stored_bytes=len(encoded),compression_vs_pcm8=len(source)/len(encoded),
                   unused_bytes_per_full_bank=4,raw_source_snr_db=snr([x-128 for x in source],[x-128 for x in expected]),
                   old_probe_decoder_mean_tstates=100.25,old_probe_driver_tstates=21,
                   decision='Select for nominal-CPU PCM8 playback, separately from exact Speex; ULA and physical hardware remain unverified.')
    with wave.open(str(out/'pvq.wav'),'wb') as w:
        w.setparams((1,1,8000,0,'NONE','not compressed'));w.writeframes(expected)
    (out/'report.json').write_text(json.dumps(results,indent=2)+'\n')
    target=HERE/'rounds/12';target.mkdir(exist_ok=True)
    for name in ('decoder.s','player.ihx','player.map','out-times.u64.gz'):(target/name).write_bytes((out/'paced'/name).read_bytes())
    (target/'report.json').write_bytes((out/'report.json').read_bytes())
    (target/'audio.pvq.gz').write_bytes(gzip.compress(encoded,mtime=0))
    print('Final',results['raw_source_snr_db'],results['compression_vs_pcm8'],results['instruction_audit'],flush=True)


if __name__=='__main__':main()
