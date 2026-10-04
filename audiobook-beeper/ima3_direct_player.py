"""Direct resident three-bit IMA; the PC reference remains ordinary IMA bytes."""
import ast,hashlib,struct,subprocess,sys
from pathlib import Path
import numpy as np
from feedback_player import loading_screen
from ima_codec import decode,STEPS,INDEX,require_unclipped
from pcm_player import TrdFile,basic_line,calculate_file_start,place_files
from probe_feedback_packets import integral_table

HERE=Path(__file__).resolve().parent
LEGACY_BANK2_RESERVE=14336
HOLDS=[36,28,28,31,24,26,22,20,22,26,22,30,31,27,34,16]
MEASURED_MODEL=dict(holds=[288,224,224,248,196,265,272,183,220,176,216,184,142,247,164,308],
                    beta=.5,extent=.5,weight_units='eighth T-state; rounded ordinary Fuse means',
                    calibration='experiments/ima-3bit-direct/pilot/output-times.u32.gz',
                    pcm_bins=128,q_clip=[3,12],level_bounds=[4,123])


def pack3(packed):
    b=np.frombuffer(packed,'u1')
    if not len(b) or np.any(b&0x11) or len(b)%4:
        raise ValueError('Requires complete eight-sample groups from the even IMA subset')
    codes=np.empty(len(b)*2,dtype=np.uint32)
    codes[::2]=(b&15)>>1;codes[1::2]=b>>5
    groups=codes.reshape(-1,8)
    words=np.sum(groups<<np.arange(0,24,3,dtype=np.uint32),axis=1,dtype=np.uint32)
    return np.column_stack((words&255,(words>>8)&255,words>>16)).astype('u1').tobytes()


