"""Read-only Fuse observations at external queue entries and returns.

The prefill ends immediately before the driver's CALL clock.prime. Take and
background-step observations include their caller's CALL and callee RET.
Prefill starts at the actual queue entry after mask generation (no CALL).
"""
from build_fap3_trd import player_harness
import bulk_frame_z80 as packet
import fap3_disk_z80 as disk
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header

FIELDS=('tstate','page','bc','de','a','count','phase','write_slot','read_slot',
        'blocks_left','position','slice_output')


def call_sites(m,raw):
    _,_,_,mapping,tables=read_header(Reader(raw),magic=b'FAP3')
    h=player_harness(bytes(4),tables,mapping,m['frames'],
        **{key:m[key] for key in ('inline_matches','fast_noop_scan','irq_safe_paging',
            'static_cache_borders','carry_huffman','register_fragments')},cached_huffman_byte=True)
    _,_,_,rows=packet.build(m['decoder_labels'],m['queue_labels'],h.frame.w,h.frame.draw,
        m['compiled_masks']['labels'],h.audio,stored_guards=False,separate_prepare='idle',page_entry=0x9780)
    takes=[r['address'] for r in rows if r['instruction'] in ('CALL take length','CALL take packet')]
    steps=[r['address'] for r in m['slot_queue_instruction_listing'] if r['instruction']=='CALL idle disk read']
    code,_=disk.build_driver(h,m['clock_labels'],bytes(11),has_next=True,
        prefill_entry=m['compiled_masks']['labels']['initialize'])
    # Locate two adjacent CALLs to the known initializer and clock prime.
    needle=b'\xcd'+m['compiled_masks']['labels']['initialize'].to_bytes(2,'little')+b'\xcd'+m['clock_labels']['prime'].to_bytes(2,'little')
    if len(takes)!=2 or len(steps)!=1 or code.count(needle)!=1:raise ValueError('unexpected queue caller layout')
    prefill_return=disk.DRIVER+code.index(needle)+3
    ay_returns=[r['address']+3 for r in rows if r['instruction']=='CALL enqueue_six']
    if len(ay_returns)!=1 or 'audio_enqueue_space' not in h.audio:raise ValueError('unexpected audio enqueue layout')
    return takes,steps,prefill_return,h.audio,ay_returns[0]


def configure(m,raw,event,lines,stamp,mem):
    q,z=m['queue_labels'],m['decoder_labels']
    state=[stamp,'ula:mem7ffd','z80:bc','z80:de','z80:a']
    state += [f'[{q[name]}]' for name in ('count','phase','write_slot','read_slot')]
    state += [mem(q['blocks_left']),mem(q['position']),mem(z['slice_output'])]
    event(q['prefill'],170,state,after=['set $qinit 1'])
    # Every loop revisits prefill; only its first entry is external.
    lines[-1] += ' && $qinit == 0'
    takes,steps,prefill_return,audio,ay_return=call_sites(m,raw)
    event(prefill_return,171,state)
    for pc in takes:
        event(pc,172,state);event(pc+3,173,state)
    for pc in steps:
        event(pc,174,state);event(pc+3,175,state)
    if m.get('audio_wait_prefetch',{}).get('enabled'):
        pc=m['audio_wait_prefetch']['step_call']
        event(pc,174,state);event(pc+3,175,state)
    audio_state=[stamp,f'[{audio["audio_write_index"]}]',f'[{audio["audio_read_index"]}]']
    event(audio['audio_enqueue_six'],176,audio_state)
    event(ay_return,177,audio_state)
    # EI/HALT/JP enqueue_one occupy the five bytes before enqueue_space.
    event(audio['audio_enqueue_space']-5,178,audio_state)
