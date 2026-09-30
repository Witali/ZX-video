"""Exact frame and copy-bridge CPU checks for borrowed literal suffixes.

Host supplies frame fields; no claim about real disk/IRQ/ULA cadence. Compare
unchanged frame data with the saved baseline. Actual playback is tested in Fuse.
"""
import argparse
from bisect import bisect_right
from collections import Counter
import gzip
import json
from pathlib import Path
import struct
import numpy as np
from benchmark_direct_motion_target import (Harness, OPTIONS, Reader, frames, install_hl_masks,
    read_header, read_packet, serialized_masks, unpack, unpack_audio, unpack_bulk, unpack_cache)
from benchmark_context_huffman import word
from benchmark_compact_screen import NativeCPU, STACK, STOP
from build_fap3_trd import sha
from profile_frame_hotspots import instrument
from frame_output_pipeline import display_screen
from row_dictionary_video import reference_tables
import cached_huffman_lookahead as lookahead
import compact_cursor
import inline_huffman_patches as inline
import uncontended_frame as memory
import pipelined_frame_z80 as page
import borrowed_literals as machine
from test_fap3_disk import install


def install_frame(h, meta):
    c=h.cpu;regions,lab,listing=machine.generate(meta,h.recon,h.w)
    fixed=dict(h.instructions)
    for at,blob in regions:
        install(c,at,blob)
        for pc in list(fixed):
            if at<=pc<at+len(blob):del fixed[pc]
    paging,_,prows=page.build_video(h.draw,{},dict(elapsed_fields=0x6000),irq_safe_paging=True)
    for at,blob in paging:
        if at==page.PAGE:install(c,at,blob)
    for row in listing+[r for r in prows if page.PAGE<=r['address']<page.STATE]:
        fixed[row['address']]=dict(row,stage='borrowed_literals' if row['phase']!='paging' else 'paging')
    c.state_regions=list(c.state_regions)+[(lab['borrowed_page'],lab['fixed_end']),
        (page.SHADOW,page.SHADOW+1),(page.REQUEST_OPERAND,page.REQUEST_OPERAND+1)]
    at=meta['inline_huffman_patches']['redirect_address']
    install(c,at,b'\xc3'+lab['patch'].to_bytes(2,'little'))
    fixed[at]=dict(address=at,instruction='JP borrowed patch bridge',tstates=10,phase='reconstruct',stage='patch')
    pcs=[pc for pc,row in fixed.items() if row['instruction']=='CALL attribute_pass']
    assert len(pcs)==1
    install(c,pcs[0],b'\xcd'+lab['attributes'].to_bytes(2,'little'))
    h.instructions.clear();h.instructions.update(fixed)
    old=h.w['run'];h.w['run']=lab['prepare']
    return lab,old


def run_frame(h,lab,group,native,expected,index,encoded_metadata,cache_map,borrow):
    _,flags,bits,vectors,bitmap,attrs,encoded,literals=group
    c=h.cpu;c.guarding=False
    target=7 if index%2==0 else 5;current=0x16 if target==7 else 0x1e
    assert c.port_7ffd==current
    c.target_bank=target; c.write8(page.SHADOW,current)
    install(c,0xba40,cache_map);install(c,memory.INPUT,encoded_metadata)
    c.input_end=memory.INPUT+len(encoded_metadata);c.set_hl(memory.INPUT)
    c.port_7ffd=(current&~7)|7
    metadata=h.execute(h.metadata_entry)
    assert c.hl()==c.input_end and metadata['total_tstates']==h.metadata_formula(encoded_metadata)
    assert bytes(c.read8(memory.MASKS+i) for i in range(480))==bitmap+attrs
    c.guarding=False
    c.port_7ffd=current
    data=encoded+b'\0'+literals+b'\0'
    for at,blob in ((memory.VECTORS,vectors),(memory.MAP,native),(memory.INPUT,data)):install(c,at,blob)
    c.input_end=memory.INPUT+len(data)
    word(c,h.w['literal_pointer'],memory.INPUT+len(encoded)+1)
    c.write8(h.w['cache_flag'],int(bool(flags&128)));c.write8(h.w['raw_attribute_flag'],int(bool(flags&64)))
    slot=(0,1,3)[index%3];pointer=0xc123
    c.banks[slot][:]=b'\x97'*16384;c.banks[slot][pointer-0xc000:pointer-0xc000+len(literals)]=literals
    before=bytes(c.banks[slot]);c.write8(lab['borrowed_page'],0x10|slot if borrow else 0)
    word(c,lab['borrowed_pointer'],pointer)
    result=h.execute(h.w['run'])
    assert bytes(c.read8(memory.FRAME+i) for i in range(3840))==expected,('compact',index)
    h.expected_screens[target]=display_screen(expected,black_borders=True)
    assert all(bytes(c.banks[b][:6912])==screen for b,screen in h.expected_screens.items()),('screens',index)
    assert (word(c,h.recon['source'])-memory.INPUT)*8+(c.read8(h.recon['bit_page'])&7)==bits
    wanted=pointer if borrow else memory.INPUT+len(encoded)+1
    assert word(c,h.recon['literal_source'])==wanted+len(literals),('literal cursor',index)
    assert bytes(c.banks[slot])==before,('borrowed input changed',index)
    for at,blob in ((memory.VECTORS,vectors),(memory.MAP,native),(memory.INPUT,data),(memory.MASKS,bitmap+attrs),(0xba40,cache_map)):
        assert bytes(c.read8(at+i) for i in range(len(blob)))==blob,('input changed',index,hex(at))
    assert c.port_7ffd==current^8
    assert bytes(c.banks[5][0x1b00:0x2400])==b'\xa5'*0x900
    return result['total_tstates']+metadata['total_tstates']


