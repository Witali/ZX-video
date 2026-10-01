"""Compile validated AYH1 into one bank: code, binary trees and coded payload.

Bank-local init/fill entries require bank 4 at C000h and a fixed-RAM stack.
Fill emits at most batch records directly into the existing AY FIFO. It never
waits for room. AF/AF'/BC/DE/HL/IX are scratch; the actual AY ISR preserves
them. A separate fixed-RAM bridge preserves the caller and pages bank 4.
Integration must allocate that bridge. No player, video slots or release
images are changed by this module.
"""
from collections import Counter
import struct

import ay_huffman_stream
import ay_interrupt
from build_fap3_trd import sha
from build_zxv_trd import MiniAssembler
from probe_motion_entropy import Reader

ORIGIN = 0xc000
LIMIT = 0x10000


def tables(data):
    """Canonical trees independent of the host encoder's code assignment."""
    initial, records = ay_huffman_stream.decode(data)  # Validate exact bits too.
    if len(records) > 65535:
        raise ValueError('resident tick counter exceeds 16 bits')
    r = Reader(data)
    r.take(23)
    trees = []
    for _ in range(13):
        entries = [tuple(r.take(2)) for _ in range(r.u16())]
        if len(entries) <= 1:
            trees.append(entries[0][0] if entries else 0)
            continue
        counts = Counter(n for _, n in entries)
        root, first = {}, 0
        for length in range(1, max(counts)+1):
            first = (first+counts[length-1])*2
            for offset, value in enumerate(sorted(v for v, n in entries if n == length)):
                code, node = first+offset, root
                for bit in range(length-1, 0, -1):
                    node = node.setdefault((code >> bit) & 1, {})
                node[code & 1] = value
        trees.append(root)
    return initial, records, trees, data[r.pos:]


def tree_bytes(trees, origin):
    result = bytearray()

    def pointer(node):
        if isinstance(node, int):
            return node  # High byte zero marks a leaf, low byte is the symbol.
        if set(node) != {0, 1}:
            raise ValueError('resident decoder requires complete Huffman trees')
        offset = len(result)
        result.extend(bytes(4))
        left, right = pointer(node[0]), pointer(node[1])
        result[offset:offset+4] = struct.pack('<HH', left, right)
        return origin+offset

    roots = [pointer(tree) for tree in trees]
    return struct.pack('<13H', *roots), bytes(result)


