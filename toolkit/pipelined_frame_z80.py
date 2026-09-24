"""One compact frame of lookahead, with native screen publication in IM2.

The compact state and packet window are reused only after native drawing.
The IRQ owns screen selection; foreground bank changes merge its latest bit
3 inside a short DI section. AY runs after publication. No new frame buffer,
compressed bytes or disk-ring allocation is introduced.
"""
from build_zxv_trd import MiniAssembler

CODE, VIDEO, PAGE, STATE = 0xde00, 0x9600, 0x9780, 0x97c0
READY, ENABLED, DEADLINE, LATE, PUBLISHED, SHADOW = range(STATE,STATE+12,2)
STATE_END = STATE+12


def helpers(a,listing,phase):
    def emit(name,data,ticks):
        listing.append(dict(address=a.pc,instruction=name,tstates=ticks,phase=phase)); a.emit(*data)
    def addr(name,opcode,value,ticks):
        listing.append(dict(address=a.pc,instruction=name,tstates=ticks,phase=phase))
        if isinstance(value,str): a.abs16(opcode,value)
        else: a.emit(*(opcode if isinstance(opcode,tuple) else (opcode,))); a.word(value)
    return emit,addr


def build_video(draw,zx0,audio):
    listing=[]; a=MiniAssembler(VIDEO); emit,addr=helpers(a,listing,'video_irq')
    a.label('video_tick')
    emit('PUSH AF',[0xf5],11)
    addr('LD A,(enabled)',0x3a,ENABLED,13); emit('OR A',[0xb7],4)
    addr('JP Z,done_af',0xca,'done_af',10)
    addr('LD A,(ready)',0x3a,READY,13); emit('OR A',[0xb7],4)
    addr('JP Z,done_af',0xca,'done_af',10)
    emit('PUSH DE',[0xd5],11)
    addr('LD HL,(elapsed_fields)',0x2a,audio['elapsed_fields'],16)
    addr('LD DE,(deadline)',(0xed,0x5b),DEADLINE,20)
    emit('OR A',[0xb7],4); emit('SBC HL,DE',[0xed,0x52],15)
    emit('BIT 7,H (signed deadline difference)',[0xcb,0x7c],8)
    addr('JP NZ,not_due',0xc2,'not_due',10)
    addr('LD (late_fields),HL',0x22,LATE,16)
    emit('PUSH BC',[0xc5],11)
    addr('LD A,(page_shadow)',0x3a,SHADOW,13); emit('XOR 8',[0xee,8],7)
    addr('LD (page_shadow),A',0x32,SHADOW,13)
    addr('LD BC,7FFD',0x01,0x7ffd,10)
    a.label('publish_out'); emit('OUT (C),A',[0xed,0x79],12)
    for name,location,mask in (('saved_page',draw['saved_page'],8),
            ('history_page',zx0['history_page'],8),('screen_base',draw['screen_base'],128)):
        addr('LD A,('+name+')',0x3a,location,13); emit('XOR mask',[0xee,mask],7)
        addr('LD ('+name+'),A',0x32,location,13)
    emit('XOR A',[0xaf],4); addr('LD (ready),A',0x32,READY,13)
    addr('LD HL,(deadline)',0x2a,DEADLINE,16); addr('LD DE,6',0x11,6,10)
    emit('ADD HL,DE',[0x19],11); addr('LD (deadline),HL',0x22,DEADLINE,16)
    addr('LD HL,(published)',0x2a,PUBLISHED,16); emit('INC HL',[0x23],6)
    addr('LD (published),HL',0x22,PUBLISHED,16)
    emit('POP BC',[0xc1],10)
    a.label('not_due'); emit('POP DE',[0xd1],10)
    a.label('done_af'); emit('POP AF',[0xf1],10); emit('RET',[0xc9],10)
    a.label('video_end')
    if a.pc>PAGE: raise ValueError('video ISR overlaps atomic paging')
    regions=[(VIDEO,a.resolve())]; labels=dict(a.labels)
    a=MiniAssembler(PAGE); emit,addr=helpers(a,listing,'paging')
    a.label('atomic_page')
    # Input A=requested page. BC and AF may be clobbered, like these callers
    # already permit. Startup callers must have installed the IM2 handler.
    # EI is intentional: all runtime paging sites permit interrupts on return.
    emit('DI',[0xf3],4); emit('AND F7h',[0xe6,0xf7],7); emit('LD B,A',[0x47],4)
    addr('LD A,(page_shadow)',0x3a,SHADOW,13); emit('AND 8',[0xe6,8],7)
    emit('OR B',[0xb0],4); addr('LD (page_shadow),A',0x32,SHADOW,13)
    addr('LD BC,7FFD',0x01,0x7ffd,10); emit('OUT (C),A',[0xed,0x79],12)
    emit('EI',[0xfb],4); emit('RET',[0xc9],10)
    a.label('page_end')
    if a.pc>STATE: raise ValueError('atomic paging overlaps state')
    regions.append((PAGE,a.resolve())); labels.update(a.labels)
    state=bytearray(STATE_END-STATE); state[SHADOW-STATE]=0x17
    regions.append((STATE,bytes(state)))
    labels.update(ready=READY,enabled=ENABLED,deadline=DEADLINE,late_fields=LATE,
        published=PUBLISHED,page_shadow=SHADOW,state=STATE,end=STATE_END)
    return regions,labels,listing


