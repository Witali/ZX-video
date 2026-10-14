"""Direct packet pointers with a closed feedback state set and split tables."""
import ast,gzip,hashlib,json,struct,subprocess,sys
from pathlib import Path
import numpy as np
from feedback_player import loading_screen
from ima_codec import decode,STEPS,INDEX,require_unclipped
from pcm_player import TrdFile,basic_line,calculate_file_start,place_files
from probe_feedback_packets import integral_table
from ram_cache import pack_controller,write_decoder,enabled as ram_enabled,copy_worker,IMA4_BYTES
from verify_pcm import save

HERE=Path(__file__).resolve().parent
MAX_PACKED_BYTES=93440
HOLDS=[36,28,28,31,24,26,22,20,22,26,22,30,31,27,34,16]
# The current four-bit encoder uses an integer PCM grid: unsigned128 is
# exactly one-half duty. Archived models without pcm_origin retain midpoint
# bins, so their tables and disk bytes remain independently reproducible.
MEASURED_MODEL=dict(holds=[288,231,225,248,192,218,204,170,215,226,177,240,248,216,291,156],
                    beta=.5,extent=.5,weight_units='eighth T-state; rounded ordinary Fuse means',
                    pcm_origin=0,
                    calibration='experiments/ima-direct/output-times.u32.gz')


def canonical_pcm_model(model=None):
    """Validate the optional 512-unit PCM16 bias; preserve historical defaults.

    The live player indexes its 256-byte table with IXH. A bias of 512 adds
    exactly two unsigned high-byte units before the divide by four, so it
    requires no live instructions. Zero is omitted from exported metadata.
    Other grids/families have no proved hardware interpretation for this flag.
    """
    result=dict(model or dict(holds=HOLDS,beta=.5,extent=1.))
    bias=result.pop('pcm_quantization_bias',0)
    if type(bias) is not int or bias not in (0,512):
        raise ValueError('pcm_quantization_bias must be integer0 or512 (PCM16 units)')
    if bias:
        if result.get('pcm_bins',64)!=64 or result.get('family') not in (None,'integral'):
            raise ValueError('PCM quantization bias requires the64-bin integral PDM model')
        result['pcm_quantization_bias']=bias
    if 'neutral_packet_word' in result or 'neutral_packet_successor' in result:
        from neutral_packet_model import validate_neutral_packet
        validate_neutral_packet(result)
    if 'idle_cycle_word' in result:
        from idle_cycle_packet_model import validate_idle_cycle_packet
        validate_idle_cycle_packet(result)
    if 'idle_pair_words' in result:
        from idle_pair_packet_model import validate_idle_pair_packet
        validate_idle_pair_packet(result)
    return result