def code(audio, ticks, initial, roots, payload, *, batch=6, total_ticks=None,
         origin=ORIGIN,payload_overflow=None,page_entry=None):
    if not 1 <= batch <= 31:
        raise ValueError('batch must be 1..31')
    if (ay_interrupt.QUEUE_BASE, ay_interrupt.QUEUE_SLOTS, ay_interrupt.SLOT_BYTES) != (0xa000,32,32):
        raise ValueError('AY FIFO address contract changed')
    if payload_overflow is not None and (origin>=0xc000 or page_entry is None):
        raise ValueError('spanning payload requires fixed code and a paging entry')
    a, listing = MiniAssembler(origin), []
    stage = 'init'

    def emit(name, blob, timing):
        listing.append(dict(address=a.pc, instruction=name, tstates=timing, stage=stage))
        a.emit(*blob)

    def absolute(name, opcode, target, timing):
        listing.append(dict(address=a.pc, instruction=name, tstates=timing, stage=stage))
        if isinstance(target, str):
            a.abs16(opcode, target)
        else:
            a.emit(*([opcode] if isinstance(opcode, int) else opcode)); a.word(target)

    def load(name): absolute('LD A,('+name+')', 0x3a, name, 13)
    def store(name): absolute('LD ('+name+'),A', 0x32, name, 13)
    def call(name): absolute('CALL '+name, 0xcd, name, 17)
    def branch(name, opcode, target):
        listing.append(dict(address=a.pc, instruction=name, tstates=[7, 12], stage=stage))
        a.rel8(opcode, target)
    def ret(): emit('RET', [0xc9], 10)

    a.label('init')
    emit('XOR A', [0xaf], 4)
    for name in ('audio_enabled', 'audio_read_index', 'audio_write_index'):
        store(name)
    absolute('LD HL,0', 0x21, 0, 10)
    for name in ('audio_ticks_played', 'audio_underruns'):
        absolute('LD ('+name+'),HL', 0x22, name, 16)
    absolute('LD HL,ticks', 0x21, ticks, 10)
    for name in ('remaining', 'audio_remaining'):
        if name=='audio_remaining' and total_ticks is not None:
            absolute('LD HL,total ticks',0x21,total_ticks,10)
        absolute('LD ('+name+'),HL', 0x22, name, 16)
    absolute('LD HL,payload', 0x21, payload, 10)
    absolute('LD (source),HL', 0x22, 'source', 16)
    emit('LD A,80h', [0x3e, 0x80], 7); store('bit_buffer')
    if payload_overflow is not None:
        emit('LD A,bank 4',[0x3e,0x14],7);store('payload_bank')
    absolute('LD HL,initial', 0x21, 'initial', 10)
    absolute('LD DE,0B00h', 0x11, 0x0b00, 10)
    a.label('init_register')
    absolute('LD BC,FFFDh', 0x01, 0xfffd, 10)
    emit('LD A,E', [0x7b], 4); emit('OUT (C),A', [0xed, 0x79], 12)
    emit('LD B,BFh', [0x06, 0xbf], 7); emit('LD A,(HL)', [0x7e], 7)
    emit('OUT (C),A', [0xed, 0x79], 12); emit('INC HL', [0x23], 6)
    emit('INC E', [0x1c], 4); emit('DEC D', [0x15], 4)
    branch('JR NZ,init_register', 0x20, 'init_register'); ret()

    stage = 'fill'
    a.label('fill')
    emit('XOR A', [0xaf], 4); store('emitted')
    absolute('LD IX,(source)', (0xdd, 0x2a), 'source', 20)
    load('bit_buffer'); emit('LD B,A', [0x47], 4)
    a.label('fill_next')
    absolute('LD HL,(remaining)', 0x2a, 'remaining', 16)
    emit('LD A,H', [0x7c], 4); emit('OR L', [0xb5], 4)
    branch('JR Z,fill_done', 0x28, 'fill_done')
    load('audio_write_index'); emit('INC A', [0x3c], 4)
    emit('AND 31', [0xe6, 31], 7)
    absolute('LD HL,read index', 0x21, 'audio_read_index', 10)
    emit('CP (HL)', [0xbe], 7); branch('JR Z,fill_done', 0x28, 'fill_done')
    store('next_index'); load('audio_write_index')
    # Same 49-T slot-address calculation as ay_interrupt.emit_slot_address.
    for _ in range(3): emit('RRCA', [0x0f], 4)
    emit('LD L,A', [0x6f], 4); emit('AND 3', [0xe6, 3], 7)
    emit('OR A0h', [0xf6, 0xa0], 7); emit('LD H,A', [0x67], 4)
    emit('LD A,L', [0x7d], 4); emit('AND E0h', [0xe6, 0xe0], 7)
    emit('LD L,A', [0x6f], 4); emit('EX DE,HL', [0xeb], 4)
    call('tick')
    load('next_index'); store('audio_write_index')  # Publish only complete data.
    absolute('LD HL,(remaining)', 0x2a, 'remaining', 16)
    emit('DEC HL', [0x2b], 6); absolute('LD (remaining),HL', 0x22, 'remaining', 16)
    load('emitted'); emit('INC A', [0x3c], 4); store('emitted')
    emit('CP batch', [0xfe, batch], 7); branch('JR NZ,fill_next', 0x20, 'fill_next')
    a.label('fill_done')
    absolute('LD (source),IX', (0xdd, 0x22), 'source', 20)
    emit('LD A,B', [0x78], 4); store('bit_buffer'); load('emitted'); ret()

    stage = 'tick'
    a.label('tick')
    emit('PUSH DE', [0xd5], 11); emit('INC DE', [0x13], 6)
    emit('XOR A', [0xaf], 4); emit("EX AF,AF' (count)", [0x08], 4)
    emit('XOR A', [0xaf], 4); call('symbol'); emit('LD C,A', [0x4f], 4)
    emit('LD A,1', [0x3e, 1], 7); call('symbol'); store('high_mask')
    for register in range(11):
        if register == 8:
            load('high_mask'); emit('LD C,A', [0x4f], 4)
        emit('SRL C', [0xcb, 0x39], 8)
        branch('JR NC,skip_'+str(register), 0x30, 'skip_'+str(register))
        emit('LD A,register', [0x3e, register], 7)
        emit('LD (DE),A', [0x12], 7); emit('INC DE', [0x13], 6)
        emit('LD A,context', [0x3e, register+2], 7); call('symbol')
        emit('LD (DE),A', [0x12], 7); emit('INC DE', [0x13], 6)
        emit("EX AF,AF' (count)", [0x08], 4); emit('INC A', [0x3c], 4)
        emit("EX AF,AF' (symbol)", [0x08], 4)
        a.label('skip_'+str(register))
    emit('POP HL', [0xe1], 10); emit("EX AF,AF' (count)", [0x08], 4)
    emit('LD (HL),A', [0x77], 7); ret()

    stage = 'symbol'
    a.label('symbol')  # A=context, IX/B=sentinel bit reader; preserve C and DE.
    emit('ADD A,A', [0x87], 4); emit('LD L,A', [0x6f], 4)
    emit('LD H,root page', [0x26, roots >> 8], 7)
    a.label('child')
    emit('LD A,(HL)', [0x7e], 7); emit('INC HL', [0x23], 6)
    emit('LD H,(HL)', [0x66], 7); emit('LD L,A', [0x6f], 4)
    emit('LD A,H', [0x7c], 4); emit('OR A', [0xb7], 4)
    branch('JR Z,leaf', 0x28, 'leaf')
    emit('SLA B', [0xcb, 0x20], 8)
    branch('JR NZ,have_bit', 0x20, 'have_bit')
    emit('LD B,(IX+0)', [0xdd, 0x46, 0], 19)
    emit('INC IX', [0xdd, 0x23], 10)
    if payload_overflow is not None:
        emit('LD A,IXH',[0xdd,0x7c],8);emit('OR A',[0xb7],4)
        branch('JR NZ,payload_byte_ready',0x20,'payload_byte_ready')
        load('payload_bank');emit('CP bank 4',[0xfe,0x14],7)
        branch('JR NZ,payload_byte_ready',0x20,'payload_byte_ready')
        emit('LD A,bank 6',[0x3e,0x16],7);store('payload_bank')
        emit('PUSH BC',[0xc5],11);absolute('CALL payload page',0xcd,page_entry,17);emit('POP BC',[0xc1],10)
        absolute('LD IX,overflow',(0xdd,0x21),payload_overflow,14)
        a.label('payload_byte_ready');emit('SCF sentinel',[0x37],4)
    emit('RL B', [0xcb, 0x10], 8)
    a.label('have_bit')
    branch('JR NC,child', 0x30, 'child')
    emit('INC HL', [0x23], 6); emit('INC HL', [0x23], 6)
    absolute('JP child', 0xc3, 'child', 10)
    a.label('leaf'); emit('LD A,L', [0x7d], 4); ret()
    a.label('code_end')
    a.label('state')
    for name, size in (('source', 2), ('remaining', 2), ('bit_buffer', 1),
                       ('next_index', 1), ('high_mask', 1), ('emitted', 1)):
        a.label(name); a.emit(*bytes(size))
    if payload_overflow is not None:a.label('payload_bank');a.emit(0x14)
    a.label('state_end'); a.label('initial'); a.emit(*initial)
    a.label('end')
    return a.resolve(audio), dict(a.labels), listing