def build_clock(packet,audio,frames,*,zx0,progress_entry=None,lookahead=False,packet_ahead=False,disk_idle_entry=None,disk_due_entry=None):
    if not 1<=frames<=10922: raise ValueError('six AY ticks per frame must fit u16')
    a=MiniAssembler(CODE); listing=[]; emit,addr=helpers(a,listing,'schedule')
    a.label('prime')
    addr('CALL compact zero',0xcd,packet['next_frame'],17)
    addr('CALL native zero',0xcd,packet['draw_bridge'],17)
    emit('LD A,1',[0x3e,1],7); addr('LD (ready),A',0x32,READY,13)
    if frames>1: addr('CALL compact one',0xcd,packet['next_frame'],17)
    if packet_ahead and frames>2: addr('CALL read packet two',0xcd,packet['read_packet'],17)
    emit('RET',[0xc9],10)
    a.label('start')
    emit('DI',[0xf3],4)
    addr('LD HL,(elapsed_fields)',0x2a,audio['elapsed_fields'],16)
    emit('INC HL',[0x23],6); addr('LD (deadline),HL',0x22,DEADLINE,16)
    emit('LD A,1',[0x3e,1],7)
    addr('LD (video_enabled),A',0x32,ENABLED,13)
    addr('LD (audio_enabled),A',0x32,audio['audio_enabled'],13)
    emit('EI',[0xfb],4)
    addr('JP wait_published',0xc3,'wait_published',10)
    a.label('play_one')
    addr('LD HL,(remaining)',0x2a,'remaining',16)
    emit('LD A,H',[0x7c],4); emit('OR L',[0xb5],4); emit('RET Z',[0xc8],[5,11])
    addr('CALL draw_compact',0xcd,packet['draw_bridge'],17)
    emit('LD A,1',[0x3e,1],7); addr('LD (ready),A',0x32,READY,13)
    addr('LD HL,(remaining)',0x2a,'remaining',16); emit('DEC HL',[0x2b],6)
    addr('LD (remaining),HL',0x22,'remaining',16)
    emit('LD A,H',[0x7c],4); emit('OR L',[0xb5],4)
    if packet_ahead:
        addr('JP Z,wait_published',0xca,'wait_published',10)
        if packet_ahead=='idle':
            addr('LD A,(packet_pending)',0x3a,'packet_pending',13); emit('OR A',[0xb7],4)
            addr('CALL Z,read required packet',0xcc,packet['read_packet'],[10,17])
        addr('CALL reconstruct pending packet',0xcd,packet['prepare_bridge'],17)
        if packet_ahead=='idle':
            emit('XOR A',[0xaf],4); addr('LD (packet_pending),A',0x32,'packet_pending',13)
        addr('LD HL,(remaining)',0x2a,'remaining',16); emit('DEC HL',[0x2b],6)
        emit('LD A,H',[0x7c],4); emit('OR L',[0xb5],4)
        if packet_ahead=='idle':
            addr('JP Z,wait_published',0xca,'wait_published',10)
            # Once the preceding screen has been published, drawing the ready
            # compact frame takes priority over optional input acquisition.
            addr('LD A,(ready)',0x3a,READY,13); emit('OR A',[0xb7],4)
            addr('JP Z,wait_published',0xca,'wait_published',10)
            addr('CALL read next packet',0xcd,packet['read_packet'],17)
            emit('LD A,1',[0x3e,1],7); addr('LD (packet_pending),A',0x32,'packet_pending',13)
        else:
            addr('CALL NZ,read next packet',0xc4,packet['read_packet'],[10,17])
    else:
        addr('CALL NZ,prepare next compact',0xc4,packet['next_frame'],[10,17])
    a.label('wait_published')
    addr('LD A,(ready)',0x3a,READY,13); emit('OR A',[0xb7],4)
    addr('JP Z,published',0xca,'published',10)
    if disk_idle_entry is not None:
        addr('CALL idle disk read',0xcd,disk_idle_entry,17); emit('OR A',[0xb7],4)
        addr('JP NZ,wait_published',0xc2,'wait_published',10)
    if lookahead:
        addr('CALL ahead',0xcd,'ahead',17); emit('OR A',[0xb7],4)
        addr('JP NZ,wait_published',0xc2,'wait_published',10)
        # The IRQ may have published during ahead; do not HALT for an extra
        # field before drawing the next frame or reporting this publication.
        addr('LD A,(ready)',0x3a,READY,13); emit('OR A',[0xb7],4)
        addr('JP Z,published',0xca,'published',10)
    emit('EI',[0xfb],4); emit('HALT',[0x76],4)
    addr('JP wait_published',0xc3,'wait_published',10)
    a.label('published')
    if progress_entry is not None: addr('CALL disk_progress',0xcd,progress_entry,17)
    if disk_due_entry is not None: addr('CALL timed disk service',0xcd,disk_due_entry,17)
    emit('RET',[0xc9],10)
    if lookahead:
        # Publication is now interruptible inside ZX0. This minimum quantum
        # bounds how long drawing may wait after a publication, not IRQ time.
        a.label('ahead')
        addr('LD HL,(slice_output)',0x2a,zx0['slice_output'],16)
        addr('LD DE,2000',0x11,8192,10); emit('ADD HL,DE',[0x19],11)
        addr('LD DE,(block_length)',(0xed,0x5b),zx0['block_length'],20)
        emit('OR A',[0xb7],4); emit('SBC HL,DE',[0xed,0x52],15)
        addr('JP Z,ahead_done',0xca,'ahead_done',10)
        emit('ADD HL,DE',[0x19],11)
        addr('LD DE,256',0x11,256,10); emit('ADD HL,DE',[0x19],11)
        addr('LD DE,(block_length)',(0xed,0x5b),zx0['block_length'],20)
        emit('OR A',[0xb7],4); emit('SBC HL,DE',[0xed,0x52],15)
        addr('JP C,ahead_fits',0xda,'ahead_fits',10)
        emit('EX DE,HL',[0xeb],4); addr('JP ahead_target',0xc3,'ahead_target',10)
        a.label('ahead_fits'); emit('ADD HL,DE',[0x19],11)
        a.label('ahead_target')
        addr('LD DE,E000',0x11,0xe000,10); emit('ADD HL,DE',[0x19],11)
        addr('LD (slice_target),HL',0x22,zx0['slice_target'],16)
        addr('CALL slice_until',0xcd,zx0['slice_until'],17)
        emit('LD A,1',[0x3e,1],7); emit('RET',[0xc9],10)
        a.label('ahead_done'); emit('XOR A',[0xaf],4); emit('RET',[0xc9],10)
    a.label('state'); a.label('remaining'); a.word(frames-1)
    if packet_ahead=='idle': a.label('packet_pending'); a.emit(int(frames>2))
    a.label('end')
    if a.pc>0xe000: raise ValueError('pipelined clock overlaps ZX0 history')
    return a.resolve(),dict(a.labels),listing