def pcm_high_lookup(pages,model=None):
    """Map every IXH to a packet page, with an explicit upper-bin clamp.

    The lower eight PCM bits cannot change floor((PCM16+32768+512)/1024).
    Thus min(63,(IXH+2)//4) is exact over all65536 signed PCM values. Compute
    with host integers: an 8-bit addition would wrap IXH254/255 incorrectly.
    """
    model=canonical_pcm_model(model)
    high_bias=model.get('pcm_quantization_bias',0)//256
    return bytes(pages[min(63,(high+high_bias)//4)]>>8 for high in range(256))


def pcm_quantization_metadata(model):
    """Describe the opt-in data-only lookup change, never a quality claim."""
    return dict(pcm16_bias=model['pcm_quantization_bias'],pcm16_bucket_step=1024,
                hardware_index='IXH',lookup_bytes=256,packet_bin='min(63,(IXH+2)//4)',
                saturated_upper_bin=63,live_instruction_changes=False,
                lookup_native_tstate_delta=0,
                timing_scope='Native instruction counts only;128/Scorpion ULA waits depend on selected addresses and require separate actual timing verification')


def neutral_packet_metadata(model):
    """Record the literal ordinary-packet contract, without source-fit claims."""
    word=model['neutral_packet_word'];period=sum(model['holds'])
    on=sum(hold for slot,hold in enumerate(model['holds']) if (word>>(15-slot))&1)
    return dict(packet_bin=32,word=word,word_hex=f'{word:04x}',successor=model['neutral_packet_successor'],
                ordinary_on_tstates=on,ordinary_period_tstates=period,ordinary_mean_duty=on/period,
                source_independent_selection_assumption='One literal chosen once from all65536 words with224/225 on-T of449 by analytical steady filtered variance; builder validates the contract, not the selection provenance',
                live_instruction_changes=False,packet_native_tstate_delta=0,
                scope='Ordinary Pentagon packet only; bank/page holds and128/Scorpion ULA effects require separate complete verification')


def idle_cycle_packet_metadata(model):
    """Describe a word-only idle-cycle override; no successor or clock change."""
    word=model['idle_cycle_word'];period=sum(model['holds'])
    on=sum(hold for slot,hold in enumerate(model['holds']) if word&(1<<(15-slot)))
    return dict(packet_bin=32,word=word,word_hex=f'{word:04x}',feedback_states=[16,17],
                preserve_successors=True,successor_cycle=[17,16],
                ordinary_on_tstates=on,ordinary_period_tstates=period,ordinary_mean_duty=on/period,
                source_independent_selection_assumption='Reuse the frozen balanced0x56ad literal selected analytically without source audio; change only the emitted words in the existing16/17 idle cycle',
                live_instruction_changes=False,packet_native_tstate_delta=0,
                scope='Ordinary Pentagon packet only; bank/page holds and128/Scorpion ULA effects require separate complete verification')


def idle_pair_packet_metadata(model):
    """Record the fixed two-word neutral cycle and its exact mean duty."""
    words=model['idle_pair_words'];period=sum(model['holds'])
    on=[sum(hold for slot,hold in enumerate(model['holds']) if word&(1<<(15-slot))) for word in words]
    return dict(packet_bin=32,words=list(words),words_hex=[f'{word:04x}' for word in words],
                feedback_states=[16,17],preserve_successors=True,successor_cycle=[17,16],
                ordinary_on_tstates=on,ordinary_period_tstates=period,
                pair_on_tstates=sum(on),pair_period_tstates=2*period,pair_mean_duty=sum(on)/(2*period),
                source_independent_selection_assumption='One frozen pair selected analytically without source audio, with224 then225 on-T of449; replace only the emitted words in the existing16/17 idle cycle',
                live_instruction_changes=False,packet_native_tstate_delta=0,
                scope='Ordinary Pentagon pair only; bank/page holds and128/Scorpion ULA effects require separate complete verification')


def layout(packed,model=None,hot_indices=None,*,resident_limit=14336):
    model=canonical_pcm_model(model)
    extended=ram_enabled(model)
    # Legacy builders retain their14336-byte reserve and source capacity.
    # The continuous stream owns all of bank2 and may explicitly move its
    # loading-only worker. Never infer a larger budget for a legacy caller.
    if resident_limit!=14336 and not extended:
        raise ValueError('a larger resident limit requires the continuous RAM layout')
    if not 14336<=resident_limit<=16384:
        raise ValueError('resident limit must stay within fixed bank2')
    words,nxt,_=integral_table(64,2,holds=model['holds'],beta=model['beta'],extent=model['extent'],pcm_origin=model.get('pcm_origin',.5))
    if 'neutral_packet_word' in model:
        from neutral_packet_model import apply_neutral_packet
        words,nxt=apply_neutral_packet(words,nxt,model)
    if 'idle_cycle_word' in model:
        from idle_cycle_packet_model import apply_idle_cycle_packet
        words,nxt=apply_idle_cycle_packet(words,nxt,model)
    if 'idle_pair_words' in model:
        from idle_pair_packet_model import apply_idle_pair_packet
        words,nxt=apply_idle_pair_packet(words,nxt,model)
    reachable={16}
    while True:
        expanded=reachable|set(map(int,nxt[:,sorted(reachable)].ravel()))
        if expanded==reachable:break
        reachable=expanded
    states=sorted(reachable);assert len(states)*6<=128
    first_patterns=sorted(set(map(int,(words[:,states]>>8).ravel())))
    second_patterns=sorted(set(map(int,(words[:,states]&255).ravel())))
    # Zero-origin tables need four more first/two more second patterns. Reuse
    # 128 bytes of uncontended startup padding; page alignment then leaves the
    # PCM-pointer/decoder tables at their old addresses and retains all audio.
    # Assembly separately proves that the complete loader/filler fits below it.
    first_base=0x8340 if extended else 0x8380 if model.get('pcm_origin',.5)==0 else 0x8400
    first_size=42 if extended else 41
    first={p:first_base+i*first_size for i,p in enumerate(first_patterns)}
    base=first_base+len(first)*first_size
    second={p:base+i*64 for i,p in enumerate(second_patterns)}
    pointers=(base+len(second)*64+255)&~255
    fixed=pointers+256;extra=fixed+1024
    reserve=(extra+17*64+255)//256*256-0x8000
    assert reserve<=resident_limit,'preserve the declared resident code/table budget'
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
    assert 256<=len(packed)<=(IMA4_BYTES if extended else MAX_PACKED_BYTES) and len(packed)%256==0
    sections=[];remaining=len(packed)
    for bank,capacity in [(b,16384) for b in (0,4,6,1,3)]+[(7,7936 if extended else 9472)]+([] if extended else [(2,2048)]):
        size=min(remaining,capacity)
        if size:sections.append(dict(bank=bank,address=0x10000-size,bytes=size,sectors=size//256))
        remaining-=size
    return words,nxt,states,first,second,pointers,pages,rows,sections,hot,float(counts[hot].sum()/counts.sum())


def build_disk(packed,work,model=None,hot_indices=None,idle_pairs=0,idle_pad=0,*,chain=None,storage=None,cover=None):
    if (chain is None)!=(storage is None):raise ValueError('chain and storage must be supplied together')
    model=canonical_pcm_model(model)
    work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    words,nxt,states,first,second,pointers,pages,rows,sections,hot,coverage=layout(packed,model,hot_indices)
    extended=ram_enabled(model or {})
    if extended:
        assert len(states)<=18,'persistent cache state needs a16-byte packet-page gap'
        copy_worker(work)
        if chain:
            write_decoder(work)
            controller=pack_controller(chain['controller_blob'])
            assert len(controller)<=1536,'transient controller exceeds bank7 reserve'
            (work/'controller.lzsa').write_bytes(controller+bytes(1536-len(controller)))
        else:(work/'controller.lzsa').write_bytes(bytes(1536))
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
    memory[pointers:pointers+256]=pcm_high_lookup(pages,model)
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),basic_line(30,b'\xf9 \xc0 \xb0 "32768"')])
    boot=TrdFile('boot','B',basic,autostart_line=10)
    track,sector=calculate_file_start([boot,TrdFile('PLAYER','C',bytes(24832 if extended else 23296),start=0x8000)])
    lower=track*16+sector;upper=lower+28;pos=upper+32
    for s in sections:s['sector']=pos;pos+=s['sectors']
    if storage is not None:
        lower,upper=storage['lower'],storage['upper']
        assert len(storage['audio'])==len(sections)
        for s,sector in zip(sections,storage['audio']):s['sector']=sector
    total_reads=60+sum(s['sectors'] for s in sections)
    progress_steps=np.diff(np.r_[0,(np.arange(1,33)*total_reads+31)//32])
    constants=dict(lpc_preloaded=0,screen_disk=0,extended_ram=int(extended),first_size=42 if extended else 41,
                   first_patterns=len(first),codec_bits=4,
                   cache_future_sector=chain.get('future_sector',0) if chain else 0,
                   cache_disk_end_sector=chain.get('end_sector',0) if chain else 0,
                   first_base=min(first.values()),pcm_high=pointers,resident_reserve=16384 if extended else 14336,decoder_seed=rows[0],
                   initial_feedback_offset=states.index(16)*6,lower_disk=lower//16*256+lower%16,upper_disk=upper//16*256+upper%16,
                   final_section_index=len(sections)-1)
    constants.update(chained_playback=int(chain is not None),
                     chain_disk=chain['controller_disk'] if chain else 0,
                     chain_sectors=chain['controller_sectors'] if chain else 0,
                     chain_volume=chain['volume'] if chain else 0,
                     chain_next_slot=chain['next_slot'] if chain else 0,
                     progress_first=int(progress_steps[0]))
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
    screen=loading_screen(len(packed)*2,'IMA / DIRECT PDM')
    if chain:
        from ima3_direct_player import direct_loading_screen
        screen=direct_loading_screen(len(packed)*2,chain,bits=4)
    if cover is not None:screen=cover
    for name,data in [('pcm-high',memory[pointers:pointers+256]),('fixed-pages',memory[pointers+256:pointers+1280]),
                      ('decoder-extra',memory[pointers+1280:pointers+1280+1088]),
                      ('bank5-lower',memory[0x4000:0x5c00]),('bank5-upper',memory[0x6000:0x8000]),
                      ('screen',screen),('progress-steps',bytes(progress_steps[1:].astype('u1'))+bytes([255]))]:
        (work/(name+'.bin')).write_bytes(data)
    (work/'player.asm').write_bytes((HERE/'direct-player.asm').read_bytes())
    run=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=player.bin','--lstfile=player.lst','-s','.*','player.asm'],cwd=work,capture_output=True,text=True)
    (work/'assembler.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    labels=next(ast.literal_eval(s) for s in run.stdout.splitlines() if s.startswith('{'))
    if chain and not extended:assert labels['resident_end']<=0xb800 and labels['resident_end']-labels['chain_exit']==57
    blob=(work/'player.bin').read_bytes();assert len(blob)==(24832 if extended else 23296)
    files=[boot,TrdFile('PLAYER','C',blob,start=0x8000),TrdFile('LOWER','C',bytes(memory[0x4000:0x5c00]),start=0x4000),TrdFile('UPPER','C',bytes(memory[0x6000:0x8000]),start=0x6000)]
    offset=0
    for i,s in enumerate(sections):
        files.append(TrdFile(f'IMA{i}','C',packed[offset:offset+s['bytes']],start=s['address']));offset+=s['bytes']
    disk,directory,capacity=place_files(files,'IMADIR') if storage is None else (None,[],{})
    meta=dict(direct=True,model=model or dict(holds=HOLDS,beta=.5,extent=1.),origin=0x8000,player_labels=labels,sections=sections,directory=directory,capacity=capacity,
              extended_ram=extended,first_code_bytes=42 if extended else 41,
              first_addresses=list(first.values()),second_addresses=list(second.values()),
              first_patterns=len(first),second_patterns=len(second),resident_reserve=16384 if extended else 14336,
              loop_idle_pairs=idle_pairs,loop_idle_pad_tstates=idle_pad,
              outputs_per_cycle=len(packed)*32+idle_pairs*2,
              decoder_rows=[rows[i] for i in range(89)],hot_indices=hot,hot_coverage=coverage,
              feedback_states=states,packet_pages=pages,pcm_samples=len(packed)*2,packed_bytes=len(packed),
              ordinary_holds_tstates=HOLDS,ordinary_tstates=sum(HOLDS),page_extra_tstates=14,bank_extra_tstates=140,
              initial_predictor=0,initial_index=0,initial_feedback=16,paging_base=24,preload_table_sectors=60,
              chained_playback={k:v for k,v in chain.items() if k!='controller_blob'} if chain else None,loading_progress_steps=32 if chain else 0,
              record_stop_addresses=[a+2 for a in first.values()],repeat=True,
              mutable_addresses=[labels['bank_jump']+1,labels['bank_jump']+2],
              source_sample_rate_hz=8000,cpu_clock_hz=3546900,saturation_guard=require_unclipped(packed),
              packed_sha256=hashlib.sha256(packed).hexdigest(),binary_sha256=hashlib.sha256(blob).hexdigest(),
              assembly=dict(instruction_bytes_emitted_by_python=False,assembler='pyz80 1.3.0'),
              memory=dict(total_ram_bytes=131072,adpcm_bytes=len(packed),shadow_screen_bytes=6912,bank5_tables_and_workspace_bytes=16384,bank2_resident_bytes=16384 if extended else 14336,
                          unused_audio_capacity_bytes=(IMA4_BYTES if extended else MAX_PACKED_BYTES)-len(packed),pcm_buffer_bytes=0,pdm_buffer_bytes=0))
    if model.get('pcm_quantization_bias'):meta['pcm_quantization']=pcm_quantization_metadata(model)
    if 'neutral_packet_word' in model:meta['neutral_packet']=neutral_packet_metadata(model)
    if 'idle_cycle_word' in model:meta['idle_cycle_packet']=idle_cycle_packet_metadata(model)
    if 'idle_pair_words' in model:meta['idle_pair_packet']=idle_pair_packet_metadata(model)
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