def build(data, audio, *, batch=6, total_ticks=None, preinitialized=False):
    initial, records, trees, payload = tables(data)
    blob, labels, _ = code(audio, len(records), initial, 0, 0, batch=batch,total_ticks=total_ticks)
    roots = (labels['end']+255) & ~255
    table_roots, nodes = tree_bytes(trees, roots+26)
    payload_start = roots+26+len(nodes)
    if payload_start+len(payload) > LIMIT:
        raise ValueError('resident code, lookup and payload exceed one 16-KiB bank')
    blob, labels, listing = code(audio, len(records), initial, roots, payload_start, batch=batch,total_ticks=total_ticks)
    if preinitialized:
        state=bytearray(blob)
        for key,value in (('source',payload_start),('remaining',len(records))):
            at=labels[key]-ORIGIN;state[at:at+2]=value.to_bytes(2,'little')
        state[labels['bit_buffer']-ORIGIN]=0x80
        blob=bytes(state)
    image = blob+bytes(roots-ORIGIN-len(blob))+table_roots+nodes+payload
    assert len(image) <= 16384
    return dict(origin=ORIGIN, bank=4, batch=batch, ticks=len(records),
        image_hex=image.hex(), image_sha256=sha(image), image_bytes=len(image),
        labels=labels, listing=listing, code_bytes=labels['code_end']-ORIGIN,
        state_bytes=labels['state_end']-labels['state'], initial_bytes=len(initial),
        root_address=roots, root_bytes=26, node_bytes=len(nodes),
        alignment_bytes=roots-labels['end'], payload_address=payload_start,
        payload_bytes=len(payload), payload_end=payload_start+len(payload),
        spare_bank_bytes=16384-len(image), ayh1_sha256=sha(data),
        input_bits=struct.unpack_from('<I', data, 8)[0],
        clobbers=['AF', "AF'", 'BC', 'DE', 'HL', 'IX'],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        timing_scope='Bank already mapped; caller saves, paging, IRQ, ULA, ROM and disk excluded.')


