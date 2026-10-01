"""Bounded Z80 LPC/PDM feasibility probe, not a decoder or release player.

Measure deliberately favorable lookup MACs, with ready-made per-coefficient
tables and 8-bit history. Frame parsing, excitation, coefficient/table changes,
history update, saturation and output filtering are NOT silently counted free
in a release: they are explicitly outside these optimistic microbenchmarks.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
from pcm_player import MiniAssembler,CPU_CLOCK
from verify_pcm import reference,save

ROOT=Path(__file__).resolve().parent.parent
TABLE=0xc000
HISTORY=0xf000
PDM_VALUE=73


def build_kernel(order,word_product,interleave):
    a=MiniAssembler(0x8000)
    # The synthesis accumulator is IX (16-bit) or A (8-bit). Alternate
    # AF/BC/DE hold the unchanged live PDM state. No interrupt service.
    a.emit(0xf3,0x31); a.word(HISTORY)
    a.emit(0xdd,0x21); a.word(0)
    a.emit(0xaf,0xd9,0x01); a.word(0x10fe)
    a.emit(0x16,PDM_VALUE,0x1e,0,0x08,0x3e,128,0x08,0xd9)
    ops=[]
    def op(name,t,*code): ops.append((name,t,bytes(code)))
    for i in range(order):
        if i%2==0: op('POP BC',10,0xc1)
        op('LD L,'+('C' if i%2==0 else 'B'),4,0x69 if i%2==0 else 0x68)
        op('LD H,table-page',7,0x26,(TABLE>>8)+i*(2 if word_product else 1))
        if word_product:
            op('LD E,(HL)',7,0x5e)
            op('INC H',4,0x24)
            op('LD D,(HL)',7,0x56)
            op('ADD IX,DE',15,0xdd,0x19)
        else:
            # Fuse the table read and accumulation; saves 8 T per tap.
            op('ADD A,(HL)',7,0x86)
    chunks=[]; chunk=[]; cost=0
    for item in ops:
        if chunk and cost+item[1]>32:
            chunks.append(chunk); chunk=[]; cost=0
        chunk.append(item); cost+=item[1]
    if chunk: chunks.append(chunk)
    def pulse():
        # EXX 4, EX AF,AF' 4, kernel 32, EX AF,AF' 4, EXX 4 =48 T.
        a.emit(0xd9,0x08,0x82,0xcb,0x1b,0xcb,0x9b,0xed,0x59,0x08,0xd9)
    a.label('begin')
    if interleave: pulse()
    for chunk in chunks:
        for _,_,code in chunk: a.emit(*code)
        if interleave: pulse()
    a.label('end'); a.emit(0x00)
    return a.resolve(),a.labels,ops,chunks


def run_case(order,word_product,interleave,states,coefficients):
    from z80 import Z80Machine
    code,labels,ops,chunks=build_kernel(order,word_product,interleave)
    machine=Z80Machine(); machine.set_memory_block(0x8000,code)
    machine.set_memory_block(HISTORY,bytes(x&255 for x in states))
    values=np.arange(256,dtype=np.int64); values[128:]-=256
    for i,c in enumerate(coefficients):
        product=values*c
        if word_product:
            table=(product&255).astype('u1').tobytes()+((product>>8)&255).astype('u1').tobytes()
        else:
            table=((product>>7)&255).astype('u1').tobytes()
        machine.set_memory_block(TABLE+i*len(table),table)
    times=[]; bits=[]; budget=100000
    def output(port,value):
        assert port==0x10fe and value&15==0
        times.append(budget-machine.ticks_to_stop); bits.append((value>>4)&1)
    machine.set_output_callback(output)
    machine.pc=0x8000; machine.ticks_to_stop=budget
    machine.set_breakpoint(labels['begin'])
    machine.run(); assert machine.pc==labels['begin']
    machine.clear_breakpoint(labels['begin'])
    start=budget-machine.ticks_to_stop
    machine.set_breakpoint(labels['end'])
    machine.run(); assert machine.pc==labels['end']
    elapsed=budget-machine.ticks_to_stop-start
    wanted=(sum(x*c for x,c in zip(states,coefficients))&65535) if word_product else (
            sum((x*c)>>7 for x,c in zip(states,coefficients))&255)
    assert (machine.ix if word_product else machine.a)==wanted, 'lookup arithmetic or PDM damaged state'
    assert machine.sp==HISTORY+order
    lpc_t=sum(t for _,t,_ in ops)
    assert elapsed==lpc_t+(48*(len(chunks)+1) if interleave else 0),(elapsed,lpc_t)
    if interleave:
        expected,_=reference(bytes([PDM_VALUE]),cycles=1,oversample=len(chunks))
        assert bits==expected.tolist(), 'PDM recurrence changed'
        assert np.array_equal(np.diff(times),[48+sum(t for _,t,_ in c) for c in chunks])
    return dict(mac_tstates=lpc_t,instructions_verified=True,arithmetic_and_registers_exact=True,
                code_bytes=len(code),chunk_tstates=[sum(t for _,t,_ in c) for c in chunks],
                measured_kernel_tstates=elapsed,
                output_intervals_tstates=list(map(int,np.diff(times))),
                steady_decoder_span_tstates=lpc_t+48*len(chunks) if interleave else lpc_t,
                prepared_table_bytes=order*(512 if word_product else 256),
                state_bits=8,product_bits=16 if word_product else 8)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--lpc-source',type=Path,default=Path('C:/Work/LPC-sound-codec'))
    args=p.parse_args(); out=args.output
    if out.exists() and any(out.iterdir()): p.error('use a new output directory')
    out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(1977); results={}
    for order in (4,6,10):
        for word_product in (True,False):
            label=f'order{order}-product{16 if word_product else 8}'
            for interleave in (False,True):
                cases=[([0]*order,[127]*order),([-128]*order,[-128]*order),
                       ([127,-128]*(order//2),[-127,127]*(order//2))]
                cases += [(rng.integers(-128,128,order).tolist(),rng.integers(-128,128,order).tolist()) for _ in range(32)]
                for state,coeff in cases: result=run_case(order,word_product,interleave,state,coeff)
                code,labels,ops,chunks=build_kernel(order,word_product,interleave)
                key=label+('-interleaved' if interleave else '-mac-only')
                (out/(key+'.z80.gz')).write_bytes(gzip.compress(code,mtime=0))
                result.update(cases_verified=len(cases),labels=labels)
                if interleave:
                    span=result['steady_decoder_span_tstates']; intervals=result['output_intervals_tstates']
                    result.update(optimistic_pcm_rate_ceiling_hz=CPU_CLOCK/span,
                                  native_minimum_pdm_rate_hz=CPU_CLOCK/max(intervals),
                                  note='ceiling excludes all other decoder/player work; not an implemented audio mode')
                results[key]=result
    budgets=[]
    for rate in (8000,6000,4000):
        # Five PDM slots per 8 kHz sample, ten at 4 kHz; noninteger ratios
        # use an average budget and need an explicit schedule in a real player.
        for pdm in (40000,80000):
            budgets.append(dict(pcm_hz=rate,pdm_hz=pdm,cpu_tstates_per_sample=CPU_CLOCK/rate,
                pdm_kernel_only_tstates_per_sample=32*pdm/rate,
                optimistic_remaining_tstates_per_sample=(CPU_CLOCK-32*pdm)/rate,
                remaining_with_register_isolation_tstates_per_sample=(CPU_CLOCK-48*pdm)/rate))
    coefficient_source=ROOT/'audiobook-ay/ym2149-preview/lpc/lpc2-analysis.json'
    saved=json.loads(coefficient_source.read_bytes())
    source_files=[args.lpc_source/'arduino/Lpc2AvrDecoder/src/Lpc2AvrDecoder.cpp',
                  args.lpc_source/'arduino/Lpc2AvrDecoder/src/Lpc2AvrDecoder.h',
                  ROOT/'audiobook-ay/lpc-probe/lpc2-core.js.gz',coefficient_source,
                  ROOT/'audiobook-beeper/pcm-live-full/verification.json']
    fingerprints={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in source_files}
    report=dict(date='2026-10-02',complete=True,scope='feasibility microbenchmarks only',
        decoder_implemented=False,audio_quality_verified=False,fuse_verified=False,physical_hardware_tested=False,
        cpu_clock_hz=CPU_CLOCK,baseline_commit='4b2f8ea',source_files_sha256=fingerprints,
        source_pcm_hz=saved['meta']['sr'],source_lpc_order=saved['meta']['order'],
        host_reference_feedback_products_per_sample=10,host_reference_postfilter_products_per_sample=20,
        avr_feedback_products_per_sample=10,avr_internal_format='16-bit Q11 history/coefficient, 32-bit product',
        pdm_kernel_tstates=32,pdm_with_register_isolation_tstates=48,
        register_isolation_delta_tstates=16,tests=sum(r['cases_verified'] for r in results.values()),
        budgets=budgets,kernels=results,
        exclusions=['LPC bitstream and repeat parsing','LSF decoding/interpolation and LSF-to-LPC conversion',
            'excitation, gain, pitch and noise','coefficient table generation/loading/replacement',
            'history update and sample saturation','postfilter and deemphasis','loop and bank control',
            'ULA memory/IO contention','TR-DOS and disk latency'],
        conclusions=['Full existing LPC2 at 8 kHz with >=40 kHz PDM is not supported by these measured kernels.',
            'Optimized 10-tap byte-table MAC costs 230 T, 80 T less than the initial 310-T trial; five isolated PDM kernels add 240 T, totaling 470 T >443.3625 T before other work.',
            'The 16-bit-product table kernel costs 490 T before any PDM; original 16-bit state requires more work.',
            'Four-tap/4 kHz synthesis with prepared tables has arithmetic headroom; this does not verify a decoder or voice quality.',
            'Prepared per-frame tables would consume excessive storage; table reuse or another multiply method must also be solved.',
            'A PCM buffer cannot repair a sustained CPU deficit; the beeper still needs bounded output intervals.'],
        timing_reference='https://www.zilog.com/docs/z80/um0080.pdf',
        producer_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest())
    save(out/'report.json',report)
    listing=['; Z80 lookup LPC/PDM microbenchmark. Not a playable decoder.',
             '; Cycle counts exclude ULA/ROM/disk. Complete tables are assumed ready.',
             '; 16-bit tap: POP BC 10 once per pair; LD L,C/B 4; LD H,n 7;',
             '; LD E,(HL) 7; INC H 4; LD D,(HL) 7; ADD IX,DE 15 =49 T/tap average.',
             '; 8-bit tap: POP BC 10 once per pair; LD L,C/B 4; LD H,n 7;',
             '; ADD A,(HL) 7 =23 T/tap average, replacing the first 31-T version (-8 T/tap).',
             '; PDM isolation: EXX 4; EX AF,AF\' 4; ADD A,D 4; RR E 8;',
             '; RES 3,E 8; OUT(C),E 12; EX AF,AF\' 4; EXX 4 =48 T.',
             '; Chunked MAC operations occupy <=32 T between 48-T isolated PDM slots.']
    (out/'timing.txt.gz').write_bytes(gzip.compress(('\n'.join(listing)+'\n').encode(),mtime=0))
    (out/'producer.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes().replace(b'\r\n',b'\n'),mtime=0))
    print(json.dumps({'tests':report['tests'],'kernels':results,'budgets':budgets}),flush=True)


if __name__=='__main__': main()
