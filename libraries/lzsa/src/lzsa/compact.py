"""Altered forward LZSA2 Small by spke & uniabis, with byte-exact EOF.

Derived from asm/unlzsa2_small.asm, pinned upstream15ee2dfe. Copyright and
zlib conditions are retained in that source and LICENSE. This is an altered
version: discard the extended-length return and return directly at EOD,
before fetching dummy word bytes or entering the nibble reader again.
Backward and IX-offset options are not part of this forward profile.
"""
from pathlib import Path
from ._z80 import MiniAssembler,sha


def build(*,core=0x8000,core_limit=0x8400):
    """Resident valid raw-v2 input/history; HL=input, DE=nonwrapping output.

    Caller stack, writable offset; AF/AF'/BC/DE/HL clobbered. IRQ preserves
    these registers including the shared nibble cache's S flag. No quotas,
    paging, coroutine state or output-size enforcement. See block.build.
    """
    if not 0<=core<core_limit<=65536:raise ValueError('invalid code reservation')
    a=MiniAssembler(core);rows=[]
    def emit(name,code,t):
        rows.append(dict(address=a.pc,instruction=name,tstates=t));a.emit(*code)
    def absolute(op,label,name,t):
        rows.append(dict(address=a.pc,instruction=name,tstates=t));a.abs16(op,label)
    def jr(op,label):
        rows.append(dict(address=a.pc,instruction='JR '+label,tstates=12 if op==0x18 else [7,12]));a.rel8(op,label)
    def inc():emit('INC HL',(0x23,),6)
    def copy():emit('LDIR',(0xed,0xb0),[16,21])
    def call(op,label):absolute(op,label,'CALL '+label,17 if op==0xcd else [10,17])
    def ret(op=0xc9):emit('RET',(op,),10 if op==0xc9 else [5,11])
    # Alternate AF caches the low nibble. S=0 requests a refill; S=1 returns
    # the cached nibble. Initialize it on every independent block.
    a.label('start');emit('XOR A',(0xaf,),4);emit('LD B,A',(0x47,),4);emit('EX AF,AF\'',(8,),4);jr(0x18,'ReadToken')
    a.label('Case00x');emit('PUSH AF',(0xf5,),11);call(0xcd,'NibbleSkipC');emit('LD C,A',(0x4f,),4)
    emit('POP AF',(0xf1,),10);emit('CP 32',(0xfe,32),7);emit('RL C',(0xcb,0x11),8);jr(0x18,'SaveOffset')
    a.label('Case0xx');emit('DEC B',(5,),4);emit('CP 64',(0xfe,64),7);jr(0x38,'Case00x')
    emit('CP 96',(0xfe,96),7)
    a.label('RotateB');emit('RL B',(0xcb,0x10),8)
    a.label('ReadOffsetC');emit('LD C,(HL)',(0x4e,),7);inc()
    a.label('SaveOffset');absolute((0xed,0x43),'offset','LD (offset),BC',20);emit('LD B,0',(6,0),7)
    a.label('MatchLen');emit('AND 7',(0xe6,7),7);emit('ADD A,2',(0xc6,2),7);emit('CP 9',(0xfe,9),7);call(0xcc,'ExtendedCode')
    a.label('CopyMatch');emit('LD C,A',(0x4f,),4);emit('PUSH HL',(0xe5,),11)
    a.labels['offset']=a.pc+1;emit('LD HL,offset',(0x21,0,0),10);emit('ADD HL,DE',(0x19,),11)
    copy();emit('POP HL',(0xe1,),10)
    a.label('ReadToken');emit('LD A,(HL)',(0x7e,),7);inc();emit('PUSH AF',(0xf5,),11)
    emit('AND 24',(0xe6,24),7);jr(0x28,'NoLiterals')
    for _ in range(3):emit('RRCA',(0x0f,),4)
    call(0xec,'ExtendedCode');emit('LD C,A',(0x4f,),4);copy()
    a.label('NoLiterals');emit('POP AF',(0xf1,),10);emit('OR A',(0xb7,),4);absolute(0xf2,'Case0xx','JP P,Case0xx',10)
    emit('CP 192',(0xfe,192),7);jr(0x38,'Case10x');emit('CP 224',(0xfe,224),7);jr(0x30,'MatchLen')
    emit('LD B,(HL)',(0x46,),7);inc();jr(0x18,'ReadOffsetC')
    a.label('Case10x');call(0xcd,'ReadNibble');emit('LD B,A',(0x47,),4);emit('LD A,C',(0x79,),4)
    emit('CP 160',(0xfe,160),7);emit('DEC B',(5,),4);jr(0x18,'RotateB')
    # C holds the token's base. Shared nibble/extra-byte/word lengths retain
    # short legal word escapes; a word encoding supplies no minimum length.
    a.label('ExtendedCode');call(0xcd,'ReadNibble');emit('INC A',(0x3c,),4);jr(0x28,'ExtraByte')
    emit('SUB 241',(0xd6,241),7);emit('ADD A,C',(0x81,),4);ret()
    a.label('ExtraByte');emit('LD A,15',(0x3e,15),7);emit('ADD A,C',(0x81,),4)
    emit('ADD A,(HL)',(0x86,),7);inc();ret(0xd0)
    # Z with carry is exact EOD. At a match, the token AF has already been
    # popped, so remove only ExtendedCode's return then return to the caller.
    # Literal EOD is invalid. Word lengths take the distinct NZ path.
    jr(0x20,'WordLength');emit('POP BC',(0xc1,),10);ret()
    a.label('WordLength');emit('LD A,(HL)',(0x7e,),7);inc();emit('LD B,(HL)',(0x46,),7);inc();ret()
    a.label('ReadNibble');emit('LD C,A',(0x4f,),4)
    a.label('NibbleSkipC');emit('XOR A',(0xaf,),4);emit('EX AF,AF\'',(8,),4);ret(0xf8)
    emit('LD A,(HL)',(0x7e,),7);emit('OR F0',(0xf6,0xf0),7);emit('EX AF,AF\'',(8,),4)
    emit('LD A,(HL)',(0x7e,),7);inc();emit('OR 0F',(0xf6,15),7)
    for _ in range(4):emit('RRCA',(0x0f,),4)
    ret()
    if a.pc>core_limit:raise ValueError('compact LZSA2 exceeds core-limit')
    return [(core,a.resolve())],a.labels,dict(entry='start',variant='small-block',one_shot=True,
        code_bytes=a.pc-core,core_end=a.pc,patched_addresses=[a.labels['offset']+i for i in (0,1)],
        instruction_listing=rows,state_bytes=0,private_stack_bytes=0,
        upstream_commit='15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5',
        upstream_sha256=sha((Path(__file__).parent/'asm/unlzsa2_small.asm').read_bytes()),
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
