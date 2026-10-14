"""Altered LZSA2 fast decoder by spke & uniabis, with bank-local suspension.

Port of asm/unlzsa2_fast.asm (zlib license notice retained there).
Alterations: preserved AF' across suspension, token-boundary yield, byte-exact
EOF without the upstream two-byte overread, preserved fast S/P dispatch.
Not the original decoder. Reuses the installed Fast ZX0 prefix/core regions.
"""
from pathlib import Path
from ._z80 import MiniAssembler
from ._z80 import sha

PREFIX,PREFIX_LIMIT,STACK=0x7c00,0x7d50,0x7be0


def build(*,core=0x8de0,core_limit=0x8ef7,streaming=False,direct_header=False,long_copy=False,near_literals=False,word_state_init=False,
          prefix=PREFIX,prefix_limit=PREFIX_LIMIT,stack=STACK,output_base=0xc000):
    """Generate raw-v2 decode regions, coroutine labels and instruction costs.

    Configure input_pointer, block_end and slice_target, then call begin or
    slice_until. The output address must not wrap; targets are minimums checked
    between tokens. Writable operands hold the last offset and target. AF'
    contains the shared nibble reservoir and is saved across suspension.
    Caller SP is restored; AF/BC/DE/HL and AF' may be clobbered on return.
    streaming input waits use input_needed and finished, independently of the
    output target. The application owns page supply and final-input bypass.
    long_copy appends bounded 16-LDI kernels to the core: reserve more core RAM
    explicitly (e.g. core_limit=0x9000). Short tokens retain their old paths.
    near_literals moves the ordinary long-copy literal helper before start,
    removing its trampoline. Streaming and all default profiles stay unchanged.
    word_state_init clears adjacent streaming flags in one word instruction;
    caller/IRQ observers see initialized flags only after instruction completion.
    """
    if direct_header and not streaming:raise ValueError('direct header requires streaming input')
    if near_literals and (not long_copy or streaming):
        raise ValueError('near literals require ordinary long-copy input')
    if word_state_init and not streaming:raise ValueError('word state init requires streaming input')
    if not (0<=core<core_limit<=65536 and 0<=prefix<prefix_limit<=65536):
        raise ValueError('invalid code reservations')
    if not (core_limit<=prefix or prefix_limit<=core):raise ValueError('code reservations overlap')
    if not 0<stack<=65535 or not 0<=output_base<65535:raise ValueError('invalid stack/output address')
    cold=MiniAssembler(prefix);a=MiniAssembler(core);rows=[]
    def emit(name,code,t):rows.append(dict(address=a.pc,instruction=name,tstates=t));a.emit(*code)
    def ld(name,op,target,t):
        rows.append(dict(address=a.pc,instruction=name,tstates=t));a.abs16(op,target)
    def jp(op,target):ld('JP '+target,op,target,10)
    def jr(op,target):
        rows.append(dict(address=a.pc,instruction='JR '+target,tstates=12 if op==0x18 else [7,12]));a.rel8(op,target)
    def x():emit('EX AF,AF\'',(8,),4)
    def inc():emit('INC HL',(0x23,),6)
    def ldir():emit('LDIR',(0xed,0xb0),[16,21])
    def ldi():emit('LDI',(0xed,0xa0),16)
    def nibble(label,scf=False):
        if scf:emit('SCF',(0x37,),4)
        x();jr(0x30,label)
        emit('LD A,(HL)',(0x7e,),7);emit('OR A',(0xb7,),4);x()
        emit('LD A,(HL)',(0x7e,),7);inc()
        for _ in range(4):emit('RRCA',(0x0f,),4)
        a.label(label);emit('OR F0h',(0xf6,0xf0),7)
    def long_literals():
        # A=count/B=token, count 18..255; BC entry requires readable literals.
        # Sixteen LDIs leave positive BC and preserve forward overlap/AF'.
        a.label('LongLiterals8');emit('LD C,A',(0x4f,),4);emit('LD A,B',(0x78,),4);emit('LD B,0',(6,0),7)
        a.label('LongLiteralsBC')
        for _ in range(16):ldi()
        ldir();jp(0xc3,'AfterLongLiterals')
    if near_literals:
        # Both helper and ManyLiterals are now within one relative jump.
        # Its untaken 7-T word path is unchanged; eligible byte forms avoid
        # the former 10-T/three-byte trampoline. begin enters start directly.
        long_literals()
    elif long_copy and not streaming:
        # Preserve the original JR's 7-T untaken word-length path. A nearby
        # trampoline adds 10 T only to the eligible long8 literal path.
        a.label('LongLiterals8Jump');jp(0xc3,'LongLiterals8')
    a.label('start');emit('LD B,0',(6,0),7);emit('SCF',(0x37,),4);x();jp(0xc3,'ReadToken')
    a.label('ManyLiterals');emit('LD A,18',(0x3e,18),7);emit('ADD A,(HL)',(0x86,),7);inc()
    if streaming:a.labels['long8_target']=a.pc+1;jp(0xd2,'guard_long8')
    elif long_copy:jr(0x30,'LongLiterals8' if near_literals else 'LongLiterals8Jump')
    else:jr(0x30,'CopyMoreLiterals')
    emit('LD C,(HL)',(0x4e,),7);inc();emit('LD A,B',(0x78,),4);emit('LD B,(HL)',(0x46,),7)
    if streaming:a.labels['long16_target']=a.pc+1
    jp(0xc3,'guard_long16' if streaming else 'NextUseBC')
    a.label('MoreLiterals');emit('LD B,(HL)',(0x46,),7);inc();nibble('LiteralNibble',True)
    emit('INC A',(0x3c,),4);jr(0x28,'ManyLiterals');emit('SUB 238',(0xd6,238),7)
    a.label('CopyMoreLiterals');emit('LD C,A',(0x4f,),4);emit('LD A,B',(0x78,),4);emit('LD B,0',(6,0),7)
    if streaming:a.label('copy_long8')
    ldi();ldi();ldir()
    if long_copy:a.label('AfterLongLiterals')
    emit('OR A',(0xb7,),4);jp(0xf2,'Case0xx')
    emit('CP 192',(0xfe,192),7);jr(0x38,'Case10x')
    a.label('Case11x');emit('CP 224',(0xfe,224),7);jr(0x30,'MatchLen')
    emit('LD B,(HL)',(0x46,),7);inc();jr(0x18,'ReadOffsetC')
    a.label('Literals00or11');jr(0x20,'MoreLiterals')
    a.label('NoLiterals');emit('OR (HL)',(0xb6,),7);inc();jp(0xfa,'Case1xx')
    a.label('Case0xx');emit('CP 64',(0xfe,64),7);jr(0x38,'Case00x')
    emit('DEC B',(5,),4);emit('CP 96',(0xfe,96),7);emit('RL B',(0xcb,0x10),8)
    a.label('ReadOffsetC');emit('LD C,(HL)',(0x4e,),7);inc()
    a.label('SaveOffset');ld('LD (offset),BC',(0xed,0x43),'offset',20);emit('LD B,0',(6,0),7)
    a.label('MatchLen');emit('INC A',(0x3c,),4);emit('AND 7',(0xe6,7),7);jr(0x28,'LongerMatch');emit('INC A',(0x3c,),4)
    a.label('CopyMatch');emit('LD C,A',(0x4f,),4)
    a.label('MatchUseC');emit('PUSH HL',(0xe5,),11);a.labels['offset']=a.pc+1;emit('LD HL,offset',(0x21,0,0),10)
    emit('ADD HL,DE',(0x19,),11);ldi();ldir()
    if long_copy:a.label('AfterLongMatch')
    emit('POP HL',(0xe1,),10)
    a.label('ReadToken');emit('LD A,D',(0x7a,),4);a.labels['high_operand']=a.pc+1;emit('CP high',(0xfe,0),7)
    if streaming:a.labels['token_high_target']=a.pc+1
    jp(0xda,'guard_header' if direct_header else 'Token')
    jr(0x20,'Yield');emit('LD A,E',(0x7b,),4);a.labels['low_operand']=a.pc+1;emit('CP low',(0xfe,0),7)
    if streaming:a.labels['token_low_target']=a.pc+1
    jp(0xda,'guard_header' if direct_header else 'Token')
    a.label('Yield');ld('LD A,(block_end+1)',0x3a,'block_end_high',13);emit('CP D',(0xba,),4);jr(0x20,'Suspend')
    ld('LD A,(block_end)',0x3a,'block_end',13);emit('CP E',(0xbb,),4)
    if streaming:a.labels['token_end_target']=a.pc+1
    jp(0xca,'guard_header' if direct_header else 'Token')
    a.label('Suspend');ld('CALL yield',0xcd,'slice_yield',17);jr(0x18,'ReadToken')
    # AND 24 has even parity for LL=00/11 and odd parity for LL=01/10.
    a.label('Token')
    if streaming and not direct_header:ld('CALL guard_header',0xcd,'guard_header',17)
    a.label('token_body')
    emit('LD A,(HL)',(0x7e,),7);emit('AND 24',(0xe6,24),7);jp(0xea,'Literals00or11')
    for _ in range(3):emit('RRCA',(0x0f,),4)
    emit('LD C,A',(0x4f,),4);emit('LD A,(HL)',(0x7e,),7)
    a.label('NextUseBC');inc()
    if streaming:a.label('copy_long16')
    ldir();emit('OR A',(0xb7,),4);jp(0xf2,'Case0xx')
    a.label('Case1xx');emit('CP 192',(0xfe,192),7);jp(0xd2,'Case11x')
    a.label('Case10x');emit('LD C,A',(0x4f,),4);nibble('Offset13Nibble')
    emit('LD B,A',(0x47,),4);emit('LD A,C',(0x79,),4);emit('CP 160',(0xfe,160),7);emit('DEC B',(5,),4);emit('RL B',(0xcb,0x10),8);jp(0xc3,'ReadOffsetC')
    a.label('Case00x');emit('LD B,A',(0x47,),4);nibble('Offset5Nibble')
    emit('LD C,A',(0x4f,),4);emit('LD A,B',(0x78,),4);emit('CP 32',(0xfe,32),7);emit('RL C',(0xcb,0x11),8);emit('LD B,255',(6,255),7);jp(0xc3,'SaveOffset')
    a.label('LongerMatch');nibble('MatchNibble',True);emit('SUB 231',(0xd6,231),7);emit('CP 24',(0xfe,24),7);jp(0xda,'CopyMatch')
    emit('ADD A,(HL)',(0x86,),7);inc();jp(0xd2,'LongMatch8' if long_copy else 'CopyMatch');emit('RET Z',(0xc8,),[5,11])
    emit('LD C,(HL)',(0x4e,),7);inc();emit('LD B,(HL)',(0x46,),7);inc();jp(0xc3,'MatchUseC')
    if long_copy:
        # Only structurally long forms reach these kernels: literals >=18,
        # extra-byte matches >=24. Escaped 16-bit lengths need not be >=256:
        # retain their original paths even for short noncanonical encodings.
        # Sixteen forward LDIs leave a positive BC for LDIR and preserve overlap at
        # distance 1/2. No count test, AF' scratch or SP redirection is needed.
        # Literal entry: A=count/B=token, count 18..255. Guards call the BC
        # entry only after the entire extent is readable. Word-length guards
        # must keep their original zero-prefix LDIR continuation.
        if not near_literals:long_literals()
        # Match entry: A=count/B=0 or BC=count; DE=next output, HL=input.
        # The shared self-modified offset is loaded as data, costing 6 T more
        # than the short path's immediate load but avoiding another store on
        # every offset token. The existing POP HL restores the continuation.
        a.label('LongMatch8');emit('LD C,A',(0x4f,),4)
        a.label('LongMatchBC');emit('PUSH HL',(0xe5,),11)
        ld('LD HL,(offset)',0x2a,'offset',16);emit('ADD HL,DE',(0x19,),11)
        for _ in range(16):ldi()
        ldir();jp(0xc3,'AfterLongMatch')
        if streaming:
            a.labels['long8_complete']=a.labels['LongLiterals8']
    # Output-only suspension and unavailable-input suspension have different
    # completion rules. Keep the private continuation until raw EOD is read.
    cold.label('slice_until')
    if streaming:
        cold.abs16(0x3a,'finished');cold.emit(0xb7,0xc0)
    cold.abs16(0xcd,'sync')
    if not streaming:
        cold.abs16(0x2a,'slice_output');cold.abs16((0xed,0x5b),'slice_target')
        cold.emit(0xb7,0xed,0x52,0xd0)
    cold.abs16((0xed,0x73),'slice_caller_sp');cold.abs16((0xed,0x7b),'slice_decoder_sp')
    cold.emit(0xe1,0xd1,0xc1,8,0xf1,8,0xf1,0xc9)
    cold.label('begin');cold.abs16(0xcd,'sync');cold.abs16((0xed,0x73),'slice_caller_sp')
    if streaming:
        if word_state_init:
            # HL is overwritten by the finish/input loads below; start's SCF
            # initializes the nibble reservoir irrespective of dead A/flags.
            # Both fields are contiguous and IRQs occur after the word store.
            cold.emit(0x21,0,0);cold.abs16(0x22,'input_needed')
        else:
            cold.emit(0xaf);cold.abs16(0x32,'finished');cold.abs16(0x32,'input_needed')
    cold.emit(0x31);cold.word(stack);cold.abs16(0x21,'finish' if streaming else 'finished');cold.emit(0xe5)
    cold.abs16(0x2a,'input_pointer');cold.emit(0x11);cold.word(output_base);cold.abs16(0xc3,'start')
    cold.label('finish' if streaming else 'finished');cold.abs16(0x2a,'block_end');cold.emit(0xb7,0xed,0x52);cold.abs16(0xc2,'fatal')
    if streaming:
        cold.emit(0x3e,1);cold.abs16(0x32,'finished')
    cold.abs16((0xed,0x53),'slice_output');cold.abs16((0xed,0x7b),'slice_caller_sp');cold.emit(0xc9)
    cold.label('slice_yield');cold.abs16((0xed,0x53),'slice_output');cold.emit(0xf5,8,0xf5,8,0xc5,0xd5,0xe5)
    cold.abs16((0xed,0x73),'slice_decoder_sp');cold.abs16((0xed,0x7b),'slice_caller_sp');cold.emit(0xc9)
    cold.label('sync');cold.abs16(0x2a,'slice_target');cold.abs16((0xed,0x5b),'block_end');cold.emit(0xb7,0xed,0x52)
    cold.abs16(0x2a,'slice_target');cold.rel8(0x20,'sync_target');cold.emit(0x21,0xff,0xff)
    cold.label('sync_target');cold.emit(0x7c);cold.abs16(0x32,'high_operand');cold.emit(0x7d);cold.abs16(0x32,'low_operand');cold.emit(0xc9)
    cold.label('fatal');cold.emit(0x76)
    if streaming:
        # A 32-byte token prefix covers <=17 literals, their <=2-byte header,
        # <=2 offset bytes and <=4 match-length bytes (25 total). Longer
        # literals take separate guarded continuations, preserving the fast
        # normal path. The input wrapper patches both guard entries to RET
        # once the final sector and shared carry have been saved.
        cold.label('guard_header')
        if not direct_header:cold.label('header_patch');cold.emit(0xf5)
        cold.emit(0x7d,0xc6,31,0x7c,0xce,0)
        cold.rel8(0x38,'header_short');cold.emit(0xfe);cold.label('header_frontier');cold.emit(0)
        if direct_header:
            # AF is dead at token entry: LD A,(HL)/AND replaces it. AF' holds
            # the nibble reservoir and is left untouched. Re-enter ReadToken
            # after input_wait so a newly complete block bypasses the guard.
            cold.abs16(0xda,'token_body');cold.label('header_short')
            cold.abs16(0xcd,'input_wait');cold.abs16(0xc3,'ReadToken')
        else:
            cold.rel8(0x38,'header_ready')
            cold.label('header_short');cold.emit(0xf1);cold.abs16(0xcd,'input_wait');cold.rel8(0x18,'guard_header')
            cold.label('header_ready');cold.emit(0xf1,0xc9)
        cold.label('guard_long8');cold.emit(0x4f,0x78,0x06,0)
        cold.abs16(0xcd,'guard_literals');cold.abs16(0xc3,'LongLiteralsBC' if long_copy else 'copy_long8')
        cold.label('guard_long16');cold.emit(0x23)
        cold.abs16(0xcd,'guard_literals');cold.abs16(0xc3,'copy_long16')
        cold.label('guard_literals');cold.emit(0xf5,0xe5,0x09);cold.rel8(0x38,'literal_short')
        cold.emit(0x7d,0xc6,7,0x7c,0xce,0);cold.rel8(0x38,'literal_short')
        cold.emit(0xfe);cold.label('literal_frontier');cold.emit(0);cold.rel8(0x38,'literal_ready')
        cold.label('literal_short');cold.emit(0xe1,0xf1);cold.abs16(0xcd,'input_wait');cold.rel8(0x18,'guard_literals')
        cold.label('literal_ready');cold.emit(0xe1,0xf1,0xc9)
        cold.label('input_wait');cold.emit(0xf5,0x3e,1);cold.abs16(0x32,'input_needed')
        cold.abs16(0xcd,'slice_yield');cold.emit(0xaf);cold.abs16(0x32,'input_needed');cold.emit(0xf1,0xc9)
    cold.label('state')
    for label in ('slice_output','slice_target','slice_caller_sp','slice_decoder_sp','block_length','block_end','input_pointer'):
        cold.label(label);cold.word(0)
    cold.label('block_stored');cold.emit(0)
    if streaming:
        for label in ('input_high','all_loaded','input_needed','finished'):cold.label(label);cold.emit(0)
    cold.label('end')
    labels=cold.labels|a.labels;labels['block_end_high']=labels['block_end']+1
    if streaming:labels['token_guard']=labels['guard_header'] if direct_header else labels['Token']
    if a.pc>core_limit or cold.pc>prefix_limit:raise ValueError(('LZSA2 does not fit',hex(a.pc),hex(cold.pc)))
    regions=[(prefix,cold.resolve(labels)),(core,a.resolve(labels))]
    # Fixed cold-wrapper timings from Zilog UM0080; data starts at state.
    cold_ops={0xcd:('CALL nn',3,17),0xc3:('JP nn',3,10),0xc2:('JP NZ,nn',3,10),0xda:('JP C,nn',3,10),
        0x2a:('LD HL,(nn)',3,16),0x22:('LD (nn),HL',3,16),0x21:('LD HL,nn',3,10),0x11:('LD DE,nn',3,10),
        0x31:('LD SP,nn',3,10),0x32:('LD (nn),A',3,13),0xb7:('OR A',1,4),
        0xd0:('RET NC',1,[5,11]),0xc9:('RET',1,10),0x20:('JR NZ,e',2,[7,12]),
        8:("EX AF,AF'",1,4),0x7c:('LD A,H',1,4),0x7d:('LD A,L',1,4),0x76:('HALT',1,4),
        0xaf:('XOR A',1,4),0x3e:('LD A,n',2,7),0x01:('LD BC,nn',3,10),0x3a:('LD A,(nn)',3,13),
        0x19:('ADD HL,DE',1,11),0x09:('ADD HL,BC',1,11),0xbc:('CP H',1,4),
        0x38:('JR C,e',2,[7,12]),0x28:('JR Z,e',2,[7,12]),0x18:('JR e',2,12),0xc0:('RET NZ',1,[5,11]),
        0xc6:('ADD A,n',2,7),0xce:('ADC A,n',2,7),0x4f:('LD C,A',1,4),0x78:('LD A,B',1,4),
        0x06:('LD B,n',2,7),0x23:('INC HL',1,6),0xfe:('CP n',2,7)}
    for op,pair in ((0xc5,'BC'),(0xd5,'DE'),(0xe5,'HL'),(0xf5,'AF')):
        cold_ops[op]=('PUSH '+pair,1,11);cold_ops[op-4]=('POP '+pair,1,10)
    code=regions[0][1];pos=0
    while prefix+pos<labels['state']:
        if code[pos]==0xed:
            q=code[pos+1]
            if q==0x52:name,size,t='SBC HL,DE',2,15
            else:
                name={0x5b:'LD DE,(nn)',0x53:'LD (nn),DE',0x73:'LD (nn),SP',0x7b:'LD SP,(nn)'}[q]
                size,t=4,20
        else:name,size,t=cold_ops[code[pos]]
        rows.append(dict(address=prefix+pos,instruction=name,tstates=t));pos+=size
    if streaming:
        for row in rows:
            if row['address'] in ([labels['header_patch']] if 'header_patch' in labels else [])+[labels['guard_literals']]:
                row.update(instruction='PUSH AF / RET when all input loaded',tstates=[10,11])
    return regions,labels,dict(prefix_end=cold.pc,core_end=a.pc,code_bytes=sum(len(b) for _,b in regions),
        output_base=output_base,private_stack=stack,
        patched_addresses=[labels[k] for k in ('high_operand','low_operand','offset')]+[labels['offset']+1]
            +([labels[k] for k in (('header_patch',) if 'header_patch' in labels else ())+('guard_literals','header_frontier','literal_frontier')]
              +[labels[k]+i for k in ('token_high_target','token_low_target','token_end_target','long8_target','long16_target') for i in (0,1)]
              if streaming else []),
        instruction_listing=rows,**(dict(direct_header_guard=True,available_header_tstates=46,
            previous_available_header_tstates=96,available_header_delta_tstates=-50) if direct_header else {}),
        upstream_commit='15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5',
        **(dict(long_copy=True,long_copy_minimum_literals=18,long_copy_minimum_match=24,
            long_copy_unrolled_bytes=16,long_copy_16bit_forms=False,
            long_copy_extra_core_bytes=84 if streaming or near_literals else 87,
            long_copy_delta_tstates=dict(literals8=-60 if streaming or near_literals else -50,
                literals16=0,guarded_literals16=0,matches8=-59,matches16=0)) if long_copy else {}),
        **(dict(near_literals=True,near_literal_delta_tstates=-10,near_literal_code_delta=-3) if near_literals else {}),
        **(dict(word_state_init=True,begin_init_tstates_before=30,begin_init_tstates_after=26,
                begin_init_code_delta=-1) if word_state_init else {}),
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        upstream_sha256=sha((Path(__file__).parent/'asm/unlzsa2_fast.asm').read_bytes()))
