"""Address-only experiment: move the compact predictor/cache to fixed bank 2.

The packet moves to bank 5. No opcodes, branches, tables of codes, or stream
bytes change. Relocation is restricted to listed LD operands and four named
page immediates; the motion cache row-high table is rebuilt explicitly.
Cold initialization is NOT relocated: the debugger installer copies the
already loaded independent checkpoint before entering the normal driver.
This is an integration experiment, not an alternative release bootstrap.
"""
from collections import Counter
from causal_tile_z80 import ROW_HIGH

FRAME, CACHE, MASKS, ATTRS = 0xa800, 0xa400, 0xb700, 0xb880
INPUT, INPUT_END, VECTORS, MAP = 0x6400, 0x7660, 0x7660, 0x7720
RANGES = ((0x6400,0x7300,FRAME), (0x7300,0x7350,MAP),
          (0x7400,0x7800,CACHE), (0xa400,0xa4c0,VECTORS),
          (0xa4c0,0xa6a0,MASKS), (0xa6a0,0xb900,INPUT))
CHECKPOINT_COPIES = ((0x6400,FRAME,3840), (0x7400,CACHE,1024))
PAGE_OPERANDS = {'OR cache_page':(0x74,0xa4), 'CP frame_page':(0x64,0xa8),
                 'CP attribute_end':(0x73,0xb7), 'OR 70h':(0x70,0xb4)}


def relocate_address(value):
    return next((dest+value-lo for lo,hi,dest in RANGES if lo<=value<hi),value)


