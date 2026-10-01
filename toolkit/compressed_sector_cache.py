"""Prefetch physical sectors into unused bank-7 RAM while decoded slots are full.

Keep the original disk cursor and in-place LZSA2 stream. Cached sectors are
copied through BC00 into the selected input slot; the decoder never sees a
different byte order. All cache state and the paging copy routine are fixed.
"""
from build_zxv_trd import MiniAssembler
from build_fap3_trd import sha
from pipelined_frame_z80 import helpers,PAGE,SHADOW

FIXED,LIMIT,PREFETCH,BUFFER,SECTORS=0xb900,0xba00,0xe300,0xe400,28


def build(m):
    p,d=m['producer_labels'],m['disk_labels'];rows=[];assemblers=[]
    def setup(origin):
        a=MiniAssembler(origin);assemblers.append(a)
        return a,*helpers(a,rows,'compressed_sector_cache')
    a,e,n=setup(FIXED)
    def load(label):n('LD A,('+str(label)+')',0x3a,label,13)
    def store(label):n('LD ('+str(label)+'),A',0x32,label,13)
    def call(label):n('CALL '+str(label),0xcd,label,17)
    def advance(label):
        load(label);e('INC A',[0x3c],4);e('CP cache slots',[0xfe,SECTORS],7)
        n('JP C,'+label+'_ready',0xda,label+'_ready',10);e('XOR A',[0xaf],4)
        a.label(label+'_ready');store(label)
    a.label('take_sector');load('count');e('OR A',[0xb7],4)
    n('JP Z,physical sector',0xca,p['read_sector'],10)
    load(SHADOW);store('saved_page');load(d['write_high']);store('destination_high')
    e('LD A,17h',[0x3e,0x17],7);call(PAGE)
    load('read_index');e('ADD A,cache high',[0xc6,BUFFER>>8],7);e('LD H,A',[0x67],4);e('LD L,0',[0x2e,0],7)
    n('LD DE,carry',0x11,0xbc00,10);call(p['copy_sector'])
    load('saved_page');call(PAGE)
    load('destination_high');e('CP carry page',[0xfe,0xbc],7)
    n('JP Z,copied',0xca,'copied',10)
    e('LD D,A',[0x57],4);e('LD E,0',[0x1e,0],7);n('LD HL,carry',0x21,0xbc00,10)
    call(p['copy_sector'])
    a.label('copied');advance('read_index')
    n('LD HL,count',0x21,'count',10);e('DEC (HL)',[0x35],11);e('RET',[0xc9],10)
    a.label('state')
    for name in ('count','read_index','write_index','saved_page','destination_high'):
        a.label(name);a.emit(0)
    a.label('fixed_end')
    if a.pc>LIMIT:raise ValueError('sector cache fixed helper exceeds BA00h')
    a,e,n=setup(PREFETCH)
    a.label('prefetch');load('count');e('CP cache slots',[0xfe,SECTORS],7)
    n('JP Z,idle',0xca,'idle',10)
    n('LD HL,(remaining)',0x2a,d['remaining'],16);e('LD A,H',[0x7c],4);e('OR L',[0xb5],4)
    n('JP Z,idle',0xca,'idle',10)
    # Disk adapter maps region 6 to physical bank 7. Explicitly restore it
    # on every read, including after the FF00 sector advances its old cursor.
    e('LD A,6',[0x3e,6],7);store(d['write_region'])
    load('write_index');e('ADD A,cache high',[0xc6,BUFFER>>8],7);store(d['write_high'])
    call(p['read_sector']);advance('write_index')
    n('LD HL,count',0x21,'count',10);e('INC (HL)',[0x34],11)
    e('LD A,1',[0x3e,1],7);e('RET',[0xc9],10)
    a.label('idle');e('XOR A',[0xaf],4);e('RET',[0xc9],10);a.label('end')
    if a.pc>BUFFER:raise ValueError('prefetch code overlaps sector data')
    labels={k:v for assembler in assemblers for k,v in assembler.labels.items()}
    regions=[(assembler.origin,assembler.resolve(labels)) for assembler in assemblers]
    return regions,labels,rows


def install(banks,m):
    if not m.get('four_video_slots',{}).get('enabled') or m['cell_codebook']['wire']!='CB46':
        raise ValueError('sector cache requires four-slot CB46')
    regions,labels,rows=build(m);p,q=m['producer_labels'],m['queue_labels']
    if q['end']>PREFETCH or q['demand_end']>PREFETCH:raise ValueError('queue overlaps cache helper')
    c=m['resident_audio']['compiled']
    if any(r['address']<LIMIT and r['address']+len(bytes.fromhex(r['data_hex']))>FIXED for r in c['regions']):
        raise ValueError('fixed sector-cache helper overlaps AY allocation')
    def put(at,data):
        bank=2 if at<0xc000 else 7;lo=at&16383
        banks[bank][lo:lo+len(data)]=data
    retired=[]
    for lo,hi in ((FIXED,LIMIT),(PREFETCH,0x10000)):
        bank=2 if lo<0xc000 else 7
        retired.append(dict(bank=bank,start=lo,end=hi,sha256=sha(bytes(banks[bank][lo&16383:(hi-1&16383)+1]))))
        put(lo,bytes(hi-lo))
    patches=[];listing=m['slot_queue_instruction_listing']
    for row in listing:
        at=row['address'];bank=5 if at<0x8000 else 2 if at<0xc000 else 7;lo=at&16383
        code=bytes(banks[bank][lo:lo+3]);target=None
        if p['step']<=at<p['end'] and code==b'\xcd'+p['read_sector'].to_bytes(2,'little'):
            target=labels['take_sector']
        if q['step']<=at<q['active'] and code==b'\xca'+q['idle'].to_bytes(2,'little'):
            target=labels['prefetch']
        if target is None:continue
        updated=code[:1]+target.to_bytes(2,'little');banks[bank][lo:lo+3]=updated
        patches.append(dict(address=at,before_hex=code.hex(),code_hex=updated.hex(),
            previous_tstates=row['tstates'],tstates=row['tstates'],delta_tstates=0))
        row['instruction']='CALL cached sector' if code[0]==0xcd else 'JP Z,prefetch compressed sector'
    if len(patches)!=4:raise ValueError(('expected two reads and two idle branches',patches))
    for at,data in regions:put(at,data)
    installed=[(at,at+len(data)) for at,data in regions]
    m['slot_queue_instruction_listing']=[r for r in listing if not any(lo<=r['address']<hi for lo,hi in installed)]+rows
    remaining=[]
    for r in m['cell_codebook']['obsolete_fixed_ranges']:
        lo,hi=r['start'],r['end']
        if hi<=FIXED or lo>=labels['fixed_end']:remaining.append(r)
        else:
            if lo<FIXED:remaining.append(dict(r,end=FIXED))
            if hi>labels['fixed_end']:remaining.append(dict(r,start=labels['fixed_end']))
    m['cell_codebook']['obsolete_fixed_ranges']=remaining
    m['compressed_sector_cache']=dict(enabled=True,bank=7,start=BUFFER,end=0x10000,sectors=SECTORS,
        bytes=SECTORS*256,labels=labels,listing=rows,patches=patches,retired=retired,
        regions=[dict(address=at,code_hex=data.hex()) for at,data in regions],
        compressed_stream_changed=False,decoder_changed=False,physical_cursor_shared=True,
        timing_scope='New instruction listing excludes existing copy/page/physical-read bodies, IRQ and contention')
    m['cell_codebook']['memory']['compressed_sector_cache']=[7,BUFFER,0x10000]