def intervals(meta):
    # Instruction-table counts, measured between starts of consecutive OUTs.
    # SECOND defers POP HL and uses B as the phase page. The 128-level FIRST
    # adds 19 T to select a half-page; its extraction tails remove 17.5 T of
    # average padding, for +1.5 T versus the 64-level direct implementation.
    before=[23,23,37,23,15,29,23,19]
    after=[20,16,19,16,16,15,24,22]
    first=HOLDS[:8]
    if meta['model'].get('pcm_bins',64)==128:
        before=[15,11,37,11,15,29,7,19]
        after=[0,0,19,0,0,15,0,22]
        first[5]+=7;first[6]+=12
    phase_holds=[first+[26,22,27,23,16,12+before[p],12+after[p],33 if p==7 else 30]
                 for p in range(8)]
    holds=np.asarray([phase_holds[(i+2)%8] for i in range(meta['pcm_samples'])],dtype=np.int64).ravel()
    sample=0
    for s in meta['sections']:
        for byte in range(3,s['audio_bytes']+1,3):
            if (s['play_address']+byte)%256==0:
                k=(sample+byte//3*8-3)*16+14
                holds[k]+=140 if byte==s['audio_bytes'] else 14
        sample+=s['audio_bytes']//3*8
    pairs=meta.get('loop_idle_pairs',0)
    if pairs:
        k=(meta['pcm_samples']-3)*16+14
        idle=[]
        for j in range(pairs):
            idle.extend([26,33 if (j+1)%255==0 and j+1<pairs else 26])
        idle[-1]=34+meta['loop_idle_pad_tstates']
        holds=np.r_[holds[:k],holds[k]-1,idle,holds[k+1:]]
    return holds


def decoder_slots(second,pointers,*,compact_tables=True,startup_gap=True):
    """Reuse only whole aligned rows in unreachable, uncontended code gaps.

    Keep every pulse/extraction address unchanged: moving those can change
    Spectrum contention and invalidate the measured encoder clock. The
    assembler independently rejects any overlap with executable bytes.
    """
    fixed=pointers+256
    if not compact_tables:
        reserve=max(LEGACY_BANK2_RESERVE,(fixed+89*32+255)//256*256-0x8000)
        return [fixed+i*32 for i in range(89)],reserve
    slots=list(range(0x8380,0x8400,32)) if startup_gap else []
    prefix_end=max(second.values())+20
    slots+=list(range((prefix_end+31)&~31,pointers-2048,32))
    slots+=list(range(fixed,fixed+89*32,32))
    slots=slots[:89]
    reserve=(max(fixed,max(slots)+32)+255)//256*256-0x8000
    return slots,reserve


def layout(packed,model=None,hot_indices=None,*,compact_tables=True,startup_gap=True):
    model=model or MEASURED_MODEL
    bins=model.get('pcm_bins',64)
    words,nxt,_=integral_table(bins,2,holds=model['holds'],beta=model['beta'],extent=model['extent'],q_clip=tuple(model.get('q_clip',(0,15))))
    reachable={16}
    while True:
        expanded=reachable|set(map(int,nxt[:,sorted(reachable)].ravel()))
        if expanded==reachable:break
        reachable=expanded
    states=sorted(reachable);assert len(states)*6<=128
    first_patterns=sorted(set(map(int,(words[:,states]>>8).ravel())))
    second_patterns=sorted(set(map(int,(words[:,states]&255).ravel())))
    first_size=46 if bins==128 else 41
    first={p:0x8400+i*first_size for i,p in enumerate(first_patterns)}
    base=0x8400+len(first)*first_size
    second={p:base+i*20 for i,p in enumerate(second_patterns)}
    phase_base=(base+len(second)*20+255)&~255
    pointers=phase_base+2048
    fixed=pointers+256;extra=fixed+(0 if bins==128 else 1024)
    reserve=(extra+(89 if bins==128 else 73)*32+255)//256*256-0x8000
    assert reserve<=16384,'code/tables exceed fixed bank 2'
    # Keep the independently bootable screen, TR-DOS and stack allocation.
    reserve=max(reserve,14336)
    pages=[fixed+(i-28)*256 if 28<=i<32 else 0x4000+i*256 for i in range(64)]
    if bins==128:
        assert model.get('level_bounds')==[4,123]
        physical=[0x4000+i*256 for i in range(64) if not 28<=i<32]
        pages=[physical[(max(4,min(123,v))-4)//2]+(v&1)*128 for v in range(128)]
    _,indices=decode(packed)
    counts=np.bincount(np.r_[0,indices[:-1]],minlength=89)
    hot=list(range(89))
    slots=[fixed+i*256+j for i in range(4) for j in (128,160,192,224)]+[extra+i*32 for i in range(73)]
    if bins==128:
        slots,reserve=decoder_slots(second,pointers,
                                   compact_tables=compact_tables,startup_gap=startup_gap)
    assert reserve<=16384,'code/tables exceed fixed bank 2'
    rows={i:a for i,a in zip(hot,slots)}
    resident=pack3(packed)
    assert len(resident)%3==0
    sections=[];remaining=len(resident)
    for bank,capacity in [(b,16383) for b in (0,4,6,1,3)]+[(7,9471),(2,(16384-reserve)//3*3)]:
        size=min(remaining,capacity)
        if size:
            allocated=(size+255)//256*256
            sections.append(dict(bank=bank,address=0x10000-allocated,play_address=0x10000-size,
                                 bytes=allocated,audio_bytes=size,sectors=allocated//256))
        remaining-=size
    assert remaining==0, 'packed IMA3 exceeds resident capacity'
    return words,nxt,states,first,second,pointers,pages,rows,sections,hot,float(counts[hot].sum()/counts.sum()),reserve


def build_disk(packed,work,model=None,hot_indices=None,idle_pairs=0,idle_pad=0,*,compact_tables=True):
    model=model or MEASURED_MODEL
    work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    # Calibration uses at most 260 T of explicit padding. Even with seven
    # LOAD_AUDIOs and six idle blocks it leaves 8380..83FF unused. Larger
    # externally requested fillers retain the old startup gap instead.
    startup_gap=idle_pad<=260
    words,nxt,states,first,second,pointers,pages,rows,sections,hot,coverage,reserve=layout(
        packed,model,hot_indices,compact_tables=compact_tables,startup_gap=startup_gap)
    bins=words.shape[0]
    compact=compact_tables and bins==128
    startup_data=0x8380 if compact and startup_gap else 0x8400
    prefix_end=max(second.values())+20
    prefix_data=(prefix_end+31)&~31 if compact else pointers-2048
    decoder_end=max(a+32 for a in rows.values())
    resident=pack3(packed)
    assert len(resident)==sum(s['audio_bytes'] for s in sections)
    pcm,indices=decode(packed);assert (pcm[-1],indices[-1])==(0,0)
    if bins==128:
        levels=(pcm.astype(np.int32)+32768)//512
        assert np.all((levels>=4)&(levels<=123)), 'PCM control outside supported table range'
    memory=bytearray(65536)
    for value in range(bins):
        if bins==128 and not 4<=value<=123:
            continue
        for sid,state in enumerate(states):
            word=int(words[value,state]);address=pages[value]+sid*6
            memory[address:address+6]=struct.pack('<HBBH',second[word&255],states.index(int(nxt[value,state]))*6,16,first[word>>8])
    for index in range(89):
        step=STEPS[index]
        for code in range(0,16,2):
            delta=(step>>3)+(step if code&4 else 0)+(step>>1 if code&2 else 0)+(step>>2 if code&1 else 0)
            if code&8:delta=-delta
            address=rows[index]+code*2
            memory[address:address+4]=struct.pack('<HH',delta&65535,rows[max(0,min(88,index+INDEX[code&7]))])
    memory[pointers:pointers+256]=bytes(pages[i*bins//256]>>8 for i in range(256))
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),basic_line(30,b'\xf9 \xc0 \xb0 "32768"')])
    boot=TrdFile('boot','B',basic,autostart_line=10)
    track,sector=calculate_file_start([boot,TrdFile('PLAYER','C',bytes(23296),start=0x8000)])
    lower=track*16+sector;upper=lower+28;pos=upper+32
    for s in sections:s['sector']=pos;pos+=s['sectors']
    total_reads=60+sum(s['sectors'] for s in sections)
    progress_steps=np.diff(np.r_[0,(np.arange(1,33)*total_reads+31)//32])
    assert np.all((progress_steps>0)&(progress_steps<256))
    constants=dict(lpc_preloaded=0,screen_disk=0,first_base=0x8400,first_size=46 if bins==128 else 41,
                   startup_data=startup_data,prefix_data=prefix_data,
                   pcm_bins=bins,pcm_high=pointers,phase_base=pointers-2048,resident_reserve=reserve,decoder_seed=rows[0],
                   initial_feedback_offset=states.index(16)*6,lower_disk=lower//16*256+lower%16,upper_disk=upper//16*256+upper%16,
                   final_section_index=len(sections)-1,progress_first=int(progress_steps[0]))
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
                          f'next_bank_{i}':nxt_section['bank'],f'next_address_{i}':nxt_section['play_address'],f'next_tail_{i}':f'bank_tail_{successor}'})
    constants['initial_audio_address']=sections[0]['play_address']
    (work/'config.inc').write_text(''.join(f'{k}: EQU {v}\n' for k,v in constants.items()))
    for name,data in [('pcm-high',memory[pointers:pointers+256]),
                      ('decoder-startup',memory[startup_data:0x8400]),
                      ('decoder-prefix',memory[prefix_data:pointers-2048]),
                      ('fixed-pages',b'' if bins==128 else memory[pointers+256:pointers+1280]),
                      ('decoder-extra',memory[pointers+256:decoder_end] if bins==128 else memory[pointers+1280:pointers+1280+2336]),
                      ('bank5-lower',memory[0x4000:0x5c00]),('bank5-upper',memory[0x6000:0x8000]),
                      ('progress-steps',bytes(progress_steps[1:].astype('u1'))+bytes([255])),
                      ('screen',direct_loading_screen(len(packed)*2))]:
        (work/(name+'.bin')).write_bytes(data)
    (work/'player.asm').write_bytes((HERE/'ima3-direct-player.asm').read_bytes())
    run=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=player.bin','--lstfile=player.lst','-s','.*','player.asm'],cwd=work,capture_output=True,text=True)
    (work/'assembler.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    labels=next(ast.literal_eval(s) for s in run.stdout.splitlines() if s.startswith('{'))
    assert labels['resident_end']<=0x8000+reserve
    blob=(work/'player.bin').read_bytes();assert len(blob)==23296
    files=[boot,TrdFile('PLAYER','C',blob,start=0x8000),TrdFile('LOWER','C',bytes(memory[0x4000:0x5c00]),start=0x4000),TrdFile('UPPER','C',bytes(memory[0x6000:0x8000]),start=0x6000)]
    offset=0
    for i,s in enumerate(sections):
        data=bytes(s['bytes']-s['audio_bytes'])+resident[offset:offset+s['audio_bytes']]
        files.append(TrdFile(f'IMA3{i}','C',data,start=s['address']));offset+=s['audio_bytes']
    disk,directory,capacity=place_files(files,'IMADIR')
    meta=dict(direct=True,packed_ima3_direct=True,phase_base=pointers-2048,model=model,origin=0x8000,player_labels=labels,sections=sections,directory=directory,capacity=capacity,
              first_addresses=list(first.values()),second_addresses=list(second.values()),
              first_patterns=len(first),second_patterns=len(second),resident_reserve=reserve,
              loop_idle_pairs=idle_pairs,loop_idle_pad_tstates=idle_pad,
              outputs_per_cycle=len(packed)*32+idle_pairs*2,
              decoder_rows=[rows[i] for i in range(89)],hot_indices=hot,hot_coverage=coverage,
              feedback_states=states,packet_pages=pages,pcm_samples=len(packed)*2,packed_bytes=len(packed),
              ordinary_tstates=427.375 if bins==128 else 425.875,page_extra_tstates=14,bank_extra_tstates=140,
              extraction_phase_tstates=([417,413,458,413,417,446,409,446] if bins==128 else [426,422,439,422,414,427,430,427]),
              baseline_ordinary_tstates=423,ordinary_delta_tstates=4.375 if bins==128 else 2.875,
              initial_predictor=0,initial_index=0,initial_feedback=16,paging_base=24,preload_table_sectors=60,
              playback_preload_sector_reads=60+sum(s['sectors'] for s in sections),
              loading_progress_steps=32,
              record_stop_addresses=[a+2 for a in first.values()],repeat=True,
              mutable_addresses=[labels['bank_jump']+1,labels['bank_jump']+2],
              source_sample_rate_hz=8000,cpu_clock_hz=3546900,saturation_guard=require_unclipped(packed),
              resident_sha256=hashlib.sha256(resident).hexdigest(),resident_audio_bytes=len(resident),
              packed_sha256=hashlib.sha256(packed).hexdigest(),binary_sha256=hashlib.sha256(blob).hexdigest(),
              assembly=dict(instruction_bytes_emitted_by_python=False,assembler='pyz80 1.3.0'),
              memory=dict(total_ram_bytes=131072,adpcm_bytes=len(resident),sector_alignment_bytes=sum(s['bytes'] for s in sections)-len(resident),shadow_screen_bytes=6912,bank5_tables_and_workspace_bytes=16384,bank2_resident_bytes=reserve,
                          compact_tables=compact,baseline_bank2_resident_bytes=14336,
                          bank2_bytes_reclaimed=14336-reserve,
                          decoder_table_bytes=89*32,decoder_rows_retained=89,
                          decoder_bytes_in_code_gaps=sum(32 for a in rows.values() if a<pointers),
                          decoder_bytes_after_pointer_table=sum(32 for a in rows.values() if a>=pointers+256),
                          unused_audio_capacity_bytes=5*16383+9471+(16384-reserve)//3*3-len(resident),
                          maximum_ima3_bytes=5*16383+9471+(16384-reserve)//3*3,
                          maximum_pcm_samples=(5*16383+9471+(16384-reserve)//3*3)//3*8,
                          resident_ima4_bytes=0,pcm_buffer_bytes=0,pdm_buffer_bytes=0))
    return disk,meta


def direct_loading_screen(samples):
    """Keep the existing UI, with the resident format stated correctly."""
    from PIL import Image,ImageDraw,ImageFont
    from pcm_player import spectrum_bitmap_offset
    data=bytearray(loading_screen(samples,'IMA3 / DIRECT PDM'))
    tile=Image.new('1',(256,24));draw=ImageDraw.Draw(tile)
    font=ImageFont.load_default(size=13);text='3-BIT PACKED AUDIO'
    box=draw.textbbox((0,0),text,font=font)
    draw.text(((256-(box[2]-box[0]))//2,6),text,font=font,fill=1)
    for y in range(24):
        for col in range(32):
            data[spectrum_bitmap_offset(col,y+48)]=sum(
                (128>>bit) for bit in range(8) if tile.getpixel((col*8+bit,y)))
    return bytes(data)