def copy_cases(meta,video):
    # Reassemble the original fixed bridge (the same verified regions as
    # the disk) and the new helper; no host copy substitutes native LDI.
    import slot_queue_z80
    regions,_,oldrows=slot_queue_z80.build(meta['decoder_labels'],meta['producer_labels'],len(meta['blocks']),
        partial_consumption=True,demand_decode=True)
    bridge=regions[0]
    patch=meta['borrowed_literals'];lab=patch['labels'];rows={r['address']:r for r in oldrows}
    rows.update({r['address']:r for r in patch['listing']})
    paging,_,prows=page.build_video(dict(saved_page=0x6000,screen_base=0x6001),{},dict(elapsed_fields=0x6002),irq_safe_paging=True)
    rows.update({r['address']:r for r in prows})
    q=meta['queue_labels'];cases=[];total_before=total_after=bytes_saved=0
    def run(entry,payload,source,region,destination,count,full,remaining,completed):
        c=NativeCPU(b'',b'');c.port_7ffd=0x17
        install(c,*bridge)
        for region_desc in patch['regions']:install(c,region_desc['address'],bytes.fromhex(region_desc['code_hex']))
        for at,blob in paging:
            if at==page.PAGE:install(c,at,blob)
        c.write8(page.SHADOW,0x17)
        if entry==lab['copy']:c.write8(lab['borrowed_page'],0x13)  # Previous packet must not leak ownership.
        slot=(0,1,3)[region];c.banks[slot][:]=b'\x3e'*16384
        c.banks[slot][source-0xc000:source-0xc000+len(payload)]=payload
        bank_before=bytes(c.banks[slot]);install(c,memory.INPUT,b'\xa5'*4704)
        word(c,machine.LENGTH,full);word(c,q['slot_left'],remaining);c.write8(q['count'],completed)
        c.a=region;c.set_hl(source);c.set_de(destination);c.set_bc(count)
        c.sp=STACK;c.push(STOP);c.pc=entry;hist=Counter();writes=0
        while c.pc!=STOP:
            pc,before=c.pc,c.tstates; row=rows[pc]
            if row['instruction']=='LDI':writes+=1
            c.step();ticks=c.tstates-before
            allowed=row['tstates'] if isinstance(row['tstates'],list) else [row['tstates']]
            assert ticks in allowed,('timing',pc,ticks,row)
            hist[pc,ticks]+=1
        assert c.de()==destination+count and c.sp==STACK and c.port_7ffd==0x17
        assert bytes(c.banks[slot])==bank_before
        flag=c.read8(lab['borrowed_page']);prefix=280+struct.unpack_from('<H',payload,1)[0]+struct.unpack_from('<H',payload,3)[0] if flag else count
        actual=bytes(c.read8(destination+i) for i in range(count))
        if flag:
            assert actual[:prefix+2]==payload[:prefix+2] and actual[prefix+2:]==b'\xa5'*(count-prefix-2)
            assert word(c,lab['borrowed_pointer'])==source+prefix and flag==0x10|slot
        else:assert actual==payload[:count]
        return dict(tstates=c.tstates,copy_bytes=writes,borrowed=bool(flag),histogram=[dict(pc=pc,tstates=t,count=n) for (pc,t),n in sorted(hist.items())])
    entries=machine.validate_video(video)
    blocks=meta['blocks'];starts=[b['raw_start'] for b in blocks]
    ends=[b['raw_end'] for b in blocks]
    assert starts and starts[0]==0 and ends[-1]==len(video)
    assert all(0<end-start<=15872 for start,end in zip(starts,ends))
    assert starts[1:]==ends[:-1], 'non-contiguous decoded block metadata'
    for i,item in enumerate(entries):
        cursor=item['offset']; length_end=cursor+2
        while cursor<length_end:
            block=bisect_right(starts,cursor)-1;block_end=ends[block];n=min(length_end,block_end)-cursor
            args=(video[cursor:cursor+n],0xc000+cursor-starts[block],block%3,
                  machine.LENGTH+cursor-item['offset'],n,item['bytes'],block_end-cursor-n,1)
            before=run(q['bridge']['copy'],*args);after=run(lab['copy'],*args)
            total_before+=before['tstates'];total_after+=after['tstates']
            assert not after['borrowed']
            cases.append(dict(frame=i,field='length',bytes=n,baseline=before,candidate=after))
            cursor+=n
        start=item['offset']+2;end=start+item['bytes'];cursor=start;first=True
        while cursor<end:
            block=bisect_right(starts,cursor)-1;block_end=ends[block];n=min(end,block_end)-cursor
            dest=memory.INPUT+cursor-start;payload=video[cursor:cursor+n];source=0xc000+cursor-starts[block]
            args=payload,source,block%3,dest,n,item['bytes'],block_end-cursor-n,1
            before=run(q['bridge']['copy'],*args);after=run(lab['copy'],*args)
            total_before+=before['tstates'];total_after+=after['tstates'];bytes_saved+=before['copy_bytes']-after['copy_bytes']
            cases.append(dict(frame=i,field='payload',bytes=n,baseline=before,candidate=after))
            cursor+=n;first=False
    # Explicit active-prefix and last-slot cases, short suffix guards, all banks.
    edges=[]
    for region in range(3):
        for length in (288,289,290,291,600):
            payload=bytearray((i*31)&255 for i in range(length));payload[:5]=struct.pack('<BHH',0,8,0)
            for remaining,completed in ((0,0),(0,1),(1,1)):
                result=run(lab['copy'],bytes(payload),0xc0f9,region,memory.INPUT,length,length,remaining,completed)
                assert result['borrowed']==(length>290 and (remaining>0 or completed==0))
                edges.append(dict(region=region,length=length,remaining=remaining,completed=completed,**result))
    return dict(complete=True,scope='Real copy instructions with fully available blocks; fixed snapshot of slot ownership, no disk/IRQ/ULA.',
        baseline_tstates=total_before,tstates=total_after,delta_tstates=total_after-total_before,
        copied_bytes_saved=bytes_saved,borrowed_packets=sum(c['candidate']['borrowed'] for c in cases),
        cases=cases,edges=edges)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('raw','video','states','metadata','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();raw=a.raw.read_bytes();video=a.video.read_bytes();m=json.loads(a.metadata.read_bytes())
    old=json.loads(gzip.decompress(Path('toolkit/row_fragment_evidence/slack16-cpu.json.gz').read_bytes()))
    assert sha(raw)==old['raw_sha256']==m['raw_sha256']
    with np.load(a.states,allow_pickle=False) as saved:states=saved['states']
    cells=unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
    tables,mapping,packets=frames(cells);masks=serialized_masks(cells)
    r=Reader(raw);_,_,count,_,_=read_header(r,magic=b'FAP3');details=[read_packet(r,stored_guards=False)[1] for _ in range(count)];r.end()
    h=Harness(tables,mapping,static_cache_borders=True,carry_huffman=True,register_fragments=True,
        cached_huffman_byte=True,metadata_mode='compiled',**OPTIONS)
    install_hl_masks(h);h.cpu.guarding=False
    memory.install_stage(h);lookahead.install_frame(h)
    generated=inline.install_stage(h,tables,mapping);compact_cursor.install_stage(h)
    install(h.cpu,0x9e00,bytes.fromhex(m['row_dictionary']['tables_hex']))
    lab,_=install_frame(h,m);hist,stages,_,_=instrument(h,generated)
    cpu_copy=copy_cases(m,video)
    borrowing={r['frame'] for r in cpu_copy['cases'] if r['candidate']['borrowed']}
    output=[];prior=Counter()
    with reference_tables(m['row_dictionary']):
        for i,(group,native) in enumerate(packets):
            t=run_frame(h,lab,group,native,states[i].tobytes(),i,masks[i],details[i]['cache'],i in borrowing)
            delta=stages-prior;prior=stages.copy();assert sum(delta.values())==t
            output.append(dict(frame=i,borrowed=i in borrowing,tstates=t,baseline_tstates=old['frames'][i]['tstates'],stages=dict(delta)))
            if i%64==63:print(f'{i+1} complete compact/both-screen/cursor/input checks',flush=True)
    total=sum(r['tstates'] for r in output)
    report=dict(complete=True,release=False,scope=__doc__,frames=output,frame_tstates=total,
        baseline_frame_tstates=old['tstates'],frame_delta_tstates=total-old['tstates'],copy=cpu_copy,
        estimated_component_net_delta_tstates=total-old['tstates']+cpu_copy['delta_tstates'],
        stages=dict(stages),all_instruction_timings_verified=True,full_compact_and_both_native_exact=True,
        raw_sha256=sha(raw),video_sha256=sha(video),metadata_sha256=sha(a.metadata.read_bytes()))
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('frames','copy','stages','scope')}),flush=True)


if __name__=='__main__':main()
