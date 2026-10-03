"""Direct packet pointers with a closed feedback state set and split tables."""
import ast,gzip,hashlib,json,struct,subprocess,sys
from pathlib import Path
import numpy as np
from feedback_player import loading_screen
from ima_codec import decode,STEPS,INDEX,require_unclipped
from pcm_player import TrdFile,basic_line,calculate_file_start,place_files
from probe_feedback_packets import integral_table
from verify_pcm import save

HERE=Path(__file__).resolve().parent
MAX_PACKED_BYTES=93440
HOLDS=[36,28,28,31,24,26,22,20,22,26,22,30,31,27,34,16]
MEASURED_MODEL=dict(holds=[288,231,225,248,192,218,204,170,215,226,177,240,248,216,291,156],
                    beta=.5,extent=.5,weight_units='eighth T-state; rounded ordinary Fuse means',
                    calibration='experiments/ima-direct/output-times.u32.gz')


def layout(packed,model=None,hot_indices=None):
    model=model or dict(holds=HOLDS,beta=.5,extent=1.)
    words,nxt,_=integral_table(64,2,holds=model['holds'],beta=model['beta'],extent=model['extent'])
    reachable={16}
    while True:
        expanded=reachable|set(map(int,nxt[:,sorted(reachable)].ravel()))
        if expanded==reachable:break
        reachable=expanded
    states=sorted(reachable);assert len(states)*6<=128
    first_patterns=sorted(set(map(int,(words[:,states]>>8).ravel())))
    second_patterns=sorted(set(map(int,(words[:,states]&255).ravel())))
    first={p:0x8400+i*41 for i,p in enumerate(first_patterns)}
    base=0x8400+len(first)*41
    second={p:base+i*64 for i,p in enumerate(second_patterns)}
    pointers=(base+len(second)*64+255)&~255
    fixed=pointers+256;extra=fixed+1024
    reserve=(extra+17*64+255)//256*256-0x8000
    assert reserve<=14336,'preserve the complete delivered 93440-byte source'
    # Leave spare resident padding rather than changing this experiment's source.
    reserve=14336
    pages=[fixed+(i-28)*256 if 28<=i<32 else 0x4000+i*256 for i in range(64)]
    _,indices=decode(packed)
    counts=np.bincount(np.r_[0,indices[:-1]],minlength=89)
    hot=(sorted(range(89),key=lambda i:(-int(counts[i]),i))[:25]
         if hot_indices is None else list(hot_indices))
    assert len(hot)==25 and len(set(hot))==25 and all(0<=i<89 for i in hot)
    slots=[fixed+i*256+j for i in range(4) for j in (128,192)]+[extra+i*64 for i in range(17)]
    cold_slots=[p+j for p in pages if p<0x8000 for j in (128,192)]
    rows={i:a for i,a in zip(hot,slots)}
    for i,a in zip([i for i in range(89) if i not in rows],cold_slots):rows[i]=a
    assert 256<=len(packed)<=MAX_PACKED_BYTES and len(packed)%256==0
    sections=[];remaining=len(packed)
    for bank,capacity in [(b,16384) for b in (0,4,6,1,3)]+[(7,9472),(2,2048)]:
        size=min(remaining,capacity)
        if size:sections.append(dict(bank=bank,address=0x10000-size,bytes=size,sectors=size//256))
        remaining-=size
    return words,nxt,states,first,second,pointers,pages,rows,sections,hot,float(counts[hot].sum()/counts.sum())


def build_disk(packed,work,model=None,hot_indices=None,idle_pairs=0,idle_pad=0):
    work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    words,nxt,states,first,second,pointers,pages,rows,sections,hot,coverage=layout(packed,model,hot_indices)
    assert len(packed)==sum(s['bytes'] for s in sections)
    pcm,indices=decode(packed);assert (pcm[-1],indices[-1])==(0,0)
    memory=bytearray(65536)
    for value in range(64):
        for sid,state in enumerate(states):
            word=int(words[value,state]);address=pages[value]+sid*6
            memory[address:address+6]=struct.pack('<HHBB',first[word>>8],second[word&255],states.index(int(nxt[value,state]))*6,16)
    for index in range(89):
        step=STEPS[index]
        for code in range(16):
            delta=(step>>3)+(step if code&4 else 0)+(step>>1 if code&2 else 0)+(step>>2 if code&1 else 0)
            if code&8:delta=-delta
            address=rows[index]+code*4
            memory[address:address+4]=struct.pack('<HH',delta&65535,rows[max(0,min(88,index+INDEX[code&7]))])
    memory[pointers:pointers+256]=bytes(pages[i>>2]>>8 for i in range(256))
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),basic_line(30,b'\xf9 \xc0 \xb0 "32768"')])
    boot=TrdFile('boot','B',basic,autostart_line=10)
    track,sector=calculate_file_start([boot,TrdFile('PLAYER','C',bytes(23296),start=0x8000)])
    lower=track*16+sector;upper=lower+28;pos=upper+32
    for s in sections:s['sector']=pos;pos+=s['sectors']
    constants=dict(first_base=0x8400,pcm_high=pointers,resident_reserve=14336,decoder_seed=rows[0],
                   initial_feedback_offset=states.index(16)*6,lower_disk=lower//16*256+lower%16,upper_disk=upper//16*256+upper%16,
                   final_section_index=len(sections)-1)
    assert 0<=idle_pairs<=1530 and idle_pad>=0 and (idle_pairs or idle_pad==0)
    loads=next((b for b in range(4) if idle_pad>=7*b and (idle_pad-7*b)%4==0),None)
    assert loads is not None,'padding must be a nonnegative sum of 4-T NOP and 7-T LD A,n'
    constants.update(loop_idle_pairs=idle_pairs,idle_pad_loads=loads,idle_pad_nops=(idle_pad-7*loads)//4)
    for i in range(6):constants[f'idle_count_{i}']=min(255,max(0,idle_pairs-255*i))
    for i in range(256):constants.update({f'first_address_{i}':first.get(i,-1),f'second_address_{i}':second.get(i,-1)})
    for i in range(7):
        s=sections[i] if i<len(sections) else dict(sector=0,address=0xc000,sectors=0)
        successor=(i+1)%len(sections);nxt_section=sections[successor]
        constants.update({f'disk_{i}':s['sector']//16*256+s['sector']%16,f'address_{i}':s['address'],f'sectors_{i}':s['sectors'],
                          f'next_bank_{i}':nxt_section['bank'],f'next_address_{i}':nxt_section['address'],f'next_tail_{i}':f'bank_tail_{successor}'})
    (work/'config.inc').write_text(''.join(f'{k}: EQU {v}\n' for k,v in constants.items()))
    for name,data in [('pcm-high',memory[pointers:pointers+256]),('fixed-pages',memory[pointers+256:pointers+1280]),
                      ('decoder-extra',memory[pointers+1280:pointers+1280+1088]),
                      ('bank5-lower',memory[0x4000:0x5c00]),('bank5-upper',memory[0x6000:0x8000]),
                      ('screen',loading_screen(len(packed)*2,'IMA / DIRECT PDM'))]:
        (work/(name+'.bin')).write_bytes(data)
    (work/'player.asm').write_bytes((HERE/'direct-player.asm').read_bytes())
    run=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=player.bin','--lstfile=player.lst','-s','.*','player.asm'],cwd=work,capture_output=True,text=True)
    (work/'assembler.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    labels=next(ast.literal_eval(s) for s in run.stdout.splitlines() if s.startswith('{'))
    blob=(work/'player.bin').read_bytes();assert len(blob)==23296
    files=[boot,TrdFile('PLAYER','C',blob,start=0x8000),TrdFile('LOWER','C',bytes(memory[0x4000:0x5c00]),start=0x4000),TrdFile('UPPER','C',bytes(memory[0x6000:0x8000]),start=0x6000)]
    offset=0
    for i,s in enumerate(sections):
        files.append(TrdFile(f'IMA{i}','C',packed[offset:offset+s['bytes']],start=s['address']));offset+=s['bytes']
    disk,directory,capacity=place_files(files,'IMADIR')
    meta=dict(direct=True,model=model or dict(holds=HOLDS,beta=.5,extent=1.),origin=0x8000,player_labels=labels,sections=sections,directory=directory,capacity=capacity,
              first_addresses=list(first.values()),second_addresses=list(second.values()),
              first_patterns=len(first),second_patterns=len(second),resident_reserve=14336,
              loop_idle_pairs=idle_pairs,loop_idle_pad_tstates=idle_pad,
              outputs_per_cycle=len(packed)*32+idle_pairs*2,
              decoder_rows=[rows[i] for i in range(89)],hot_indices=hot,hot_coverage=coverage,
              feedback_states=states,packet_pages=pages,pcm_samples=len(packed)*2,packed_bytes=len(packed),
              ordinary_holds_tstates=HOLDS,ordinary_tstates=sum(HOLDS),page_extra_tstates=14,bank_extra_tstates=140,
              initial_predictor=0,initial_index=0,initial_feedback=16,paging_base=24,preload_table_sectors=60,
              record_stop_addresses=[a+2 for a in first.values()],repeat=True,
              mutable_addresses=[labels['bank_jump']+1,labels['bank_jump']+2],
              source_sample_rate_hz=8000,cpu_clock_hz=3546900,saturation_guard=require_unclipped(packed),
              packed_sha256=hashlib.sha256(packed).hexdigest(),binary_sha256=hashlib.sha256(blob).hexdigest(),
              assembly=dict(instruction_bytes_emitted_by_python=False,assembler='pyz80 1.3.0'),
              memory=dict(total_ram_bytes=131072,adpcm_bytes=len(packed),shadow_screen_bytes=6912,bank5_tables_and_workspace_bytes=16384,bank2_resident_bytes=14336,
                          unused_audio_capacity_bytes=MAX_PACKED_BYTES-len(packed),pcm_buffer_bytes=0,pdm_buffer_bytes=0))
    return disk,meta


def prepare(out,model=None):
    import shutil
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    source=HERE/'experiments/ima-packet'
    packed=gzip.decompress((source/'soundtrack.ima.gz').read_bytes())
    disk,meta=build_disk(packed,out/'assembly',model)
    for name in ('source-preview.wav','soundtrack.ima.gz'):shutil.copy2(source/name,out/name)
    (out/'audiobook-preview.trd').write_bytes(disk);save(out/'player.json',meta)
    print(json.dumps({k:meta[k] for k in ('first_patterns','second_patterns','hot_coverage','ordinary_tstates','binary_sha256')}),flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--measured-model',action='store_true')
    a=p.parse_args();prepare(a.output,MEASURED_MODEL if a.measured_model else None)
