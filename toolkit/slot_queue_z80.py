"""Four bank-local ZX0 slots, with a packet consumer and bounded producer.

All public entries require bank 7 mapped and restore it before returning.
step performs one sector operation or one ZX0 quantum, never both. Completed
slots are released only after take has copied their last byte. IRQ owns the
screen bit. The former bank-7 ZX0 history now holds queue code and state.
demand_decode lets take wait for its whole required prefix before copying;
background step retains its configured quantum. History stays until EOF.
"""
from build_zxv_trd import MiniAssembler
from pipelined_frame_z80 import helpers, PAGE

CODE, BRIDGE, LIMIT = 0xe000, 0x6100, 0xf000
DEMAND, DEMAND_LIMIT = 0xe200, 0xe300


def build(z, p, blocks, *, quantum=256, partial_consumption=False, demand_decode=False):
    if not 1 <= blocks <= 65535 or not 1 <= quantum <= 8192:
        raise ValueError('invalid block count or decode quantum')
    partial_consumption = partial_consumption or demand_decode
    rows=[]
    a=MiniAssembler(BRIDGE);e,n=helpers(a,rows,'slot_bridge')
    def call(target):n('CALL '+str(target),0xcd,target,17)
    def jump(target):n('JP '+str(target),0xc3,target,10)
    def ret():e('RET',[0xc9],10)
    a.label('begin_input');call(p['begin']);jump('restore')
    a.label('input_step');call(p['step']);jump('restore')
    a.label('begin_decode');call(p['page_slot']);call(z['begin']);jump('restore')
    a.label('decode_step');call(p['page_slot']);call(z['slice_until']);jump('restore')
    a.label('copy')
    # A=region, HL=source, DE=destination, BC=count>0. Paging clobbers BC.
    e('PUSH BC',[0xc5],11);e('CP 2',[0xfe,2],7);n('JP C,copy_page',0xda,'copy_page',10)
    e('INC A',[0x3c],4)
    a.label('copy_page');e('OR 10h',[0xf6,0x10],7);call(PAGE);e('POP BC',[0xc1],10)
    e('LD A,C',[0x79],4);e('NEG',[0xed,0x44],8);e('AND 31',[0xe6,31],7);e('ADD A,A',[0x87],4)
    n('LD (copy_jump_operand),A',0x32,'copy_jump_operand',13)
    e('JR partial group',[0x18,0],12);a.labels['copy_jump_operand']=a.pc-1
    a.label('copy_group')
    for _ in range(32):e('LDI',[0xed,0xa0],16)
    e('LD A,B',[0x78],4);e('OR C',[0xb1],4);n('JP NZ,copy_group',0xc2,'copy_group',10)
    a.label('restore');e('PUSH AF',[0xf5],11);e('LD A,17h',[0x3e,0x17],7);call(PAGE)
    e('POP AF',[0xf1],10);ret()
    a.label('end');bridge=a.resolve();b=dict(a.labels)
    if a.pc>0x6200:raise ValueError('queue bridge overlaps next-disk prompt')

    a=MiniAssembler(CODE);e,n=helpers(a,rows,'slot_queue')
    def load(name):n('LD A,('+name+')',0x3a,name,13)
    def store(name):n('LD ('+name+'),A',0x32,name,13)
    def wl(name):n('LD HL,('+str(name)+')',0x2a,name,16)
    def ws(name):n('LD ('+str(name)+'),HL',0x22,name,16)
    def j(op,target):n('JP '+str(target),op,target,10)
    a.label('prefill');call('step');e('OR A',[0xb7],4);j(0xc2,'prefill');ret()
    a.label('step')
    load('phase');e('OR A',[0xb7],4);j(0xc2,'active')
    load('count');e('CP 4',[0xfe,4],7);j(0xca,'idle')
    wl('blocks_left');e('LD A,H',[0x7c],4);e('OR L',[0xb5],4);j(0xca,'idle')
    load('write_slot');call(b['begin_input']);e('LD A,1',[0x3e,1],7);store('phase');j(0xc3,'worked')
    a.label('active');e('CP 1',[0xfe,1],7);j(0xc2,'decode')
    call(b['input_step']);e('OR A',[0xb7],4);j(0xca,'worked')
    # Starting at zero output suspends before the first literal; no full
    # block reconstruction is hidden in the final input operation.
    n('LD HL,E000',0x21,0xe000,10);ws(z['slice_target']);call(b['begin_decode'])
    e('LD A,2',[0x3e,2],7);store('phase');j(0xc3,'worked')
    a.label('decode');wl(z['slice_output']);n('LD DE,2000',0x11,8192,10);e('ADD HL,DE',[0x19],11)
    n('LD DE,quantum',0x11,quantum,10);e('ADD HL,DE',[0x19],11)
    n('LD DE,(block_length)',(0xed,0x5b),z['block_length'],20);e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15)
    j(0xda,'quota_fits');e('EX DE,HL',[0xeb],4);j(0xc3,'quota')
    a.label('quota_fits');e('ADD HL,DE',[0x19],11)
    a.label('quota');n('LD DE,E000',0x11,0xe000,10);e('ADD HL,DE',[0x19],11);ws(z['slice_target'])
    a.label('run_decode')
    call(b['decode_step'])
    wl(z['slice_output']);n('LD DE,(block_end)',(0xed,0x5b),z['block_end'],20)
    e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15);j(0xc2,'worked')
    # EOF has been reached: publish the descriptor, then advance producer.
    a.label('block_ready');load('write_slot');call('descriptor')
    n('LD DE,(block_length)',(0xed,0x5b),z['block_length'],20)
    e('LD (HL),E',[0x73],7);e('INC HL',[0x23],6);e('LD (HL),D',[0x72],7)
    load('write_slot');e('INC A',[0x3c],4);e('AND 3',[0xe6,3],7);store('write_slot')
    n('LD HL,count',0x21,'count',10);e('INC (HL)',[0x34],11)
    wl('blocks_left');e('DEC HL',[0x2b],6);ws('blocks_left')
    e('XOR A',[0xaf],4);store('phase')
    a.label('worked');e('LD A,1',[0x3e,1],7);ret()
    a.label('idle');e('XOR A',[0xaf],4);ret()
    a.label('descriptor');e('ADD A,A',[0x87],4);e('LD L,A',[0x6f],4);e('LD H,0',[0x26,0],7)
    n('LD DE,lengths',0x11,'lengths',10);e('ADD HL,DE',[0x19],11);ret()

    a.label('take');e('LD A,B',[0x78],4);e('OR C',[0xb1],4);e('RET Z',[0xc8],[5,11])
    n('LD (pending),BC',(0xed,0x43),'pending',20);n('LD (destination),DE',(0xed,0x53),'destination',20)
    a.label('take_next');load('count');e('OR A',[0xb7],4);j(0xc2,'have_slot')
    if demand_decode:
        load('phase');e('CP 2',[0xfe,2],7);j(0xca,'demand')
    elif partial_consumption:
        # With no completed descriptor, read_slot == write_slot. The active
        # decoder retains all history even when its produced prefix is copied.
        # Release this slot only after EOF publishes its complete descriptor.
        load('phase');e('CP 2',[0xfe,2],7);j(0xc2,'need_step')
        wl(z['slice_output']);n('LD DE,E000',0x11,0xe000,10)
        e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15)
        n('LD DE,(position)',(0xed,0x5b),'position',20)
        e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15)
        e('LD A,H',[0x7c],4);e('OR L',[0xb5],4);j(0xc2,'take_available')
        a.label('need_step')
    call('step');e('OR A',[0xb7],4);j(0xca,'fatal');j(0xc3,'take_next')
    a.label('have_slot');load('read_slot');call('descriptor')
    e('LD E,(HL)',[0x5e],7);e('INC HL',[0x23],6);e('LD D,(HL)',[0x56],7)
    wl('position');e('EX DE,HL',[0xeb],4);e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15)
    a.label('take_available')
    n('LD BC,(pending)',(0xed,0x4b),'pending',20);e('PUSH HL',[0xe5],11)
    e('OR A',[0xb7],4);e('SBC HL,BC',[0xed,0x42],15);j(0xd2,'take_fits')
    e('POP BC',[0xc1],10);n('LD HL,0',0x21,0,10);j(0xc3,'take_count')
    a.label('take_fits');e('POP DE',[0xd1],10)
    a.label('take_count');ws('slot_left');n('LD (copy_count),BC',(0xed,0x43),'copy_count',20)
    wl('pending');e('OR A',[0xb7],4);e('SBC HL,BC',[0xed,0x42],15);ws('pending')
    wl('position');e('PUSH HL',[0xe5],11);e('ADD HL,BC',[0x09],11);ws('position');e('POP HL',[0xe1],10)
    n('LD DE,E000',0x11,0xe000,10);e('ADD HL,DE',[0x19],11)
    n('LD DE,(destination)',(0xed,0x5b),'destination',20);load('read_slot');call(b['copy'])
    n('LD (destination),DE',(0xed,0x53),'destination',20)
    wl('slot_left');e('LD A,H',[0x7c],4);e('OR L',[0xb5],4);j(0xc2,'retained')
    if partial_consumption:
        load('count');e('OR A',[0xb7],4);j(0xca,'retained')
    a.label('release');n('LD HL,count',0x21,'count',10);e('DEC (HL)',[0x35],11)
    load('read_slot');e('INC A',[0x3c],4);e('AND 3',[0xe6,3],7);store('read_slot')
    n('LD HL,0',0x21,0,10);ws('position')
    a.label('retained');wl('pending');e('LD A,H',[0x7c],4);e('OR L',[0xb5],4);j(0xc2,'take_next')
    n('LD DE,(destination)',(0xed,0x5b),'destination',20);ret()
    a.label('fatal');e('HALT',[0x76],4)
    a.label('state')
    for name in ('phase','count','write_slot','read_slot'):a.label(name);a.emit(0)
    a.label('blocks_left');a.word(blocks)
    for name in ('position','pending','destination','copy_count','slot_left'):a.label(name);a.word(0)
    a.label('lengths');a.emit(*bytes(8));a.label('end')
    if a.pc>LIMIT:raise ValueError('queue code/state exceeds bank-7 reservation')
    extra=[]
    if demand_decode:
        # Separate gap after compiled-mask initialization and before runtime
        # E300. The original E180 generator must remain available at boot.
        if a.pc>0xe180:raise ValueError('demand queue overlaps compiled-mask initializer')
        main=a;a=MiniAssembler(DEMAND);a.labels.update(main.labels)
        e,n=helpers(a,rows,'slot_queue')
        a.label('demand')
        # Relative target=min(position+pending,block_length); a wide caller
        # request may overflow 16 bits, which must also clamp to block end.
        wl('position');n('LD BC,(pending)',(0xed,0x4b),'pending',20)
        n('LD DE,(block_length)',(0xed,0x5b),z['block_length'],20)
        e('ADD HL,BC',[0x09],11);j(0xda,'demand_full')
        e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15);j(0xda,'demand_fits')
        a.label('demand_full');e('EX DE,HL',[0xeb],4);j(0xc3,'demand_target')
        a.label('demand_fits');e('ADD HL,DE',[0x19],11)
        a.label('demand_target');e('PUSH HL',[0xe5],11)
        # Compare relative positions so absolute output 0000 means 8192,
        # and a target wrapping to 0000 never looks like an already-ready 0.
        n('LD DE,(slice_output)',(0xed,0x5b),z['slice_output'],20)
        e('EX DE,HL',[0xeb],4);n('LD BC,2000',0x01,0x2000,10);e('ADD HL,BC',[0x09],11)
        e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15);j(0xd2,'demand_ready')
        e('POP HL',[0xe1],10);n('LD DE,E000',0x11,0xe000,10);e('ADD HL,DE',[0x19],11)
        ws(z['slice_target']);call('run_decode');j(0xc3,'take_next')
        a.label('demand_ready');e('POP HL',[0xe1],10)
        n('LD DE,(position)',(0xed,0x5b),'position',20)
        e('OR A',[0xb7],4);e('SBC HL,DE',[0xed,0x52],15);j(0xc3,'take_available')
        a.label('demand_end')
        if a.pc>DEMAND_LIMIT:raise ValueError('demand helper overlaps compiled-mask runtime')
        extra=[(DEMAND,a.resolve())];main.labels.update(a.labels);a=main
    return [(BRIDGE,bridge),(CODE,a.resolve())]+extra,dict(a.labels,bridge=b),rows
