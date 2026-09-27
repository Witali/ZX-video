"""One-sector producer for host-proved in-place ZX0 blocks in banks 0/1/3.

Acquire four header bytes through BC00, then read body sectors at the top
of the selected bank. Save the last shared sector before decoding starts.
Header-only sectors need no copy. No complete compressed-block copy occurs.
"""
from build_zxv_trd import MiniAssembler
from pipelined_frame_z80 import helpers, PAGE

CODE, LIMIT, AUX, AUX_LIMIT, COPY, COPY_LIMIT = 0x7d50, 0x7f00, 0x7823, 0x78a0, 0x7b00, 0x7b58
CARRY, OUTPUT, MAX_OUTPUT = 0xbc00, 0xc000, 15872


def build(z, disk, *, elapsed_fields=None):
    rows = []; assemblers = []
    def setup(origin):
        a = MiniAssembler(origin); assemblers.append(a)
        return a, *helpers(a, rows, 'inplace_slot_input')
    a, e, n = setup(CODE)
    def load(label): n('LD A,('+str(label)+')', 0x3a, label, 13)
    def store(label): n('LD ('+str(label)+'),A', 0x32, label, 13)
    def wl(label): n('LD HL,('+str(label)+')', 0x2a, label, 16)
    def ws(label): n('LD ('+str(label)+'),HL', 0x22, label, 16)
    def call(label): n('CALL '+str(label), 0xcd, label, 17)
    def jump(op, label): n('JP '+str(label), op, label, 10)
    def ret(): e('RET', [0xc9], 10)
    def advance():
        n('LD HL,pages', 0x21, 'pages', 10); e('DEC (HL)', [0x35], 11)
        e('INC HL', [0x23], 6); e('INC (HL)', [0x34], 11)

    a.label('begin'); e('CP 3', [0xfe, 3], 7); jump(0xd2, 'fatal'); store('slot')
    e('XOR A', [0xaf], 4); store('phase'); store('header_count'); ret()
    a.label('step'); call('page_slot'); load('phase'); e('OR A', [0xb7], 4); jump(0xc2, 'body')
    load('has_carry'); e('OR A', [0xb7], 4); jump(0xc2, 'header')
    e('LD A,BCh', [0x3e, 0xbc], 7); store(disk['write_high']); call('read_sector')
    e('LD A,1', [0x3e, 1], 7); store('has_carry'); e('XOR A', [0xaf], 4); ret()

    a.label('header'); load('header_count'); e('LD E,A', [0x5f], 4); e('LD D,0', [0x16, 0], 7)
    n('LD HL,header bytes', 0x21, 'header_bytes', 10); e('ADD HL,DE', [0x19], 11); e('EX DE,HL', [0xeb], 4)
    e('NEG', [0xed, 0x44], 8); e('ADD A,4', [0xc6, 4], 7); e('LD B,A', [0x47], 4)
    load('offset'); e('LD L,A', [0x6f], 4); e('LD H,BC', [0x26, 0xbc], 7)
    a.label('header_byte'); e('LD A,(HL)', [0x7e], 7); e('LD (DE),A', [0x12], 7)
    e('INC DE', [0x13], 6); e('INC L', [0x2c], 4); jump(0xca, 'header_wrapped')
    rows.append(dict(address=a.pc, instruction='DJNZ header byte', tstates=[8, 13], phase='inplace_slot_input'))
    a.rel8(0x10, 'header_byte'); jump(0xc3, 'header_done')
    a.label('header_wrapped'); e('XOR A', [0xaf], 4); store('has_carry')
    e('DEC B', [0x05], 4); jump(0xca, 'header_done')
    e('LD A,4', [0x3e, 4], 7); e('SUB B', [0x90], 4); store('header_count')
    e('XOR A', [0xaf], 4); store('offset'); ret()

    a.label('header_done'); e('LD A,L', [0x7d], 4); store('offset')
    wl('header_bytes'); n('LD BC,max output plus one', 0x01, MAX_OUTPUT+1, 10); call('validate')
    ws(z['block_length']); n('LD DE,C000', 0x11, OUTPUT, 10); e('ADD HL,DE', [0x19], 11); ws(z['block_end'])
    wl('compressed_length'); n('LD BC,4001', 0x01, 16385, 10); call('validate')
    load('offset'); e('LD E,A', [0x5f], 4); e('LD D,0', [0x16, 0], 7); e('ADD HL,DE', [0x19], 11)
    e('LD A,L', [0x7d], 4); store('tail_offset'); e('OR A', [0xb7], 4); e('LD A,H', [0x7c], 4)
    jump(0xca, 'span_ready'); e('INC A', [0x3c], 4)
    a.label('span_ready'); e('CP 65', [0xfe, 65], 7); jump(0xd2, 'fatal'); store('pages')
    e('NEG', [0xed, 0x44], 8); store('destination_high'); e('LD H,A', [0x67], 4)
    load('offset'); e('LD L,A', [0x6f], 4); ws(z['input_pointer'])
    e('XOR A', [0xaf], 4); store(z['block_stored']); e('LD A,1', [0x3e, 1], 7); store('phase')
    load('has_carry'); e('OR A', [0xb7], 4); jump(0xca, 'body')
    load('destination_high'); e('LD D,A', [0x57], 4); e('LD E,0', [0x1e, 0], 7)
    n('LD HL,carry', 0x21, CARRY, 10); call('copy_sector'); advance()

    a.label('body'); load('phase'); e('CP 2', [0xfe, 2], 7); jump(0xca, 'ready_return')
    load('pages'); e('OR A', [0xb7], 4); jump(0xca, 'finish_input')
    load('destination_high'); store(disk['write_high']); call('read_sector'); advance()
    e('XOR A', [0xaf], 4); ret()
    a.label('finish_input'); load('tail_offset'); store('offset'); store('has_carry')
    e('OR A', [0xb7], 4); jump(0xca, 'ready')
    n('LD HL,last sector', 0x21, 0xff00, 10); n('LD DE,carry', 0x11, CARRY, 10); call('copy_sector')
    a.label('ready'); e('LD A,2', [0x3e, 2], 7); store('phase')
    a.label('ready_return'); e('LD A,1', [0x3e, 1], 7); ret()
    a.label('fatal'); e('HALT', [0x76], 4)
    a.label('state')
    for label, value in (('phase',0), ('slot',0), ('has_carry',0), ('offset',0), ('header_count',0),
                         ('tail_offset',0), ('pages',0), ('destination_high',0), ('linear',1)):
        a.label(label); a.emit(value)
    a.label('header_bytes'); a.word(0); a.label('compressed_length'); a.word(0)
    a.label('end')
    if a.pc>LIMIT: raise ValueError(f'in-place producer too large: {a.pc:04x}')

    a, e, n = setup(AUX)
    a.label('validate'); e('LD A,H', [0x7c], 4); e('OR L', [0xb5], 4); jump(0xca, 'fatal')
    e('PUSH HL', [0xe5], 11); e('OR A', [0xb7], 4); e('SBC HL,BC', [0xed, 0x42], 15)
    e('POP HL', [0xe1], 10); jump(0xd2, 'fatal'); ret()
    a.label('page_slot'); load('slot'); store(disk['write_region'])
    e('CP 2', [0xfe, 2], 7); jump(0xda, 'page_value'); e('INC A', [0x3c], 4)
    a.label('page_value'); e('OR 10h', [0xf6, 0x10], 7); jump(0xc3, PAGE)
    a.label('read_sector'); wl(disk['remaining']); e('LD A,H', [0x7c], 4); e('OR L', [0xb5], 4); jump(0xca, 'fatal')
    if elapsed_fields is not None: call('check_idle')
    load('linear'); e('OR A', [0xb7], 4); jump(0xca, 'read_interleaved')
    wl(disk['disk_position']); e('INC L', [0x2c], 4); e('BIT 4,L', [0xcb, 0x65], 8); jump(0xca, 'linear_next')
    e('LD L,0', [0x2e, 0], 7); e('INC H', [0x24], 4); e('XOR A', [0xaf], 4); store('linear')
    a.label('linear_next'); e('PUSH HL', [0xe5], 11); call(disk['read_one']); e('POP HL', [0xe1], 10)
    ws(disk['disk_position']); ret()
    a.label('read_interleaved'); jump(0xc3, disk['read_one'])
    if elapsed_fields is not None:
        # A long filled-slot interval may let the drive unload its head.
        # Force the existing cached SEEK/HLD path before the next read.
        # FF still means uninitialized and must use the full dispatcher.
        a.label('check_idle'); wl(elapsed_fields)
        n('LD DE,(last read field)', (0xed, 0x5b), 'last_read_field', 20); ws('last_read_field')
        e('OR A', [0xb7], 4); e('SBC HL,DE', [0xed, 0x52], 15)
        e('LD A,H', [0x7c], 4); e('OR A', [0xb7], 4); jump(0xc2, 'reload_head')
        e('LD A,L', [0x7d], 4); e('CP 64 fields', [0xfe, 64], 7); e('RET C', [0xd8], [5, 11])
        a.label('reload_head'); load(disk['cached_track']); e('CP FFh', [0xfe, 255], 7)
        e('RET Z', [0xc8], [5, 11]); e('LD A,FEh', [0x3e, 254], 7); store(disk['cached_track']); ret()
        a.label('last_read_field'); a.word(0)
    a.label('aux_end')
    if a.pc>AUX_LIMIT: raise ValueError('producer helpers overlap retired metadata boundary')

    a, e, n = setup(COPY)
    a.label('copy_sector'); n('LD BC,256', 0x01, 256, 10); e('LD A,8', [0x3e, 8], 7)
    a.label('copy_chunk')
    for _ in range(32): e('LDI', [0xed, 0xa0], 16)
    e('DEC A', [0x3d], 4); jump(0xc2, 'copy_chunk'); ret(); a.label('copy_end')
    if a.pc>COPY_LIMIT: raise ValueError('sector copier overlaps private decoder stack')
    labels = {}
    for assembler in assemblers: labels.update(assembler.labels)
    regions = []
    for assembler in assemblers:
        assembler.labels.update(labels); regions.append((assembler.origin, assembler.resolve()))
    return regions, labels, rows
