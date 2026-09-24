"""Experimental TR-DOS adapter for the measured FAP3 raster pipeline.

The refill hook replaces only fully consumed 256-byte ring sectors. ROM
service time is additional to the instruction listing, never estimated as
zero. Disk calls use a separate fixed-RAM stack, preserving ZX0's alternate
registers and private suspension stack. Optional deferred credits move reads
into idle waits, with forced refill before the loaded ring reserve runs out.
"""
from build_zxv_trd import MiniAssembler
from pipelined_frame_z80 import helpers, PAGE
import zx0_codec

DISK, DRIVER, DISK_STACK = 0x6000, 0xdf20, 0x9c00
WAIT_NEXT, LOAD_NEXT = 0x6200, 0x9a60
CACHED_SEEK = 0x9a90  # after the next-volume loader, before row-low at 9B00
DEFERRED, CONSUME = 0x6100, 0x6140  # installed after bootstrap, before disk prompt
LAST_DISK_FIELDS = 0x61fc
DEFERRED_DUE = 0x611c
TRDOS_503_SHA256='91259fca6a8ded428cc24046f5b48b31d4043f2afbd9087d8946eaf4e10d71a5'


def prompt_bitmap():
    # Original 5x7 lettering, six-pixel pitch, centered in 256 px.
    glyphs = {
        'I': '11111/00100/00100/00100/00100/00100/11111',
        'N': '10001/11001/11001/10101/10011/10011/10001',
        'S': '01111/10000/10000/01110/00001/00001/11110',
        'E': '11111/10000/10000/11110/10000/10000/11111',
        'R': '11110/10001/10001/11110/10100/10010/10001',
        'T': '11111/00100/00100/00100/00100/00100/00100',
        'X': '10001/10001/01010/00100/01010/10001/10001',
        'D': '11110/10001/10001/10001/10001/10001/11110',
        'K': '10001/10010/10100/11000/10100/10010/10001',
        ' ': '00000/00000/00000/00000/00000/00000/00000',
    }
    message='INSERT NEXT DISK'; left=(256-len(message)*6)//2
    output=bytearray(224)
    for i,char in enumerate(message):
        for y,row in enumerate(glyphs[char].split('/')):
            for x,pixel in enumerate(row):
                if pixel=='1':
                    col=left+i*6+x; output[y*32+col//8]|=128>>(col%8)
    return bytes(output)


def packed_sector(linear):
    track, sector = divmod(linear, 16)
    return track * 256 + sector


def emit_interleaved_cursor(a, listing):
    """DE holds physical track/sector, zero based; advance 0,8,1,9,...,15."""
    e,n=helpers(a,listing,'interleaved_cursor')
    e('LD A,E',[0x7b],4); e('XOR 8',[0xee,8],7); e('BIT 3,A',[0xcb,0x5f],8)
    n('JP NZ,advance_value',0xc2,'advance_value',10)
    e('INC A',[0x3c],4); e('CP 8',[0xfe,8],7)
    n('JP NZ,advance_value',0xc2,'advance_value',10)
    e('XOR A',[0xaf],4); e('INC D',[0x14],4)
    a.label('advance_value'); e('LD E,A',[0x5f],4)


def build_disk(next_sector, remaining, *, fast_disk=False, cached_seek=False, initial_track=255, interleaved=False, deferred_limit=0,keepalive_fields=0,elapsed_fields=None):
    if not 0 <= deferred_limit <= 248: raise ValueError('deferred limit must be 0..248 sectors')
    if keepalive_fields and not (1<=keepalive_fields<=100 and deferred_limit and cached_seek and initial_track!=255 and elapsed_fields is not None):
        raise ValueError('keepalive requires deferred cached reads and a field counter')
    if cached_seek and not fast_disk: raise ValueError('cached seek requires fast disk')
    if initial_track!=255 and not (cached_seek and 0<=initial_track<160):
        raise ValueError('initial track requires cached seek and a valid bootstrap track')
    a = MiniAssembler(DISK); listing = []
    e, n = helpers(a, listing, 'disk_adapter')
    a.label('refill')
    if deferred_limit:
        n('JP deferred_consume', 0xc3, CONSUME, 10)
    else:
        n('LD A,(free_high)', 0x3a, 'free_high', 13)
        e('CP H', [0xbc], 4); e('RET Z', [0xc8], [5,11])
        e('LD A,H', [0x7c], 4); n('LD (free_high),A', 0x32, 'free_high', 13)
    a.label('read_one')
    n('LD HL,(remaining)', 0x2a, 'remaining', 16)
    e('LD A,H', [0x7c], 4); e('OR L', [0xb5], 4); e('RET Z', [0xc8], [5,11])
    n('LD (saved_sp),SP', (0xed,0x73), 'saved_sp', 20)
    n('LD SP,disk_stack', 0x31, DISK_STACK, 10)
    e('PUSH IX', [0xdd,0xe5], 15); e('PUSH IY', [0xfd,0xe5], 15)
    e('EX AF,AF2', [0x08], 4); e('PUSH AF', [0xf5], 11); e('EX AF,AF2', [0x08], 4)
    e('EXX', [0xd9], 4)
    for op, reg in ((0xc5,'BC'),(0xd5,'DE'),(0xe5,'HL')): e('PUSH '+reg, [op], 11)
    e('EXX', [0xd9], 4)
    n('LD A,(write_region)', 0x3a, 'write_region', 13)
    e('CP 2', [0xfe,2], 7); n('JP C,page', 0xda, 'page', 10)
    e('INC A', [0x3c], 4)
    a.label('page'); e('OR 10h', [0xf6,0x10], 7); n('CALL atomic_page', 0xcd, PAGE, 17)
    if not fast_disk:
        n('LD HL,slow_irq', 0x21, 0xbd00, 10); n('LD (irq_vector),HL', 0x22, 0xbdbe, 16)
    n('LD A,(write_high)', 0x3a, 'write_high', 13)
    e('LD H,A', [0x67], 4); e('LD L,0', [0x2e,0], 7)
    n('LD DE,(disk_position)', (0xed,0x5b), 'disk_position', 20)
    if fast_disk:
        if cached_seek:
            e('LD A,80h',[0x3e,0x80],7); n('LD (ROM_command),A',0x32,0x5cfe,13)
        n('LD A,(cached_track)', 0x3a, 'cached_track', 13); e('CP D',[0xba],4)
        if cached_seek:
            n('JP Z,direct_ready',0xca,'direct_ready',10)
            e('CP FFh',[0xfe,255],7); n('JP Z,full_read',0xca,'full_read',10)
            n('CALL cached_seek',0xcd,CACHED_SEEK,17)
            n('LD DE,(disk_position)',(0xed,0x5b),'disk_position',20)
            a.label('direct_ready')
        else:
            n('JP NZ,full_read',0xc2,'full_read',10)
        n('LD (ROM_destination),HL',0x22,0x5d00,16)
        e('LD A,E',[0x7b],4); n('LD (ROM_sector),A',0x32,0x5cff,13)
        if not cached_seek:
            e('LD A,80h',[0x3e,0x80],7); n('LD (ROM_command),A',0x32,0x5cfe,13)
        n('LD DE,fast_disk_return',0x11,'fast_disk_return',10); e('PUSH DE',[0xd5],11)
        n('LD DE,retry_counter',0x11,0x0a00,10); e('PUSH DE',[0xd5],11)
        n('LD DE,read_503',0x11,0x3f17,10); e('PUSH DE',[0xd5],11)
        a.label('fast_read_enter'); n('JP ROM trampoline',0xc3,0x3d2f,10)
        a.label('fast_disk_return'); e('EI',[0xfb],4)
        # ROM masks the not-ready flag. Only a full 256-byte advance counts
        # as success; retry short/error reads with the ordinary dispatcher.
        n('LD DE,(ROM_destination)',(0xed,0x5b),0x5d00,20)
        e('INC D',[0x14],4); e('OR A',[0xb7],4); e('SBC HL,DE',[0xed,0x52],15)
        n('JP Z,disk_finish',0xca,'disk_finish',10)
        a.label('fast_read_retry'); n('LD HL,(ROM_destination)',0x2a,0x5d00,16)
        n('LD DE,(disk_position)',(0xed,0x5b),'disk_position',20)
        a.label('full_read'); e('LD A,D',[0x7a],4); n('LD (cached_track),A',0x32,'cached_track',13)
        e('PUSH HL',[0xe5],11)
        n('LD HL,slow_irq',0x21,0xbd00,10); n('LD (irq_vector),HL',0x22,0xbdbe,16)
        e('POP HL',[0xe1],10)
    n('LD BC,0105h', 0x01, 0x105, 10)
    a.label('disk_full_call'); n('CALL TR-DOS', 0xcd, 0x3d13, 17)
    a.label('disk_return')
    a.label('disk_finish')
    e('DI', [0xf3], 4)
    e('LD A,BEh', [0x3e,0xbe], 7); e('LD I,A', [0xed,0x47], 9); e('IM 2', [0xed,0x5e], 8)
    n('LD HL,fast_irq', 0x21, 0xbd80, 10); n('LD (irq_vector),HL', 0x22, 0xbdbe, 16)
    e('EI', [0xfb], 4)
    n('LD DE,(disk_position)', (0xed,0x5b), 'disk_position', 20)
    if interleaved:
        emit_interleaved_cursor(a,listing)
    else:
        e('INC E', [0x1c], 4); e('BIT 4,E', [0xcb,0x63], 8)
        n('JP Z,sector_ok', 0xca, 'sector_ok', 10)
        e('LD E,0', [0x1e,0], 7); e('INC D', [0x14], 4)
    a.label('sector_ok'); n('LD (disk_position),DE', (0xed,0x53), 'disk_position', 20)
    n('LD HL,(remaining)', 0x2a, 'remaining', 16); e('DEC HL', [0x2b], 6)
    n('LD (remaining),HL', 0x22, 'remaining', 16)
    n('LD A,(write_high)', 0x3a, 'write_high', 13); e('INC A', [0x3c], 4)
    n('JP NZ,high_ok', 0xc2, 'high_ok', 10)
    n('LD A,(write_region)', 0x3a, 'write_region', 13)
    e('INC A', [0x3c], 4); e('AND 3', [0xe6,3], 7)
    n('LD (write_region),A', 0x32, 'write_region', 13); e('LD A,C0h', [0x3e,0xc0], 7)
    a.label('high_ok'); n('LD (write_high),A', 0x32, 'write_high', 13)
    if keepalive_fields:
        n('LD HL,(elapsed_fields)',0x2a,elapsed_fields,16)
        n('LD (last_disk_fields),HL',0x22,LAST_DISK_FIELDS,16)
    a.label('disk_restore')
    e('EXX', [0xd9], 4)
    for op, reg in ((0xe1,'HL'),(0xd1,'DE'),(0xc1,'BC')): e('POP '+reg, [op], 10)
    e('EXX', [0xd9], 4)
    e('EX AF,AF2', [0x08], 4); e('POP AF', [0xf1], 10); e('EX AF,AF2', [0x08], 4)
    e('POP IY', [0xfd,0xe1], 14); e('POP IX', [0xdd,0xe1], 14)
    n('LD SP,(saved_sp)', (0xed,0x7b), 'saved_sp', 20); e('RET', [0xc9], 10)
    a.label('state')
    for label, value in (('disk_position',packed_sector(next_sector)),('remaining',remaining),('saved_sp',0)):
        a.label(label); a.word(value)
    for label, value in (('write_region',0),('write_high',0xc0),('free_high',0xc0)):
        a.label(label); a.emit(value)
    if fast_disk: a.label('cached_track'); a.emit(initial_track)
    a.label('end')
    if a.pc > 0x6100: raise ValueError('disk adapter exceeds bootstrap overlay')
    return a.resolve(), dict(a.labels), listing


def build_deferred(disk_labels, limit, *,keepalive_fields=0,elapsed_fields=None,frame_service=False):
    """Defer completed sectors; force one read before consuming the ring reserve.

    A sector becomes writable only after its bytes have been copied to BC00.
    At most limit-1 sectors remain unfilled: even limit=248 retains eight
    complete loaded sectors ahead of a <=256-byte consumer request. The
    caller still accounts for 4-byte block headers through the same hook.
    Idle calls run from the bank-7 clock and must restore bank 7 before RET.
    """
    if not 1 <= limit <= 248: raise ValueError('deferred limit must be 1..248')
    if keepalive_fields and not (1<=keepalive_fields<=100 and elapsed_fields is not None and 'cached_track' in disk_labels):
        raise ValueError('invalid deferred keepalive')
    if frame_service and not keepalive_fields: raise ValueError('frame service requires keepalive clock')
    a=MiniAssembler(DEFERRED); rows=[]; e,n=helpers(a,rows,'disk_deferred')
    a.label('idle')
    n('LD A,(pending)',0x3a,'pending',13); e('OR A',[0xb7],4)
    if keepalive_fields: n('JP Z,no_pending',0xca,'no_pending',10)
    else: e('RET Z',[0xc8],[5,11])
    n('LD HL,(remaining)',0x2a,disk_labels['remaining'],16)
    e('LD A,H',[0x7c],4); e('OR L',[0xb5],4); e('RET Z',[0xc8],[5,11])
    n('LD HL,pending',0x21,'pending',10); e('DEC (HL)',[0x35],11)
    n('CALL read_one',0xcd,disk_labels['read_one'],17)
    e('LD A,17h',[0x3e,0x17],7); n('CALL atomic_page',0xcd,PAGE,17)
    e('LD A,1',[0x3e,1],7); e('RET',[0xc9],10)
    if keepalive_fields:
        a.label('no_pending')
        if a.pc!=DEFERRED_DUE: raise ValueError('timed service entry moved')
        n('LD HL,(remaining)',0x2a,disk_labels['remaining'],16)
        e('LD A,H',[0x7c],4); e('OR L',[0xb5],4); e('RET Z',[0xc8],[5,11])
        n('LD HL,(elapsed_fields)',0x2a,elapsed_fields,16)
        n('LD DE,(last_disk_fields)',(0xed,0x5b),LAST_DISK_FIELDS,20)
        e('OR A',[0xb7],4); e('SBC HL,DE',[0xed,0x52],15)
        target='service_due' if frame_service else 'keepalive'
        e('LD A,H',[0x7c],4); e('OR A',[0xb7],4); n('JP NZ,service due',0xc2,target,10)
        e('LD A,L',[0x7d],4); e('CP fields',[0xfe,keepalive_fields],7)
        n('JP NC,service due',0xd2,target,10)
        e('XOR A',[0xaf],4); e('RET',[0xc9],10)
    if a.pc>CONSUME: raise ValueError('idle routine overlaps consumption hook')
    a.emit(*bytes(CONSUME-a.pc))
    a.label('consume')
    n('LD A,(free_high)',0x3a,disk_labels['free_high'],13)
    e('CP H',[0xbc],4); e('RET Z',[0xc8],[5,11])
    e('LD A,H',[0x7c],4); n('LD (free_high),A',0x32,disk_labels['free_high'],13)
    n('LD HL,(remaining)',0x2a,disk_labels['remaining'],16)
    e('LD A,H',[0x7c],4); e('OR L',[0xb5],4); e('RET Z',[0xc8],[5,11])
    n('LD HL,pending',0x21,'pending',10); e('INC (HL)',[0x34],11)
    e('LD A,(HL)',[0x7e],7); e('CP limit',[0xfe,limit],7); e('RET C',[0xd8],[5,11])
    e('DEC (HL)',[0x35],11); n('JP read_one',0xc3,disk_labels['read_one'],10)
    if keepalive_fields:
        if frame_service:
            a.label('service_due')
            n('LD A,(pending)',0x3a,'pending',13); e('OR A',[0xb7],4)
            n('JP NZ,idle read',0xc2,'idle',10)
        a.label('keepalive')
        # Same outer register/stack contract as read_one. The controller gets
        # SEEK+HLD to the LAST-read cylinder; no stream/side/READ flag changes.
        n('LD (saved_sp),SP',(0xed,0x73),disk_labels['saved_sp'],20)
        n('LD SP,disk_stack',0x31,DISK_STACK,10)
        e('PUSH IX',[0xdd,0xe5],15); e('PUSH IY',[0xfd,0xe5],15)
        e('EX AF,AF2',[0x08],4); e('PUSH AF',[0xf5],11); e('EX AF,AF2',[0x08],4)
        e('EXX',[0xd9],4)
        for op,reg in ((0xc5,'BC'),(0xd5,'DE'),(0xe5,'HL')): e('PUSH '+reg,[op],11)
        e('EXX',[0xd9],4)
        n('LD HL,slow_irq',0x21,0xbd00,10); n('LD (irq_vector),HL',0x22,0xbdbe,16)
        e('LD B,0',[0x06,0],7)
        n('LD HL,keepalive_return',0x21,'keepalive_return',10); e('PUSH HL',[0xe5],11)
        n('LD HL,seek_503',0x21,0x3e44,10); e('PUSH HL',[0xe5],11)
        e('LD A,BEh',[0x3e,0xbe],7); e('LD I,A',[0xed,0x47],9); e('IM 2',[0xed,0x5e],8)
        n('LD A,(cached_track)',0x3a,disk_labels['cached_track'],13); e('SRL A',[0xcb,0x3f],8); e('EI',[0xfb],4)
        a.label('keepalive_enter'); n('JP ROM trampoline',0xc3,0x3d2f,10)
        a.label('keepalive_return'); e('EI',[0xfb],4)
        n('LD HL,fast_irq',0x21,0xbd80,10); n('LD (irq_vector),HL',0x22,0xbdbe,16)
        n('LD HL,(elapsed_fields)',0x2a,elapsed_fields,16)
        n('LD (last_disk_fields),HL',0x22,LAST_DISK_FIELDS,16)
        e('LD A,1',[0x3e,1],7); n('JP disk_restore',0xc3,disk_labels['disk_restore'],10)
        if a.pc>LAST_DISK_FIELDS-2: raise ValueError('keepalive code overlaps deferred state')
        a.emit(*bytes(LAST_DISK_FIELDS-2-a.pc))
    a.label('state'); a.label('pending'); a.emit(0); a.label('end')
    if keepalive_fields:
        a.emit(0); a.label('last_disk_fields'); a.word(0); a.labels['end']=a.pc
    if a.pc>WAIT_NEXT: raise ValueError('deferred disk code overlaps next-disk prompt')
    return a.resolve(),dict(a.labels),rows


def build_cached_seek(disk_labels):
    """Known 5.03 side/SEEK entries; HL is the pending sector destination."""
    a=MiniAssembler(CACHED_SEEK); listing=[]
    e,n=helpers(a,listing,'cached_seek')
    a.label('cached_seek')
    e('PUSH HL',[0xe5],11); e('LD A,D',[0x7a],4)
    n('LD (ROM_track),A',0x32,0x5cf5,13)
    n('LD (cached_track),A',0x32,disk_labels['cached_track'],13)
    n('LD HL,slow_irq',0x21,0xbd00,10); n('LD (irq_vector),HL',0x22,0xbdbe,16)
    n('LD A,(disk_track)',0x3a,disk_labels['disk_position']+1,13)
    e('AND 1',[0xe6,1],7); n('LD DE,side_zero',0x11,0x1feb,10)
    n('JP Z,side_ready',0xca,'side_ready',10); n('LD DE,side_one',0x11,0x1ff6,10)
    a.label('side_ready'); n('LD HL,seek_side_return',0x21,'seek_side_return',10)
    e('PUSH HL',[0xe5],11); e('PUSH DE',[0xd5],11)
    e('LD A,BEh',[0x3e,0xbe],7); e('LD I,A',[0xed,0x47],9); e('IM 2',[0xed,0x5e],8); e('EI',[0xfb],4)
    a.label('seek_side_enter'); n('JP ROM trampoline',0xc3,0x3d2f,10)
    a.label('seek_side_return'); e('EI',[0xfb],4)
    n('LD A,(ROM_drive)',0x3a,0x5cf6,13); e('LD E,A',[0x5f],4); e('LD D,0',[0x16,0],7)
    n('LD HL,drive_step_rates',0x21,0x5cfa,10); e('ADD HL,DE',[0x19],11)
    e('LD A,(HL)',[0x7e],7); e('AND 3',[0xe6,3],7); e('LD B,A',[0x47],4)
    n('LD A,(disk_track)',0x3a,disk_labels['disk_position']+1,13); e('SRL A',[0xcb,0x3f],8)
    n('LD HL,seek_return',0x21,'seek_return',10); e('PUSH HL',[0xe5],11)
    n('LD HL,seek_503',0x21,0x3e44,10); e('PUSH HL',[0xe5],11); e('EI',[0xfb],4)
    a.label('seek_enter'); n('JP ROM trampoline',0xc3,0x3d2f,10)
    a.label('seek_return'); e('EI',[0xfb],4)
    n('LD HL,fast_irq',0x21,0xbd80,10); n('LD (irq_vector),HL',0x22,0xbdbe,16)
    e('LD A,84h',[0x3e,0x84],7); n('LD (ROM_command),A',0x32,0x5cfe,13)
    e('POP HL',[0xe1],10); e('RET',[0xc9],10)
    a.label('end')
    if a.pc>0x9b00: raise ValueError('cached seek overlaps row-low table')
    return a.resolve(),dict(a.labels),listing


def build_next_loader(*,entry=0x6000):
    a=MiniAssembler(LOAD_NEXT)
    # Runs outside 6000..63ff while replacing the next disk's bootstrap.
    a.label('load_next'); a.emit(0xf3,0x31); a.word(0x5ff0)
    a.emit(0xed,0x56,0xfb,0x21); a.word(0x6000); a.emit(0x16,1,0x1e,1,0x06,4)
    a.label('load_next_sector'); a.emit(0xc5,0xd5,0xe5,0x01); a.word(0x105)
    a.emit(0xcd); a.word(0x3d13)
    a.emit(0xe1,0xd1,0xc1,0x24,0x1c); a.rel8(0x10,'load_next_sector')
    a.emit(0xc3); a.word(entry)
    a.label('end')
    if a.pc > 0x9b00: raise ValueError('next loader overlaps row-low table')
    return a.resolve(), dict(a.labels)


def build_driver(h, clock, ay_state, *, has_next=False, deferred=False):
    a = MiniAssembler(DRIVER)
    def call(address): a.emit(0xcd); a.word(address)
    a.label('start'); a.emit(0xf3,0x31); a.word(0x9df0)
    if deferred:
        # Bootstrap is finished; its old 6100..61FF can now be replaced.
        # Copy before audio_init clears the temporary AY queue at A200.
        a.emit(0x21); a.word(0xa200); a.emit(0x11); a.word(DEFERRED)
        a.emit(0x01); a.word(256); a.emit(0xed,0xb0)
    a.emit(0x21); a.word(h.frames); call(h.audio['audio_init']); call(h.audio['setup_clock'])
    # R0..10 checkpoint: following packets remain byte-identical AY deltas.
    a.abs16(0x21,'ay_state'); a.emit(0x16,0)
    a.label('ay_restore'); a.emit(0x7a,0x01); a.word(0xfffd); a.emit(0xed,0x79,0x7e,0x23,0x06,0xbf,0xed,0x79,0x14,0x7a,0xfe,11)
    a.rel8(0x20,'ay_restore')
    a.emit(0xfb); call(clock['prime']); call(clock['start'])
    a.label('main_loop'); a.emit(0x2a); a.word(clock['remaining']); a.emit(0x7c,0xb5)
    a.abs16(0xca,'drain'); call(clock['play_one']); a.abs16(0xc3,'main_loop')
    a.label('drain'); call(h.audio['audio_drain'])
    # Silence at the disk boundary, leaving the complete last screen/bar.
    for reg in (8,9,10):
        a.emit(0x3e,reg,0x01); a.word(0xfffd); a.emit(0xed,0x79,0xaf,0x06,0xbf,0xed,0x79)
    a.label('finished')
    if has_next: a.emit(0xc3); a.word(WAIT_NEXT)
    else: a.emit(0x3e,4,0xd3,0xfe,0x76); a.abs16(0xc3,'finished')
    a.label('ay_state'); a.emit(*ay_state); a.label('end')
    if a.pc > 0xe000: raise ValueError('driver overlaps ZX0 history')
    return a.resolve(), dict(a.labels)


def build_bootstrap(sections, video_sector, video_sectors, *, next_id=bytes(16), interleaved=False,
                    warm_set=False,continuation=False):
    """Sections already sector-aligned on disk; decompress directly to RAM."""
    a = MiniAssembler(0x6000)
    def call(label): a.abs16(0xcd,label)
    def page(bank):
        a.emit(0x3e,0x10|bank,0x01); a.word(0x7ffd); a.emit(0xed,0x79)
    if continuation and not warm_set: raise ValueError('continuation requires warm set')
    a.label('bootstrap')
    if warm_set:
        # The disk-change loader enters at 6003. A cold USR on a later
        # disk returns to BASIC, which prints START WITH DISK 1.
        if continuation: a.emit(0xc9,0,0)
        else: a.emit(0xc3); a.word(0x6003)
    a.label('bootstrap_entry'); a.emit(0xf3,0x31); a.word(0x5ff0)
    a.emit(0xfd,0x21); a.word(0x5c3a); a.emit(0xed,0x56,0xfb)
    for section in sections:
        page(section['bank'])
        a.emit(0x11); a.word(packed_sector(section['sector']))
        a.abs16((0xed,0x53),'disk_position')
        a.emit(0x21); a.word(section['buffer'])
        a.emit(0x06,section['sectors']); call('read_n')
        a.emit(0x21); a.word(section['buffer'])
        a.emit(0x11); a.word(section['address']); call('dzx0_standard')
        if section.get('warm_reset'):
            a.emit(0x21); a.word(section['address']); call('warm_reset')
    a.emit(0x11); a.word(packed_sector(video_sector)); a.abs16((0xed,0x53),'disk_position')
    left = min(256, video_sectors)
    for bank in (0,1,3,4):
        count = min(64,left)
        if not count: break
        page(bank); a.emit(0x21); a.word(0xc000); a.emit(0x06,count); call('read_n'); left -= count
    page(7)
    # Runtime reader replaces only the no-longer-used bootstrap prefix.
    # A100 is temporary storage in the initially empty AY queue.
    if a.pc<0x6100:
        # Small videos preload fewer banks and produce a shorter bootstrap.
        # Skip inert padding before overwriting 6000..60FF. JP nn = 10 T;
        # existing full-ring bootstraps emit exactly the previous byte sequence.
        target=max(0x6100,a.pc+3)
        a.label('overlay_jump')
        a.emit(0xc3); a.word(target); a.emit(*bytes(target-a.pc))
    a.label('overlay_copy')
    a.emit(0x21); a.word(0xa100); a.emit(0x11); a.word(DISK)
    a.emit(0x01); a.word(256); a.emit(0xed,0xb0,0xf3,0xc3); a.word(DRIVER)
    a.label('read_n')
    a.label('read_loop'); a.emit(0xc5,0xe5)
    a.abs16((0xed,0x5b),'disk_position'); a.emit(0x01); a.word(0x105)
    a.label('boot_disk_call'); a.emit(0xcd); a.word(0x3d13)
    a.emit(0xe1,0xc1,0x24)
    a.abs16((0xed,0x5b),'disk_position')
    if interleaved:
        # Startup sections and the first partial video track stay linear.
        # Every later track belongs only to the arranged video stream.
        a.emit(0x7a,0xfe,video_sector//16+1); a.abs16(0xda,'advance_linear')
        emit_interleaved_cursor(a,[]); a.abs16(0xc3,'sector_ok')
        a.label('advance_linear')
    a.emit(0x1c,0xcb,0x63)
    a.rel8(0x28,'sector_ok'); a.emit(0x1e,0,0x14)
    a.label('sector_ok'); a.abs16((0xed,0x53),'disk_position')
    a.rel8(0x10,'read_loop'); a.emit(0xc9)
    zx0_codec.emit_decoder(a,variant='standard')
    if any(s.get('warm_reset') for s in sections):
        # count:u16, destination:u16, count bytes; zero count terminates.
        a.label('warm_reset'); a.emit(0x4e,0x23,0x46,0x23,0x78,0xb1,0xc8)
        a.emit(0x5e,0x23,0x56,0x23,0xed,0xb0); a.abs16(0xc3,'warm_reset')
    a.label('disk_position'); a.word(0)
    if a.pc>WAIT_NEXT: raise ValueError('bootstrap overlaps disk prompt')
    a.emit(*bytes(WAIT_NEXT-a.pc))
    a.label('wait_next'); a.emit(0xf3,0x31); a.word(0x5ff0)
    a.emit(0xfd,0x21); a.word(0x5c3a); a.emit(0xed,0x56)
    # Retain the last visible screen; bank 7 is mapped for the second copy.
    a.emit(0x3a); a.word(0x97ca); a.emit(0xe6,8,0xf6,0x17,0x01); a.word(0x7ffd); a.emit(0xed,0x79)
    a.abs16(0x21,'prompt'); a.emit(0x11); a.word(0x50c0); a.emit(0x3e,7)
    a.label('prompt_row'); a.emit(0xf5,0xd5,0xe5,0x01); a.word(32); a.emit(0xed,0xb0,0xe1,0xd1,0xd5,0xcb,0xfa,0x01)
    a.word(32); a.emit(0xed,0xb0,0xd1,0x14,0xf1,0x3d); a.rel8(0x20,'prompt_row')
    for address in (0x5ac0,0xdac0):
        a.emit(0x21); a.word(address); a.emit(0x06,32)
        a.label(f'attr_{address}'); a.emit(0x36,7,0x23); a.rel8(0x10,f'attr_{address}')
    a.label('poll_next'); a.emit(0xfb,0x06,25)
    a.label('pause'); a.emit(0x76); a.rel8(0x10,'pause')
    a.emit(0xaf,0x32); a.word(0xbc00)  # A failed read must not accept stale ID bytes.
    a.emit(0x11); a.word(15); a.emit(0x21); a.word(0xbc00); a.emit(0x01); a.word(0x105)
    a.label('poll_disk_call'); a.emit(0xcd); a.word(0x3d13)
    a.emit(0x21); a.word(0xbc00); a.abs16(0x11,'next_id'); a.emit(0x06,16)
    a.label('check_id'); a.emit(0x1a,0xbe); a.abs16(0xc2,'poll_next'); a.emit(0x13,0x23); a.rel8(0x10,'check_id')
    a.label('next_disk_accepted'); a.emit(0xc3); a.word(LOAD_NEXT)
    a.label('next_id'); a.emit(*next_id)
    a.label('prompt'); a.emit(*prompt_bitmap()); a.label('end')
    if a.pc > 0x6400: raise ValueError('bootstrap overlaps compact checkpoint')
    return a.resolve()+bytes(0x6400-a.pc), dict(a.labels)