def bridge(origin, target, *, page, shadow, bank_address=None,bank=4):
    """Fixed-RAM caller, preserving all registers and the previous RAM bank.

Use the existing restartable 92-T paging helper. It merges the latest IRQ
screen bit when both entering and leaving bank 4. No code may run from a
paged-out bank. The caller owns finding 35 free fixed-RAM bytes; this module
does not assert that a test placement is available in the integrated player.
The return value is deliberately discarded, so AF and AF' both survive.
"""
    from pipelined_frame_z80 import helpers
    a, rows = MiniAssembler(origin), []
    e, n = helpers(a, rows, 'audio_bridge')
    a.label('fill')
    for name, blob, ticks in (('AF',[0xf5],11), ('BC',[0xc5],11),
                              ('DE',[0xd5],11), ('HL',[0xe5],11), ('IX',[0xdd,0xe5],15)):
        e('PUSH '+name, blob, ticks)
    e("EX AF,AF'", [0x08], 4); e("PUSH AF (save AF')", [0xf5], 11)
    e("EX AF,AF'", [0x08], 4)
    n('LD A,(page shadow)', 0x3a, shadow, 13); e('PUSH AF (page)', [0xf5], 11)
    if not 0<=bank<=7:raise ValueError('invalid resident bank')
    if bank_address is None:e(f'LD A,{0x10|bank:02x}h', [0x3e,0x10|bank], 7)
    else:n('LD A,(resident bank)',0x3a,bank_address,13)
    n('CALL page', 0xcd, page, 17)
    n('CALL resident entry', 0xcd, target, 17)
    e('POP AF (page)', [0xf1], 10); n('CALL page', 0xcd, page, 17)
    e("EX AF,AF'", [0x08], 4); e("POP AF (restore AF')", [0xf1], 10)
    e("EX AF,AF'", [0x08], 4)
    for name, blob, ticks in (('IX',[0xdd,0xe1],14), ('HL',[0xe1],10),
                              ('DE',[0xd1],10), ('BC',[0xc1],10), ('AF',[0xf1],10)):
        e('POP '+name, blob, ticks)
    e('RET', [0xc9], 10)
    if not 0x4000 <= origin < a.pc <= 0xc000:
        raise ValueError('resident bridge requires fixed RAM')
    blob = a.resolve()
    return dict(origin=origin, code_hex=blob.hex(), code_bytes=len(blob), labels=a.labels,
        listing=[dict(row, stage='bridge') for row in rows],
        overhead_tstates=sum(row['tstates'] for row in rows)+2*92,
        scope='Includes RET, two 92-T paging calls and resident CALL; excludes resident body and outer CALL. An IRQ restarting paging adds re-executed foreground instructions.')