def patches(read8, instructions):
    changes={}; audit=[]
    for row in instructions:
        if row.get('phase')=='cold_init': continue
        pc,name=row['address'],row['instruction']; opcode=read8(pc)
        offset=None
        if name.startswith('LD ') and opcode in (0x01,0x11,0x21,0x31,0x22,0x2a,0x32,0x3a): offset=1
        if name.startswith('LD ') and opcode in (0xdd,0xfd) and read8(pc+1) in (0x21,0x22,0x2a): offset=2
        if name.startswith('LD ') and opcode==0xed and read8(pc+1) in (0x43,0x4b,0x53,0x5b,0x63,0x6b,0x73,0x7b): offset=2
        if offset is not None:
            before=read8(pc+offset)+256*read8(pc+offset+1); after=relocate_address(before)
            if before!=after:
                for i,v in enumerate(after.to_bytes(2,'little')):
                    if read8(pc+offset+i)!=v:changes[pc+offset+i]=v
                audit.append(dict(address=pc,instruction=name,old_operand=before,new_operand=after,
                                  baseline_tstates=row['tstates'],tstates=row['tstates'],delta_tstates=0))
        if name in PAGE_OPERANDS:
            before,after=PAGE_OPERANDS[name]
            if read8(pc+1)!=before:raise ValueError(('page operand changed',row))
            changes[pc+1]=after
            audit.append(dict(address=pc,instruction=name,old_operand=before,new_operand=after,
                              baseline_tstates=row['tstates'],tstates=row['tstates'],delta_tstates=0))
    if not audit:raise ValueError('no frame instructions to relocate')
    for i in range(16):
        if read8(ROW_HIGH+i)!=(0x7400+i*64)>>8:raise ValueError('unexpected cache row table')
        changes[ROW_HIGH+i]=(CACHE+i*64)>>8
    return sorted(changes.items()),dict(instruction_operands=audit,changed_bytes=len(changes),
        instruction_tstate_delta=0,extra_runtime_bytes=0,packet_capacity=INPUT_END-INPUT,
        memory=[dict(old_start=lo,old_end=hi,new_start=dest,new_end=dest+hi-lo) for lo,hi,dest in RANGES],
        checkpoint_copy_tstates=sum(25+21*n for _,_,n in CHECKPOINT_COPIES),
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')


def install_stage(h):
    """Relocate a freshly built standalone stage fixture, including host RAM."""
    from benchmark_compact_screen import STACK
    from frame_output_pipeline import PipelineCPU
    from validate_fast_sparse import CPU
    if h.metadata_mode == 'idle':
        raise ValueError('idle metadata relocation is not verified')
    c=h.cpu;c.guarding=False
    # Compiled metadata lives in bank 7; bank 6 is normally mapped here.
    # Its generated bodies already exist in this standalone CPU fixture.
    page=c.port_7ffd
    if h.metadata_mode == 'compiled':c.port_7ffd=(page&~7)|7
    changes,report=patches(c.read8,h.instructions.values())
    for a,v in changes:c.write8(a,v)
    c.port_7ffd=page
    saved=[(dest,bytes(c.read8(lo+i) for i in range(hi-lo))) for lo,hi,dest in RANGES]
    for dest,blob in saved:
        for i,v in enumerate(blob):c.write8(dest+i,v)

    class RelocatedCPU(PipelineCPU):
        def read8(self,address):
            if self.guarding and self.phase in ('metadata','reconstruct') and INPUT<=address<INPUT_END and address>=self.input_end:
                raise AssertionError(f'relocated input overread {address:04x}')
            return CPU.read8(self,address)

        def write8(self,address,value):
            if self.guarding:
                screen=(self.target_bank==5 and 0x4000<=address<0x5b00 or
                        self.target_bank==7 and self.port_7ffd&7==7 and 0xc000<=address<0xdb00)
                allowed=(self.phase=='output' and (screen or 0xbf20<=address<0xbf70) or
                         self.phase=='reconstruct' and (FRAME<=address<FRAME+3840 or
                             CACHE<=address<CACHE+1024 and 1<=address&63<=32) or
                         self.phase=='metadata' and (MASKS<=address<MASKS+480 or 0xbf80<=address<0xbfc0) or
                         any(lo<=address<hi for lo,hi in self.state_regions) or STACK-96<=address<STACK)
                if not allowed:raise AssertionError(f'relocated write outside contract {address:04x}, {self.phase}')
            return CPU.write8(self,address,value)
    c.__class__=RelocatedCPU
    return report


def run_stage(h,group,native,expected,index,encoded_metadata,cache_map,interrupt=None):
    """Execute actual relocated metadata/reconstruction/native code, no disk/ULA."""
    from benchmark_context_huffman import word
    from frame_output_pipeline import display_screen
    n,flags,bits,vectors,bitmap,attrs,encoded,literals=group
    if n!=1 or len(expected)!=3840:raise ValueError('one compact frame required')
    c=h.cpu;c.guarding=False
    target=7 if index%2==0 else 5;page=0x16 if target==7 else 0x1e
    if c.port_7ffd!=page:raise AssertionError('paging history differs')
    c.target_bank=target
    def put(base,blob):
        for i,v in enumerate(blob):c.write8(base+i,v)
    put(0xba40,cache_map);put(INPUT,encoded_metadata)
    c.input_end=INPUT+len(encoded_metadata);c.set_hl(INPUT)
    if h.metadata_mode == 'compiled':c.port_7ffd=(page&~7)|7
    metadata=h.execute(h.metadata_entry,interrupt)
    if (c.hl()!=c.input_end or metadata['total_tstates']!=h.metadata_formula(encoded_metadata) or
        bytes(c.read8(MASKS+i) for i in range(480))!=bitmap+attrs or any(c.read8(0xbfbc+i) for i in range(4))):
        raise AssertionError('relocated metadata differs')
    c.guarding=False
    c.port_7ffd=page
    data=encoded+b'\0'+literals+b'\0'
    if len(data)>INPUT_END-INPUT:raise ValueError('packet too large')
    for base,blob in ((VECTORS,vectors),(MAP,native),(INPUT,data)):put(base,blob)
    c.input_end=INPUT+len(data)
    word(c,h.w['literal_pointer'],INPUT+len(encoded)+1)
    c.write8(h.w['cache_flag'],int(bool(flags&128)));c.write8(h.w['raw_attribute_flag'],int(bool(flags&64)))
    result=h.execute(h.w['run'],interrupt)
    if bytes(c.read8(FRAME+i) for i in range(3840))!=expected:raise AssertionError(('compact differs',index))
    h.expected_screens[target]=display_screen(expected,black_borders=True)
    if any(bytes(c.banks[b][:6912])!=s for b,s in h.expected_screens.items()):raise AssertionError(('native differs',index))
    if (word(c,h.recon['source'])-INPUT)*8+(c.read8(h.recon['bit_page'])&7)!=bits:raise AssertionError('bit cursor differs')
    if word(c,h.recon['literal_source'])!=INPUT+len(encoded)+1+len(literals):raise AssertionError('literal cursor differs')
    for base,blob in ((VECTORS,vectors),(MAP,native),(INPUT,data),(MASKS,bitmap+attrs),(0xba40,cache_map)):
        if bytes(c.read8(base+i) for i in range(len(blob)))!=blob:raise AssertionError('input changed')
    if c.port_7ffd!=page^8 or result['page_writes']!=[page|1,page,page^8]:raise AssertionError('paging differs')
    if bytes(c.banks[5][0x1b00:0x2400])!=b'\xa5'*0x900:raise AssertionError('TR-DOS workspace changed')
    stages=Counter(result['stages']);stages.update(metadata['stages'])
    return dict(total_tstates=result['total_tstates']+metadata['total_tstates'],stages=dict(stages))
