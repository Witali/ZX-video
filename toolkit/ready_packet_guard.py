"""Bound optional packet reads to a complete slot and six free AY records.

Required reads and initial priming are unchanged. The conservative bound
accepts every legal packet length without paging merely to inspect its size.
"""
from build_zxv_trd import MiniAssembler
from build_fap3_trd import sha
from pipelined_frame_z80 import helpers

ORIGIN = 0x7c31
LIMIT = 0x7d3a
MAX_PACKET = 4705  # u16 length + maximum 4703-byte body; RAM guard is not stored


def build(queue, audio, read_packet):
    a=MiniAssembler(ORIGIN);rows=[];e,n=helpers(a,rows,'optional_packet_guard')
    a.label('guard')
    n('LD A,(count)',0x3a,queue['count'],13);e('OR A',[0xb7],4)
    n('JP Z,skip',0xca,'skip',10)
    n('LD A,(read_slot)',0x3a,queue['read_slot'],13)
    e('ADD A,A',[0x87],4);e('LD L,A',[0x6f],4);e('LD H,0',[0x26,0],7)
    n('LD DE,lengths',0x11,queue['lengths'],10);e('ADD HL,DE',[0x19],11)
    e('LD E,(HL)',[0x5e],7);e('INC HL',[0x23],6);e('LD D,(HL)',[0x56],7)
    n('LD HL,(position)',0x2a,queue['position'],16);e('EX DE,HL',[0xeb],4)
    e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15)
    n('LD BC,max_packet',0x01,MAX_PACKET,10)
    e('OR A',[0xb7],4);e('SBC HL,BC',[0xed,0x42],15)
    n('JP C,skip',0xda,'skip',10)
    # The IRQ only advances read_index; a stale value overestimates occupancy.
    n('LD A,(audio_read_index)',0x3a,audio['audio_read_index'],13);e('LD B,A',[0x47],4)
    n('LD A,(audio_write_index)',0x3a,audio['audio_write_index'],13)
    e('SUB B',[0x90],4);e('AND 31',[0xe6,31],7);e('CP 26',[0xfe,26],7)
    n('JP NC,skip',0xd2,'skip',10)
    a.label('read_call');n('CALL read_packet',0xcd,read_packet,17)
    e('LD A,1',[0x3e,1],7);e('RET',[0xc9],10)
    a.label('skip');e('XOR A',[0xaf],4);e('RET',[0xc9],10)
    a.label('end');code=a.resolve()
    if a.pc>LIMIT:raise ValueError('optional guard exceeds retired ZX0 RAM')
    return code,dict(a.labels,origin=ORIGIN,code_bytes=len(code),code_hex=code.hex(),
        code_sha256=sha(code),instruction_listing=rows,max_packet_bytes=MAX_PACKET,
        maximum_audio_occupancy=25,previous_overhead_tstates=24,
        no_slot_overhead_tstates=66,short_slot_overhead_tstates=213,
        audio_full_overhead_tstates=271,accepted_overhead_tstates=291,
        accepted_delta_tstates=267,
        timing_excludes=['read_packet body including RET','IRQ','ULA','ROM','disk latency'])


def install(read8,put,m,h):
    if not m.get('bank2_zx0',{}).get('enabled'):raise ValueError('packet guard requires bank-2 ZX0')
    rows=m['slot_queue_instruction_listing']
    hooks=[r['address'] for r in rows if r['instruction']=='CALL read next packet']
    if len(hooks)!=1:raise ValueError('expected one optional read site')
    start=hooks[0];target=m['packet_labels']['read_packet']
    original=bytes([0xcd])+target.to_bytes(2,'little')+bytes([0x3e,1])
    if bytes(read8(start+i) for i in range(5))!=original:raise ValueError('optional read differs')
    code,report=build(m['queue_labels'],h.audio,target)
    if ORIGIN<m['bank2_zx0']['old_origin'] or report['end']>m['bank2_zx0']['old_end']:
        raise ValueError('guard is outside retired core')
    if any(read8(ORIGIN+i) for i in range(len(code))):raise ValueError('guard RAM is occupied')
    hook=bytes([0xcd,ORIGIN&255,ORIGIN>>8,0,0])
    put(ORIGIN,code);put(start,hook)
    # The returned A is the packet_pending value; skipped reads must keep 0.
    for r in rows:
        if r['address']==start:r['instruction']='CALL guarded next packet'
        if r['address']==start+3:r.update(instruction='NOP',tstates=4)
    rows.append(dict(address=start+4,instruction='NOP',tstates=4,phase='schedule'))
    rows.extend(report['instruction_listing'])
    return dict(report,enabled=True,hook_address=start,hook_hex=hook.hex(),previous_hook_hex=original.hex(),
        audio_labels={key:h.audio[key] for key in ('audio_read_index','audio_write_index')},
        extra_ram_bytes=0,extra_stream_bytes=0,extra_stack_bytes=2,bank7_required=True,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
