"""Read optional packets only from an already produced, contiguous prefix.

Both completed slots and a suspended active ZX0 slot can satisfy the query.
The query peeks at two bytes without consuming or decoding input. Paging is
IRQ-safe, and bank 7 is restored before any parser entry or return.
"""
from build_zxv_trd import MiniAssembler
from build_fap3_trd import sha
from pipelined_frame_z80 import helpers,PAGE
from ready_packet_guard import ORIGIN,LIMIT

MIN_BODY,MAX_BODY=294,4703


def build(queue,zx0,audio,read_packet):
    a=MiniAssembler(ORIGIN);rows=[];e,n=helpers(a,rows,'packet_prefix_guard')
    a.label('guard')
    n('LD A,(count)',0x3a,queue['count'],13);e('OR A',[0xb7],4)
    n('JP Z,active',0xca,'active',10)
    n('LD A,(read_slot)',0x3a,queue['read_slot'],13)
    e('ADD A,A',[0x87],4);e('LD L,A',[0x6f],4);e('LD H,0',[0x26,0],7)
    n('LD DE,lengths',0x11,queue['lengths'],10);e('ADD HL,DE',[0x19],11)
    e('LD E,(HL)',[0x5e],7);e('INC HL',[0x23],6);e('LD D,(HL)',[0x56],7)
    e('EX DE,HL',[0xeb],4);n('JP available',0xc3,'available',10)
    a.label('active');n('LD A,(phase)',0x3a,queue['phase'],13)
    e('CP 2',[0xfe,2],7);n('JP NZ,skip',0xc2,'skip',10)
    n('LD HL,(slice_output)',0x2a,zx0['slice_output'],16)
    n('LD DE,2000',0x11,0x2000,10);e('ADD HL,DE',[0x19],11)
    a.label('available')
    n('LD DE,(position)',(0xed,0x5b),queue['position'],20)
    e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15)
    n('JP C,skip invalid position',0xda,'skip',10)
    # A legal packet needs at least 296 bytes including its size prefix.
    e('PUSH HL',[0xe5],11);n('LD BC,minimum packet',0x01,MIN_BODY+2,10)
    e('OR A',[0xb7],4);e('SBC HL,BC',[0xed,0x42],15)
    n('JP C,pop_skip',0xda,'pop_skip',10)
    e('EX DE,HL',[0xeb],4);n('LD BC,E000',0x01,0xe000,10);e('ADD HL,BC',[0x09],11)
    n('LD A,(read_slot)',0x3a,queue['read_slot'],13)
    e('CP 2',[0xfe,2],7);n('JP C,page',0xda,'page',10);e('INC A',[0x3c],4)
    a.label('page');e('OR 10h',[0xf6,0x10],7);n('CALL page input',0xcd,PAGE,17)
    a.label('peek');e('LD E,(HL)',[0x5e],7);e('INC HL',[0x23],6);e('LD D,(HL)',[0x56],7)
    e('LD A,17h',[0x3e,0x17],7);n('CALL restore bank 7',0xcd,PAGE,17)
    a.label('length_ready')
    # Validate before adding 2, so corrupt FFFE/FFFF cannot wrap and pass.
    e('EX DE,HL',[0xeb],4);n('LD DE,min body',0x11,MIN_BODY,10)
    e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15);n('JP C,pop_skip',0xda,'pop_skip',10)
    n('LD DE,body range',0x11,MAX_BODY-MIN_BODY+1,10)
    e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15);n('JP NC,pop_skip',0xd2,'pop_skip',10)
    e('ADD HL,DE',[0x19],11);n('LD DE,min packet',0x11,MIN_BODY+2,10)
    e('ADD HL,DE',[0x19],11);e('EX DE,HL',[0xeb],4);e('POP HL',[0xe1],10)
    e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15);n('JP C,skip',0xda,'skip',10)
    n('LD A,(audio_read_index)',0x3a,audio['audio_read_index'],13);e('LD B,A',[0x47],4)
    n('LD A,(audio_write_index)',0x3a,audio['audio_write_index'],13)
    e('SUB B',[0x90],4);e('AND 31',[0xe6,31],7)
    a.label('audio_ready');e('CP 26',[0xfe,26],7)
    n('JP NC,skip',0xd2,'skip',10)
    a.label('read_call');n('CALL read_packet',0xcd,read_packet,17)
    e('LD A,1',[0x3e,1],7);e('RET',[0xc9],10)
    a.label('pop_skip');e('POP HL',[0xe1],10)
    a.label('skip');e('XOR A',[0xaf],4);e('RET',[0xc9],10)
    a.label('end');code=a.resolve()
    if a.pc>LIMIT:raise ValueError('prefix guard exceeds retired ZX0 RAM')
    return code,dict(a.labels,origin=ORIGIN,code_bytes=len(code),code_hex=code.hex(),code_sha256=sha(code),
        instruction_listing=rows,min_body_bytes=MIN_BODY,max_body_bytes=MAX_BODY,
        maximum_audio_occupancy=25,previous_overhead_tstates=24,
        extra_stream_bytes=0,extra_ram_bytes=0,helper_extra_stack_bytes=4,parser_extra_stack_bytes=2,
        timing_excludes=['read_packet body including RET','IRQ','ULA','ROM','disk latency'])


def install(read8,put,m,h):
    if not m.get('bank2_zx0',{}).get('enabled') or not m.get('demand_decode'):
        raise ValueError('prefix guard requires bank-2 ZX0 and demand decoding')
    if m.get('ready_packet_guard',{}).get('enabled'):raise ValueError('packet guards are mutually exclusive')
    rows=m['slot_queue_instruction_listing'];hooks=[r['address'] for r in rows if r['instruction']=='CALL read next packet']
    if len(hooks)!=1:raise ValueError('expected one optional read site')
    start=hooks[0];target=m['packet_labels']['read_packet']
    original=bytes([0xcd])+target.to_bytes(2,'little')+bytes([0x3e,1])
    if bytes(read8(start+i) for i in range(5))!=original:raise ValueError('optional read differs')
    code,report=build(m['queue_labels'],m['decoder_labels'],h.audio,target)
    if ORIGIN<m['bank2_zx0']['old_origin'] or report['end']>m['bank2_zx0']['old_end'] or any(read8(ORIGIN+i) for i in range(len(code))):
        raise ValueError('prefix guard RAM is occupied')
    hook=bytes([0xcd,ORIGIN&255,ORIGIN>>8,0,0]);put(ORIGIN,code);put(start,hook)
    for r in rows:
        if r['address']==start:r['instruction']='CALL prefix-guarded next packet'
        if r['address']==start+3:r.update(instruction='NOP',tstates=4)
    rows.append(dict(address=start+4,instruction='NOP',tstates=4,phase='schedule'));rows.extend(report['instruction_listing'])
    return dict(report,enabled=True,hook_address=start,hook_hex=hook.hex(),previous_hook_hex=original.hex(),
        audio_labels={key:h.audio[key] for key in ('audio_read_index','audio_write_index')},
        bank7_required=True,one_slot_only=True,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
