"""Restore four video slots with AY payload in bank 6 and optional fixed RAM tail."""

from inplace_slot_input_z80 import MAX_OUTPUT


def install(banks,m):
    audio=m['resident_audio'];q=m['queue_labels'];p=m['producer_labels']
    if not audio.get('shared_fixed') or audio['banks']!=[6]:
        raise ValueError('four slots require fixed audio code/trees and bank 6 as the only paged audio bank')
    if audio['video_slot_banks']!=[0,1,3]:raise ValueError('unexpected original slot map')
    rows=m['slot_queue_instruction_listing'];patches=[];removed=[];added=[]
    def replace(at,before,after,listing,previous,total):
        bank=5 if at<0x8000 else 2 if at<0xc000 else 7;lo=at&16383
        assert bytes(banks[bank][lo:lo+len(before)])==before,('slot patch mismatch',hex(at))
        assert len(before)==len(after)
        banks[bank][lo:lo+len(after)]=after;removed.append((at,at+len(after)));added.extend(listing)
        patches.append(dict(address=at,before_hex=before.hex(),code_hex=after.hex(),
            previous_tstates=previous,tstates=total,
            delta_tstates=[total-n for n in previous] if isinstance(previous,list) else total-previous))
    for lo,hi in ((q['step'],q['active']),(p['begin'],p['step'])):
        matches=[r for r in rows if lo<=r['address']<hi and r['instruction']=='CP 3']
        assert len(matches)==1,matches
        row=matches[0]
        replace(row['address'],b'\xfe\x03',b'\xfe\x04',[dict(row,instruction='CP 4')],7,7)
    for lo,hi in ((q['block_ready'],q['worked']),(q['release'],q['retained'])):
        matches=[r for r in rows if lo<=r['address']<hi and r['instruction']=='CALL advance three-slot cursor']
        assert len(matches)==1,matches
        row=matches[0];at=row['address']
        replace(at,b'\xcd'+audio['hooks']['advance_slot'].to_bytes(2,'little'),b'\x3c\xe6\x03',
            [dict(row,instruction='INC A',tstates=4),dict(row,address=at+1,instruction='AND 3',tstates=7)],
            [39,47],11)
    m['slot_queue_instruction_listing']=[r for r in rows if not any(lo<=r['address']<hi for lo,hi in removed)]+added
    audio.update(video_slot_banks=[0,1,3,4],video_ready_history_bytes=4*MAX_OUTPUT,
        queue_cursor_tstates_after=11,queue_cursor_delta_tstates=0)
    m['cell_codebook']['memory']['video_slots']=[0,1,3,4]
    m['cell_codebook']['memory'].pop('unused_legacy_huffman',None)
    m['inplace_video']['video_ready_history_bytes']=4*MAX_OUTPUT
    # Earlier component metadata is historical; the explicit patches below
    # and final queue instruction listing describe the installed override.
    m['four_video_slots']=dict(enabled=True,patches=patches,video_banks=[0,1,3,4],audio_bank=6,
        decoded_capacity_before=3*MAX_OUTPUT,decoded_capacity_after=4*MAX_OUTPUT,
        paging_mapping_changed=False,compressed_stream_changed=False,
        cursor_before_tstates=[39,47],cursor_after_tstates=11,cursor_delta_tstates=[-28,-36],
        admission_before_tstates=7,admission_after_tstates=7,
        timing_scope='Per executed cursor/admission; excludes IRQ, contention, disk and different service work')
