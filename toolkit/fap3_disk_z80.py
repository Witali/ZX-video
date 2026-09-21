"""Experimental TR-DOS adapter for the measured FAP3 raster pipeline.

The refill hook replaces only fully consumed 256-byte ring sectors. ROM
service time is additional to the instruction listing, never estimated as
zero. Disk calls use a separate fixed-RAM stack, preserving ZX0's alternate
registers and private suspension stack. This is a blocking first backend.
"""
from build_zxv_trd import MiniAssembler
from pipelined_frame_z80 import helpers, PAGE
import zx0_codec

DISK, DRIVER, DISK_STACK = 0x6000, 0xdf20, 0x9c00
WAIT_NEXT, LOAD_NEXT = 0x6200, 0x9a60


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


def build_disk(next_sector, remaining):
    a = MiniAssembler(DISK); listing = []
    e, n = helpers(a, listing, 'disk_adapter')
    a.label('refill')
    n('LD A,(free_high)', 0x3a, 'free_high', 13)
    e('CP H', [0xbc], 4); e('RET Z', [0xc8], [5,11])
    e('LD A,H', [0x7c], 4); n('LD (free_high),A', 0x32, 'free_high', 13)
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
    n('LD HL,slow_irq', 0x21, 0xbd00, 10); n('LD (irq_vector),HL', 0x22, 0xbdbe, 16)
    n('LD A,(write_high)', 0x3a, 'write_high', 13)
    e('LD H,A', [0x67], 4); e('LD L,0', [0x2e,0], 7)
    n('LD DE,(disk_position)', (0xed,0x5b), 'disk_position', 20)
    n('LD BC,0105h', 0x01, 0x105, 10)
    a.label('disk_full_call'); n('CALL TR-DOS', 0xcd, 0x3d13, 17)
    a.label('disk_return')
    e('DI', [0xf3], 4)
    e('LD A,BEh', [0x3e,0xbe], 7); e('LD I,A', [0xed,0x47], 9); e('IM 2', [0xed,0x5e], 8)
    n('LD HL,fast_irq', 0x21, 0xbd80, 10); n('LD (irq_vector),HL', 0x22, 0xbdbe, 16)
    e('EI', [0xfb], 4)
    n('LD DE,(disk_position)', (0xed,0x5b), 'disk_position', 20)
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
    a.label('end')
    if a.pc > 0x6100: raise ValueError('disk adapter exceeds bootstrap overlay')
    return a.resolve(), dict(a.labels), listing


def build_next_loader():
    a=MiniAssembler(LOAD_NEXT)
    # Runs outside 6000..63ff while replacing the next disk's bootstrap.
    a.label('load_next'); a.emit(0xf3,0x31); a.word(0x5ff0)
    a.emit(0xed,0x56,0xfb,0x21); a.word(0x6000); a.emit(0x16,1,0x1e,1,0x06,4)
    a.label('load_next_sector'); a.emit(0xc5,0xd5,0xe5,0x01); a.word(0x105)
    a.emit(0xcd); a.word(0x3d13)
    a.emit(0xe1,0xd1,0xc1,0x24,0x1c); a.rel8(0x10,'load_next_sector')
    a.emit(0xc3); a.word(0x6000)
    a.label('end')
    if a.pc > 0x9b00: raise ValueError('next loader overlaps row-low table')
    return a.resolve(), dict(a.labels)


def build_driver(h, clock, ay_state, *, has_next=False):
    a = MiniAssembler(DRIVER)
    def call(address): a.emit(0xcd); a.word(address)
    a.label('start'); a.emit(0xf3,0x31); a.word(0x9df0)
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


def build_bootstrap(sections, video_sector, video_sectors, *, next_id=bytes(16)):
    """Sections already sector-aligned on disk; decompress directly to RAM."""
    a = MiniAssembler(0x6000)
    def call(label): a.abs16(0xcd,label)
    def page(bank):
        a.emit(0x3e,0x10|bank,0x01); a.word(0x7ffd); a.emit(0xed,0x79)
    a.label('bootstrap'); a.emit(0xf3,0x31); a.word(0x5ff0)
    a.emit(0xfd,0x21); a.word(0x5c3a); a.emit(0xed,0x56,0xfb)
    for section in sections:
        page(section['bank'])
        a.emit(0x11); a.word(packed_sector(section['sector']))
        a.abs16((0xed,0x53),'disk_position')
        a.emit(0x21); a.word(section['buffer'])
        a.emit(0x06,section['sectors']); call('read_n')
        a.emit(0x21); a.word(section['buffer'])
        a.emit(0x11); a.word(section['address']); call('dzx0_standard')
    a.emit(0x11); a.word(packed_sector(video_sector)); a.abs16((0xed,0x53),'disk_position')
    left = min(256, video_sectors)
    for bank in (0,1,3,4):
        count = min(64,left)
        if not count: break
        page(bank); a.emit(0x21); a.word(0xc000); a.emit(0x06,count); call('read_n'); left -= count
    page(7)
    # Runtime reader replaces only the no-longer-used bootstrap prefix.
    # A100 is temporary storage in the initially empty AY queue.
    if a.pc<0x6100: raise ValueError('overlay copy executes inside its target')
    a.emit(0x21); a.word(0xa100); a.emit(0x11); a.word(DISK)
    a.emit(0x01); a.word(256); a.emit(0xed,0xb0,0xf3,0xc3); a.word(DRIVER)
    a.label('read_n')
    a.label('read_loop'); a.emit(0xc5,0xe5)
    a.abs16((0xed,0x5b),'disk_position'); a.emit(0x01); a.word(0x105)
    a.label('boot_disk_call'); a.emit(0xcd); a.word(0x3d13)
    a.emit(0xe1,0xc1,0x24)
    a.abs16((0xed,0x5b),'disk_position'); a.emit(0x1c,0xcb,0x63)
    a.rel8(0x28,'sector_ok'); a.emit(0x1e,0,0x14)
    a.label('sector_ok'); a.abs16((0xed,0x53),'disk_position')
    a.rel8(0x10,'read_loop'); a.emit(0xc9)
    zx0_codec.emit_decoder(a,variant='standard')
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
