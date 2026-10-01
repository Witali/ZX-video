"""Experimental independently bootable CB41/LZSA2 player on the existing queue.

The wire bytes stay identical to the saved CB41 probe. Read its book once,
then length-prefixed packets into fixed RAM and draw directly to the back
screen. Reuse actual disk, AY50, progress and nominal six-field publication.
"""
import struct
from types import SimpleNamespace
from build_zxv_trd import MiniAssembler
from build_fap3_trd import sha,padded,sectors
from lzsa2_row_player import Builder as PreviousBuilder
from pipelined_frame_z80 import helpers,build_clock,CODE as CLOCK,VIDEO,PAGE
from frame_output_pipeline import display_screen
from disk_progress_z80 import reference_screen
import fap3_disk_z80 as disk
import cell_codebook_z80 as native
from probe_cell_codebook import history_state

PACKET,INPUT,LENGTH=0xdc00,0x6400,0xba58


def packet_code(m,labels,screen_base,*,dynamic_rows=False):
    a=MiniAssembler(PACKET);rows=[];e,n=helpers(a,rows,'cb41_packet')
    q,z=m['queue_labels'],m['decoder_labels']
    service=m['inplace_keepalive']['wrapper']
    def take(length,destination):
        n('LD DE,destination',0x11,destination,10)
        n('LD BC,count',1,length,10);n('CALL queue take',0xcd,q['take'],17)
    a.label('next_frame');a.label('read_packet')
    n('CALL audio and drive service',0xcd,service,17)
    n('LD A,(initialized)',0x3a,'initialized',13);e('OR A',[0xb7],4)
    n('JP NZ,body',0xc2,'body',10)
    # One-time book load is part of stream delivery, not a hidden host preload.
    take(2056,INPUT)
    n('LD HL,book',0x21,INPUT+8,10);n('CALL transpose book',0xcd,labels['load_book'],17)
    e('LD A,1',[0x3e,1],7);n('LD (initialized),A',0x32,'initialized',13)
    a.label('body');take(2,LENGTH)
    n('LD HL,(length)',0x2a,LENGTH,16)
    if dynamic_rows:
        e('BIT 7,H (row update)',[0xcb,0x7c],8)
        n('JP NZ,row_updates',0xc2,'row_updates',10)
    n('LD DE,minimum',0x11,144,10)
    e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15);n('JP C,fatal',0xda,z['fatal'],10)
    n('LD DE,range',0x11,3096-144+1,10);e('OR A',[0xb7],4)
    e('SBC HL,DE',[0xed,0x52],15);n('JP NC,fatal',0xd2,z['fatal'],10)
    n('LD DE,packet',0x11,INPUT,10);n('LD BC,(length)',(0xed,0x4b),LENGTH,20)
    n('CALL queue take',0xcd,q['take'],17)
    n('LD (payload_end),DE',(0xed,0x53),'payload_end',20)
    a.label('video_payload_ready');a.label('packet_ready');e('RET',[0xc9],10)
    a.label('draw_bridge');n('CALL audio and drive service',0xcd,service,17)
    # This code and the clock execute in bank 7, so both physical screens
    # are already addressable. The fixed kernel needs no frame paging.
    n('LD A,(back screen)',0x3a,screen_base,13);n('LD HL,packet',0x21,INPUT,10)
    n('CALL native draw',0xcd,labels['draw'],17)
    n('LD DE,(payload_end)',(0xed,0x5b),'payload_end',20)
    e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15)
    n('JP NZ,fatal',0xc2,z['fatal'],10);e('RET',[0xc9],10)
    a.label('prepare_bridge');e('RET',[0xc9],10)
    if dynamic_rows:
        re,rn=helpers(a,rows,'cb42_row_updates')
        a.label('row_updates')
        re('RES 7,H',[0xcb,0xbc],8);re('LD A,H',[0x7c],4);re('OR L',[0xb5],4)
        rn('JP Z,fatal',0xca,z['fatal'],10)
        rn('LD DE,257',0x11,257,10);re('PUSH HL',[0xe5],11)
        re('OR A',[0xb7],4);re('SBC HL,DE',[0xed,0x52],15);re('POP HL',[0xe1],10)
        rn('JP NC,fatal',0xd2,z['fatal'],10)
        re('LD A,L',[0x7d],4);rn('LD (patch_count),A',0x32,'patch_count',13)
        re('LD D,H',[0x54],4);re('LD E,L',[0x5d],4)
        re('ADD HL,HL',[0x29],11);re('ADD HL,DE',[0x19],11)
        re('LD B,H',[0x44],4);re('LD C,L',[0x4d],4)
        rn('LD DE,patch data',0x11,INPUT,10);rn('CALL queue take',0xcd,q['take'],17)
        rn('LD HL,patch data',0x21,INPUT,10);re('LD D,row page',[0x16,native.ROWS>>8],7)
        rn('LD A,(patch_count)',0x3a,'patch_count',13);re('LD B,A',[0x47],4)
        a.label('replace_row')
        for name,blob,t in (('LD E,(HL)',[0x5e],7),('INC HL',[0x23],6),
                ('LD A,(HL)',[0x7e],7),('INC HL',[0x23],6),('LD (DE),A',[0x12],7),
                ('INC D',[0x14],4),('LD A,(HL)',[0x7e],7),('INC HL',[0x23],6),
                ('LD (DE),A',[0x12],7),('DEC D',[0x15],4)):
            re(name,blob,t)
        rows.append(dict(address=a.pc,instruction='DJNZ replace_row',tstates=[8,13],phase='cb42_row_updates'))
        a.rel8(0x10,'replace_row');rn('JP body',0xc3,'body',10)
    a.label('state');a.label('initialized');a.emit(0)
    a.label('payload_end');a.word(0)
    if dynamic_rows:a.label('patch_count');a.emit(0)
    a.label('end')
    if a.pc>CLOCK:raise ValueError('CB41 packet code overlaps clock')
    return a.resolve(),dict(a.labels),rows


