"""Read sector-aligned stored blocks straight into the four video slots.

Reuse the guarded queue consumer, descriptor publication, fixed AY service
and physical TR-DOS reader. Each block has a256-byte header (u16 raw bytes,
u16 body sectors), followed by ceil(raw/256) body sectors. The queue never
exposes a descriptor before all its bytes are resident. No LZSA instruction,
in-place copy or compressed-sector cache is needed. All public calls restore
bank7; the bank5 bridge owns paging while banked input is being read/copied.
"""
from build_zxv_trd import MiniAssembler
from build_fap3_trd import sha
from pipelined_frame_z80 import helpers,PAGE


def install(banks,m):
    q,z,p,d=[m[k] for k in ('queue_labels','decoder_labels','producer_labels','disk_labels')]
    a=MiniAssembler(0xe400);rows=[];e,n=helpers(a,rows,'stored_native_input')
    def load(name):n('LD A,('+str(name)+')',0x3a,name,13)
    def store(name):n('LD ('+str(name)+'),A',0x32,name,13)
    def call(value):n('CALL '+str(value),0xcd,value,17)
    def jump(op,value):n('JP '+str(value),op,value,10)
    a.label('step');call(m['resident_audio']['hooks']['queue_service']);load(q['phase']);e('OR A',[0xb7],4);jump(0xc2,'body')
    load(q['count']);e('CP 4',[0xfe,4],7);jump(0xca,q['idle'])
    n('LD HL,(blocks_left)',0x2a,q['blocks_left'],16);e('LD A,H',[0x7c],4);e('OR L',[0xb5],4);jump(0xca,q['idle'])
    load(q['write_slot']);store(d['write_region']);e('LD A,BCh',[0x3e,0xbc],7);store(d['write_high']);call('read_bridge')
    n('LD HL,(raw length)',0x2a,0xbc00,16);n('LD BC,maximum+1',1,15873,10);call(p['validate']);n('LD (block_length),HL',0x22,z['block_length'],16)
    n('LD DE,C000',0x11,0xc000,10);e('ADD HL,DE',[0x19],11);n('LD (block_end),HL',0x22,z['block_end'],16)
    # Sector count is validated independently of the decoded extent. The
    # build also proves their exact relationship and every padded byte.
    n('LD HL,(sector count)',0x2a,0xbc02,16);n('LD BC,63',1,63,10);call(p['validate']);e('LD A,L',[0x7d],4);store('pages')
    e('LD A,C0h',[0x3e,0xc0],7);store('high');e('LD A,1',[0x3e,1],7);store(q['phase']);jump(0xc3,q['worked'])
    a.label('body');load(q['write_slot']);store(d['write_region']);load('high');store(d['write_high']);call('read_bridge')
    n('LD HL,high',0x21,'high',10);e('INC (HL)',[0x34],11);n('LD HL,pages',0x21,'pages',10);e('DEC (HL)',[0x35],11)
    jump(0xc2,q['worked']);jump(0xc3,q['block_ready'])
    a.label('state');a.label('pages');a.emit(0);a.label('high');a.emit(0);a.label('end')
    b=MiniAssembler(0x7b50);be,bn=helpers(b,rows,'stored_read_bridge')
    b.label('read_bridge');bn('CALL existing physical sector reader',0xcd,p['read_sector'],17)
    be('LD A,17h',[0x3e,0x17],7);bn('CALL restore bank7',0xcd,PAGE,17);be('RET',[0xc9],10);b.label('bridge_end')
    labels=a.labels|b.labels;regions=[(a.origin,a.resolve(labels)),(b.origin,b.resolve(labels))]
    def put(at,data):
        bank=5 if at<0x8000 else 2 if at<0xc000 else 7
        banks[bank][at&16383:(at&16383)+len(data)]=data
    old=bytes(banks[7][q['step']&16383:(q['step']&16383)+3]);put(q['step'],b'\xc3'+labels['step'].to_bytes(2,'little'))
    for at,data in regions:put(at,data)
    listing=m['slot_queue_instruction_listing']
    replacement=rows+[dict(address=q['step'],instruction='JP stored-sector producer',tstates=10,phase='stored_native_input')]
    def updated(listing):
        return [r for r in listing if not any(lo<=r['address']<lo+len(data) for lo,data in regions) and r['address']!=q['step']]+replacement
    m['slot_queue_instruction_listing']=updated(listing)
    m['streaming_input'].update(enabled=False,codec='stored',listing=updated(m['streaming_input']['listing']),
        replacement='stored_native_video',decoder_executed=False)
    m['outer_codec']='stored';m['stored_native_video']=dict(enabled=True,labels=labels,listing=rows,header_bytes=256,
        maximum_decoded_block_bytes=15872,complete_slots_only=True,raw_frames_exact=True,
        sector_cache_removed=True,decoder_executed=False,step_patch=dict(address=q['step'],before_hex=old.hex(),after_hex=('c3'+labels['step'].to_bytes(2,'little').hex()),
            previous_tstates=17,tstates=10,delta_tstates=-7),
        read_bridge_tstates=51,regions=[dict(address=at,code_hex=data.hex(),sha256=sha(data)) for at,data in regions],
        timing_scope='Producer bypasses all decoder instructions; consumer copy and physical reads are counted/measured separately.')
