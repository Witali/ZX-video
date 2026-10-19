"""Execute a bounded high-byte-root/full-precision selector CPU prototype.

Only new evidence files are produced. This standalone component does not
modify or boot the player, change its clock, or claim fixed-RAM integration.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import time

import numpy as np
from z80 import Z80Machine

HERE=Path(__file__).resolve().parent


def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


def runs(values):
    starts=np.r_[0,np.flatnonzero(values[1:]!=values[:-1])+1]
    ends=np.r_[starts[1:]-1,len(values)-1]
    return [(int(end),int(values[start])) for start,end in zip(starts,ends)]


def padding(tstates):
    for reads in range(5):
        for loads in range(10):
            left=tstates-9*reads-7*loads
            if left>=0 and left%4==0:
                return ' LD A,R\n'*reads+' LD A,0\n'*loads+' NOP\n'*(left//4)
    raise ValueError(('unrepresentable safe padding',tstates))


def assemble(folder,source):
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'selector.asm').write_text(source,encoding='utf-8',newline='\n')
    result=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=selector.bin',
        '--lstfile=selector.lst','-s','.*','selector.asm'],cwd=folder,capture_output=True,text=True)
    (folder/'assembler.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    labels=next(ast.literal_eval(line) for line in result.stdout.splitlines() if line.startswith('{'))
    return (folder/'selector.bin').read_bytes(),labels


def component(folder,seed,words,nexts,addresses):
    packed=(words.astype(np.uint32)<<8)|nexts
    records=sorted(map(int,np.unique(packed)));ids={value:index for index,value in enumerate(records)}
    record_index=np.array([ids[int(value)] for value in packed],dtype=np.uint16)
    groups=[runs(record_index[high*256:(high+1)*256]) for high in range(256)]
    signatures=sorted(set(tuple(group) for group in groups))
    names={signature:'group_'+str(index) for index,signature in enumerate(signatures)}
    header='''; Full-input model-B selector component, standalone CPU evidence only.
; Enter after SECOND dispatch, where old IY is dead; main A/F/HL scratch.
; IX retains all16 predictor bits. BC remains the output port, D16/E state.
; E is newly encoded as0x40+2*raw_state, selecting two parallel root pages.
; Alternate decoder/source registers and AF' are untouched. No CALL/PUSH.
; The component is flat native RAM: real paging/ULA/boot are not implemented.
 ORG 0x8000
selector:
 LD A,IXH
 LD L,A
 LD H,E
 LD A,(HL)
 INC H
 LD H,(HL)
 LD L,A
 JP (HL)
selector_root_end:
 DS 0x8100-$
handlers:
'''
    pieces=[header];leaf_count=0
    def tree(group,name,depth,variable):
        nonlocal leaf_count
        pieces.append(name+':\n')
        if len(group)==1:
            leaf_count+=1;record=group[0][1]
            # Root42, optional IXL8+17 per comparison, fetch44, continuation10.
            intrinsic=96+(8+17*depth if variable else 0)
            pieces.append(padding(155-intrinsic))
            pieces.append(f' LD SP,{0xB000+record*6}\n POP HL\n POP IY\n POP DE\n JP complete\n')
            return
        middle=len(group)//2;boundary=group[middle-1][0]+1
        pieces.append(f' CP {boundary}\n JP C,{name}_left\n')
        tree(group[middle:],name+'_right',depth+1,True)
        tree(group[:middle],name+'_left',depth+1,True)
    for signature in signatures:
        name=names[signature]
        if len(signature)==1:tree(list(signature),name,0,False)
        else:
            pieces.append(name+':\n LD A,IXL\n')
            tree(list(signature),name+'_search',0,True)
    pieces.append('handlers_end:\ncomplete:\n NOP\n ASSERT $ < 0xB000\n')
    blob,labels=assemble(folder,''.join(pieces))
    roots_lo=bytes(labels[names[tuple(group)]]&255 for group in groups)
    roots_hi=bytes(labels[names[tuple(group)]]>>8 for group in groups)
    dictionary=b''.join(struct.pack('<HHBB',addresses['first'][value>>16],
        addresses['second'][(value>>8)&255],0x40+2*(value&255),16) for value in records)
    assert len(dictionary)<=4096
    (folder/'roots.bin').write_bytes(roots_lo+roots_hi)
    (folder/'records.bin').write_bytes(dictionary)
    # Independently reproduce each input's reference word/successor using
    # interval endpoints. No native code result is reused by this host check.
    reconstructed=np.empty(65536,dtype=np.uint32)
    for high,group in enumerate(groups):
        ends=np.array([end for end,_ in group]);keys=np.array([record for _,record in group])
        selected=keys[np.searchsorted(ends,np.arange(256),side='left')]
        reconstructed[high*256:(high+1)*256]=np.asarray(records,dtype=np.uint32)[selected]
    np.testing.assert_array_equal(reconstructed,packed)
    tests=set((0,65535,32768+37,32768+38))
    for high,group in enumerate(groups):
        tests.update((high*256,high*256+255))
        for end,_ in group[:-1]:tests.update((high*256+end,high*256+end+1))
    m=Z80Machine();m.memory[0x8000:0x8000+len(blob)]=blob
    page=0x4000+seed*512;m.memory[page:page+512]=roots_lo+roots_hi
    m.memory[0xB000:0xB000+len(dictionary)]=dictionary
    before=bytes(m.memory);budget=10000;native=[]
    for number,unsigned in enumerate(sorted(tests)):
        for key,value in dict(ix=unsigned,af=0x1234,bc=0x00FE,de=0x1000|((page>>8)&255),
            hl=0x4321,iy=0x8765,sp=0x7777,alt_af=0xA5A5,
            alt_bc=0x2468,alt_de=0xC123,alt_hl=0xABCD).items():setattr(m,key,value)
        m.iff1=False;m.iff2=bool(number&1);m.r=(0,127,128,255)[number%4]
        m.pc=labels['selector'];m.set_breakpoint(labels['complete']);m.ticks_to_stop=budget
        while m.pc!=labels['complete']:
            event=m.run();assert not event&m._TICKS_LIMIT_HIT,'Native selector timeout'
        elapsed=budget-m.ticks_to_stop;value=int(packed[unsigned]);record=ids[value]
        expected=(addresses['first'][value>>16],addresses['second'][(value>>8)&255],
                  0x1000|0x40|2*(value&255),0xB000+record*6+6)
        assert (m.hl,m.iy,m.de,m.sp)==expected,(seed,unsigned,expected,m.hl,m.iy,m.de,m.sp)
        assert elapsed==155,(seed,unsigned,elapsed)
        assert (m.ix,m.bc,m.alt_af,m.alt_bc,m.alt_de,m.alt_hl)==(unsigned,0x00FE,0xA5A5,0x2468,0xC123,0xABCD)
        native.append(dict(unsigned_pcm16=unsigned,tstates=elapsed,word=value>>8,successor=value&255))
    assert bytes(m.memory)==before,'Selector must not write RAM or use a call stack'
    report=dict(seed=seed,root_page=page>>8,root_bytes=512,local_records=len(records),
        local_record_bytes=len(dictionary),handler_bytes=labels['handlers_end']-labels['handlers'],
        unique_group_signatures=len(signatures),inline_leaves=leaf_count,
        max_ranges_per_high_byte=max(map(len,groups)),range_histogram=dict(Counter(map(len,groups))),
        native_cases=len(native),native_uniform_tstates=155,
        lower_bit_witness=[row for row in native if row['unsigned_pcm16'] in (32768+37,32768+38)],
        every65536_host_input_exact=True,native_boundary_highbyte_and_worstcase_exact=True,
        predictor_port_alternate_registers_and_memory_guards=True,
        IY_output_only_after_old_SECOND_dispatch=True,SP_only_POP_no_CALL_PUSH=True,
        native_vectors=native)
    save(folder/'report.json',report)
    return report,groups,records


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
    cell_path=HERE.parent/'sdm16-architecture/model-b-all-pcm16-cells.npz'
    address_path=HERE.parent/'sdm16-patterns/high-only/addresses.json'
    cells=np.load(cell_path);words=cells['words'];nexts=cells['successors']
    addresses={key:{int(a):int(b) for a,b in value.items()} for key,value in json.loads(address_path.read_bytes()).items() if key in ('first','second')}
    reached={16};previous=None
    while reached!=previous:
        previous=reached.copy();reached|=set(map(int,nexts[:,sorted(reached)].ravel()))
    summaries=[];all_host=0;full_runs=[];word_only_runs=[]
    for seed in range(32):
        packed=(words[:,seed].astype(np.uint32)<<8)|nexts[:,seed]
        groups=[runs(packed[high*256:(high+1)*256]) for high in range(256)]
        rebuilt=np.empty(65536,dtype=np.uint32)
        for high,group in enumerate(groups):
            lower=0
            for end,value in group:rebuilt[high*256+lower:high*256+end+1]=value;lower=end+1
        np.testing.assert_array_equal(rebuilt,packed);all_host+=65536
        if seed in reached:
            full_runs.extend(map(len,groups))
            word_only_runs.extend(len(runs(words[high*256:(high+1)*256,seed])) for high in range(256))
            report,_,_=component(out/f'seed-{seed:02d}',seed,words[:,seed],nexts[:,seed],addresses)
            summaries.append({key:value for key,value in report.items() if key!='native_vectors'})
    report=dict(complete=True,date='2026-10-19',scope='Standalone selector CPU and source-independent table proof only; no player/clock/quality promotion',
        model_b_cells_sha256=hashlib.sha256(cell_path.read_bytes()).hexdigest(),
        high_only_pattern_addresses_sha256=hashlib.sha256(address_path.read_bytes()).hexdigest(),
        all32_seed_host_cells_verified=all_host,reachable_states=sorted(reached),
        components=summaries,native_cases=sum(x['native_cases'] for x in summaries),
        full_range_histogram=dict(Counter(full_runs)),word_only_range_histogram=dict(Counter(word_only_runs)),
        full_max_ranges=max(full_runs),word_only_max_ranges=max(word_only_runs),
        query_root_tstates=42,binary_compare_tstates=17,load_low_predictor_tstates=8,
        packet_fetch_tstates=44,continuation_JP_tstates=10,
        constant_path_before_padding_tstates=96,worst_3_compare_path_tstates=155,
        all_native_paths_padded_tstates=155,
        historical_lookup_and_POP_tstates=70,historical_JP_IY_tstates_excluded=8,
        source_period_if_naively_substituted_without_Pentagon_pacing_tstates=508,
        fixed_layout_fit=False,integrated_live_register_and_paging_timing_verified=False,
        stored_component_root_bytes=sum(x['root_bytes'] for x in summaries),
        stored_component_handler_bytes=sum(x['handler_bytes'] for x in summaries),
        stored_component_record_bytes=sum(x['local_record_bytes'] for x in summaries),
        host_elapsed_seconds=time.perf_counter()-started,
        decision='Reject this literal high8-root/binary-handler/current-address-ABI implementation as an unchanged-clock player; retain exact native and memory constraints for the compact successor mechanism')
    save(out/'report.json',report)
    manifest=[dict(path=p.relative_to(out).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
    save(out/'manifest.json',dict(files=len(manifest),artifacts=manifest))
    print(json.dumps(dict(complete=True,host_cells=all_host,native_cases=report['native_cases'],artifacts=len(manifest),elapsed=report['host_elapsed_seconds'])))


if __name__=='__main__':main()