class Builder(PreviousBuilder):
    def __init__(self,*args,cell_raw,cell_start,frame_fields=6,reference_frames=None,**kwargs):
        if frame_fields not in (5,6):raise ValueError('CB41 supports five or six fields per frame')
        self.frame_fields=frame_fields
        super().__init__(*args,**kwargs)
        count,entries=struct.unpack_from('<HH',cell_raw,4)
        self.dynamic_rows=cell_raw[:4]==b'CB42'
        self.reference_frames=reference_frames
        if cell_raw[:4] not in (b'CB41',b'CB42') or entries!=256 or cell_start<0:
            raise ValueError('this builder needs a 256-entry book and a nonnegative start')
        if self.dynamic_rows and reference_frames is None:
            raise ValueError('CB42 needs independent five-level reference frames')
        at=2056
        for _ in range(count):
            length=struct.unpack_from('<H',cell_raw,at)[0]
            while self.dynamic_rows and length&0x8000:
                replacements=length&0x7fff
                if not 1<=replacements<=256:raise ValueError('invalid CB42 row replacement count')
                at+=2+3*replacements
                length=struct.unpack_from('<H',cell_raw,at)[0]
            if not 144<=length<=3096:raise ValueError('CB41 payload outside native contract')
            at+=2+length
        if at!=len(cell_raw):raise ValueError('CB41 frame extents differ')
        self.cell_raw=cell_raw;self.cell_start=cell_start;self.cell_end=cell_start+count

    def separated(self,start,end):
        if (start,end)!=(self.cell_start,self.cell_end):raise ValueError('different CB41 window')
        _,sound=super().separated(start,end)
        return self.cell_raw,sound

    def ram(self,start,end,next_sector,remaining):
        sections,m=super().ram(start,end,next_sector,remaining);banks=self.expected_banks
        def bank(at):return 5 if at<0x8000 else 2 if at<0xc000 else 7
        def read(at):return banks[bank(at)][at&16383]
        def put(at,data):
            if (at&16383)+len(data)>16384:raise ValueError('cross-bank CB41 install')
            banks[bank(at)][at&16383:(at&16383)+len(data)]=data
        regions,labels,layout=native.build(dictionary=True)
        screen_base,saved_page=labels['end'],labels['end']+1
        retired=[];patches=[]
        for lo,hi in ((native.CODE,0x9400),(0xa800,0xb700),(PACKET,0xe000)):
            retired.append(dict(start=lo,end=hi,sha256=sha(bytes(read(at) for at in range(lo,hi)))))
            put(lo,bytes(hi-lo))
        for at,data in regions:put(at,data)
        put(screen_base,bytes([0xc0,0x17]))
        # Old screen state lived inside the retired renderer. Remap only the
        # retained IRQ's named load/store operands, with unchanged opcodes/T.
        for row in m['slot_queue_instruction_listing']:
            pc,name=row['address'],row['instruction']
            if not VIDEO<=pc<PAGE:continue
            for key,target in (('screen_base',screen_base),('saved_page',saved_page)):
                if name in ('LD A,('+key+')','LD ('+key+'),A'):
                    old=bytes([read(pc+1),read(pc+2)]);put(pc+1,target.to_bytes(2,'little'))
                    patches.append(dict(address=pc,old_operand=int.from_bytes(old,'little'),new_operand=target,
                        previous_tstates=13,tstates=13,delta_tstates=0))
        if len(patches)!=4:raise ValueError('unexpected IRQ screen-state references')
        # The resident stream owns the AY tick count independently of video.
        # Only the immediate deadline increment changes: LD DE,nn stays 10 T.
        steps=[r for r in m['slot_queue_instruction_listing']
               if VIDEO<=r['address']<PAGE and r['instruction']=='LD DE,6']
        if len(steps)!=1:raise ValueError('unexpected video deadline increment')
        step=steps[0];pc=step['address']
        if bytes(read(pc+i) for i in range(3))!=b'\x11\x06\x00':
            raise ValueError('video deadline instruction changed')
        put(pc+1,self.frame_fields.to_bytes(2,'little'))
        step['instruction']=f'LD DE,{self.frame_fields}'
        if m['resident_audio']['compiled']['ticks']!=(end-start)*self.frame_fields:
            raise ValueError('resident AY count does not match video duration')
        m['video_cadence']=dict(fields_per_frame=self.frame_fields,ay_hz=50,
            deadline_increment_pc=pc,previous_tstates=10,tstates=10,delta_tstates=0,
            schedule_origin_preserved=True)
        code,p,rows=packet_code(m,labels,screen_base,dynamic_rows=self.dynamic_rows);put(PACKET,code)
        # The old clock was retired above; its progress target is a constant
        # from the unchanged progress component.
        import disk_progress_z80
        progress_code,progress_labels,progress_rows,_=disk_progress_z80.build(end-start)
        if p['end']>disk_progress_z80.CODE:raise ValueError('CB41 packet overlaps progress')
        put(disk_progress_z80.CODE,progress_code)
        initial=progress_labels['initial_state']-disk_progress_z80.CODE
        put(progress_labels['state'],progress_code[initial:initial+7])
        clock,c,crows=build_clock(p,m['audio_labels'],end-start,zx0=m['decoder_labels'],
            progress_entry=progress_labels['tick'],packet_ahead=False,disk_idle_entry=m['queue_labels']['step'])
        put(CLOCK,clock)
        driver,dl=disk.build_driver(SimpleNamespace(frames=end-start,audio=m['audio_labels']),c,self.ay[start],
            has_next=end<len(self.states),prefill_entry=m['queue_labels']['prefill'])
        put(disk.DRIVER,driver);m['player_labels'].update(dl)
        # Cold boot stores the exact required histories, independently of
        # anything left in RAM by another disk. No compact frame survives.
        for b,frame in ((7,start-2),(5,start-1)):
            if self.dynamic_rows:
                from dynamic_row_dictionary import screen
                initial=screen(self.reference_frames,frame)
            else:
                initial=display_screen(history_state(self.states,frame).tobytes(),black_borders=True)
            banks[b][:6912]=reference_screen(initial,0,end-start)
        m.update(packet_labels=p,clock_labels=c,clock_end=c['end'],driver_end=dl['end'],
            native_ready_pcs=[r['address']+3 for r in crows if r['instruction'] in ('CALL native zero','CALL draw_compact')])
        retired_ranges=[(r['start'],r['end']) for r in retired]
        m['slot_queue_instruction_listing']=[r for r in m['slot_queue_instruction_listing']
            if not any(lo<=r['address']<hi for lo,hi in retired_ranges)]+rows+crows+progress_rows+layout['instruction_listing']
        m['cell_codebook']=dict(enabled=True,experimental=True,wire='CB42' if self.dynamic_rows else 'CB41',raw_sha256=sha(self.cell_raw),
            raw_bytes=len(self.cell_raw),native_labels=labels,screen_base=screen_base,saved_page=saved_page,
            native=layout,packet_listing=rows,clock_listing=crows,irq_patches=patches,retired=retired,
            header_bytes=2056,book_loaded_from_stream=True,initial_frames=[start-2,start-1],
            compact_frame_removed=True,packet_ahead=False,packet_capacity=3096,
            memory=dict(screens=[5,7],video_slots=[0,1,3],audio=4,unused_legacy_huffman=6,
                fixed_kernel=[native.CODE,saved_page+1],rows=[0x9e00,0xa000],book=[0xa800,0xb000],
                popcount=[0xb000,0xb100],packet=[INPUT,INPUT+3096],stack_top=0x9df0,
                disk_stack_top=disk.DISK_STACK),
            delivery_measured=False,release=False)
        if 'segments' in m['resident_audio']['compiled']:
            m['cell_codebook']['memory']['audio']=[4,6]
            del m['cell_codebook']['memory']['unused_legacy_huffman']
        if self.dynamic_rows:
            m['cell_codebook']['dynamic_rows']=dict(enabled=True,slots=256,mutable_bytes=512,
                ordinary_packet_delta_tstates=18,renderer_delta_tstates=0,
                update_handler_tstates='207 + 74 * replaced_rows',
                update_handler_excludes='queue take body, dispatch, length read, IRQ, contention and disk latency',
                wire='8001h..8100h, then count triples: index, top, bottom',
                prior_screen_copies_required=False,pixel_changes=0)
        retired_keys=('compiled_masks','hl_mask_reader','compact_cursor','cached_huffman_lookahead',
                      'inline_huffman_patches','inline_literals')
        m['cell_codebook']['retired_metadata']={key:m[key] for key in retired_keys if key in m}
        for key in retired_keys:
            if key in m:m[key]=dict(enabled=False,replaced_by='cell_codebook')
        result=[]
        for s in sections:
            lo=s['address']&16383;raw=bytes(banks[s['bank']][lo:lo+s['decoded_bytes']])
            if sha(raw)==s['sha256']:result.append(s);continue
            if s.get('startup_delta'):raise ValueError('unexpected startup delta')
            coded=self.compress(raw)
            capacity=6912 if s['buffer']==0x4000 else 4608
            if len(padded(coded))>capacity:raise ValueError('CB41 startup staging overflow')
            result.append(dict(s,data=padded(coded),compressed_bytes=len(coded),sectors=sectors(coded),sha256=sha(raw)))
        return result,m

    def volume(self,start,end,part):
        image,m=super().volume(start,end,part)
        if self.dynamic_rows:m['states_sha256']=sha(self.reference_frames.tobytes())
        m.update(frame_fields=self.frame_fields,fps='10' if self.frame_fields==5 else '25/3',
            duration_seconds=(end-start)*self.frame_fields/50,
            ay_ticks=(end-start)*self.frame_fields)
        return image,m
