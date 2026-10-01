"""Defer optional track-changing reads near an imminent frame publication.

Only the clock's background queue step is wrapped. Required packet reads,
startup prefill, decode quanta and AY interrupts retain their existing paths.
Experimental only: measured late-run starvation regresses; not selected.
"""
from build_zxv_trd import MiniAssembler
from pipelined_frame_z80 import helpers, DEADLINE, READY

ORIGIN, LIMIT = 0xe340, 0xe400


def build(m):
    q,d=m['queue_labels'],m['disk_labels'];cache=m['compressed_sector_cache']['labels']
    a=MiniAssembler(ORIGIN);rows=[];e,n=helpers(a,rows,'optional_read_gate')
    def load(at):n('LD A,('+str(at)+')',0x3a,at,13)
    def branch(op,label):n('JP '+str(label),op,label,10)
    a.label('step');load(q['count']);e('CP 2',[0xfe,2],7);branch(0xda,q['step'])
    e('CP 4',[0xfe,4],7);branch(0xca,'physical')
    load(q['phase']);e('CP 2',[0xfe,2],7);branch(0xca,q['step'])
    load(cache['count']);e('OR A',[0xb7],4);branch(0xc2,q['step'])
    a.label('physical');load(d['cached_track']);e('LD B,A',[0x47],4)
    load(d['disk_position']+1);e('CP B',[0xb8],4);branch(0xca,q['step'])
    n('LD HL,(deadline)',0x2a,DEADLINE,16)
    n('LD DE,(elapsed fields)',(0xed,0x5b),m['player_labels']['elapsed_fields'],20)
    # Read READY after both counters. Otherwise an IRQ between READY and
    # DEADLINE could publish and advance the deadline, admitting a long read
    # before the next frame is drawn. No interrupt masking is needed.
    load(READY);e('OR A',[0xb7],4);branch(0xca,'idle')
    e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15)
    e('BIT 7,H',[0xcb,0x7c],8);branch(0xc2,'idle')
    e('LD A,H',[0x7c],4);e('OR A',[0xb7],4);branch(0xc2,q['step'])
    e('LD A,L',[0x7d],4);e('CP 2 fields',[0xfe,2],7);branch(0xd2,q['step'])
    a.label('idle');e('XOR A',[0xaf],4);e('RET',[0xc9],10);a.label('end')
    assert a.pc<=LIMIT
    return a.resolve(),dict(a.labels),rows


def install(banks,m):
    if not m.get('compressed_sector_cache',{}).get('enabled'):
        raise ValueError('optional read gate requires the sector cache')
    if m['compressed_sector_cache']['labels']['end']>ORIGIN:
        raise ValueError('optional gate overlaps cache code')
    code,labels,rows=build(m)
    lo=ORIGIN&16383
    assert not any(banks[7][lo:lo+len(code)])
    banks[7][lo:lo+len(code)]=code
    call=next(r for r in m['cell_codebook']['clock_listing'] if r['instruction']=='CALL idle disk read')
    at=call['address']&16383;before=bytes(banks[7][at:at+3])
    assert before==b'\xcd'+m['queue_labels']['step'].to_bytes(2,'little')
    after=b'\xcd'+labels['step'].to_bytes(2,'little');banks[7][at:at+3]=after
    m['slot_queue_instruction_listing']+=rows
    m['optional_read_gate']=dict(enabled=True,labels=labels,code_hex=code.hex(),listing=rows,
        patch=dict(address=call['address'],before_hex=before.hex(),after_hex=after.hex(),
                   previous_tstates=17,tstates=17,delta_tstates=0),
        minimum_ready_slots=2,minimum_fields_before_track_read=2,
        compressed_stream_changed=False,decoder_changed=False,
        timing_scope='Gate overhead only, excluding unchanged queue step, IRQ, ULA and physical disk service')
