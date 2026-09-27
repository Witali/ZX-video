"""Finer motion-cache maps in the resident-AY player's existing RAM layout.

Retains the old paired full-row copier. A selector uses retired fixed RAM
after the audio initializer; a half-row copier uses the retired initializer.
The old cache selector becomes a tail jump and a five-LDI packet helper.
No existing generator or default packet format is changed.
"""
import numpy as np

from build_zxv_trd import MiniAssembler
from pipelined_frame_z80 import helpers
from probe_sparse_motion_cache import coverage
from build_fap3_trd import sha

SELECTOR, HALF, SELECTOR_END, HALF_END = 0x7823, 0x7b00, 0x78a0, 0x7b58


def map_for(vectors, old):
    fine = coverage(vectors, 8).reshape(24, 4, 4).any(axis=1)
    pairs = fine.reshape(24, 2, 2).any(axis=2)
    if np.packbits(pairs.any(axis=1)).tobytes() != old:
        raise ValueError('original cache map differs from motion coverage')
    return np.packbits(pairs).tobytes()


def widen(body):
    if len(body) < 288:
        raise ValueError('short video-only packet')
    return body[:5]+map_for(body[8:200], body[5:8])+body[8:]


def narrow(body):
    if len(body) < 291:
        raise ValueError('short half-row packet')
    pairs = np.unpackbits(np.frombuffer(body[5:11], dtype=np.uint8)).reshape(24, 2)
    return body[:5]+np.packbits(pairs.any(axis=1)).tobytes()+body[11:]


def copy_tstates(pairs):
    """Twelve calls covering 24 groups, including new entry JPs, not CALLs."""
    values = np.asarray(pairs, dtype=np.uint8).reshape(24, 2)
    counts = np.bincount(values[:, 0]*2+values[:, 1], minlength=4)
    return 4998+1436*int(counts[1])+1373*int(counts[2])+2234*int(counts[3])


def install_stage(h):
    """Install only cache code in the compiled-mask, relocated CPU fixture."""
    if h.metadata_mode != 'compiled': raise ValueError('fixed metadata space must be retired')
    c = h.cpu; c.guarding = False
    regions, labels, rows = build(h.recon)
    regions.append((h.recon['cache_copy'], b'\xc3'+SELECTOR.to_bytes(2, 'little')))
    rows.append(dict(address=h.recon['cache_copy'], instruction='JP half-row selector',
                     tstates=10, phase='reconstruct', stage='half_row_cache'))
    for address, code in regions:
        for i, value in enumerate(code): c.write8(address+i, value)
    for row in rows:
        h.instructions[row['address']] = dict(row, phase='reconstruct', stage='half_row_cache')
    h.cache_map_bytes = 6
    return dict(labels=labels, regions=[dict(address=a, code_hex=b.hex()) for a, b in regions])


def build(labels, *, cache_page=0xa4):
    """Return two bounded code regions and a listing with instruction costs."""
    a, rows = MiniAssembler(SELECTOR), []
    e, n = helpers(a, rows, 'half_row_cache')

    def jr(name, opcode, target):
        rows.append(dict(address=a.pc, instruction=name, tstates=[7, 12], phase='half_row_cache'))
        a.rel8(opcode, target)

    a.label('copy')
    e('PUSH BC', [0xc5], 11)
    n('LD A,(cache_mask_shift)', 0x3a, labels['cache_mask_shift'], 13)
    e('ADD A,A', [0x87], 4); jr('JR NZ,ready', 0x20, 'ready')
    e('PUSH HL', [0xe5], 11)
    n('LD HL,(cache_mask_source)', 0x2a, labels['cache_mask_source'], 16)
    e('LD A,(HL)', [0x7e], 7); e('INC HL', [0x23], 6)
    n('LD (cache_mask_source),HL', 0x22, labels['cache_mask_source'], 16)
    e('POP HL', [0xe1], 10); e('ADC A,A', [0x8f], 4)
    a.label('ready')
    e('LD C,0', [0x0e, 0], 7); e('RL C', [0xcb, 0x11], 8)
    e('ADD A,A', [0x87], 4); e('RL C', [0xcb, 0x11], 8)
    n('LD (cache_mask_shift),A', 0x32, labels['cache_mask_shift'], 13)
    e('LD A,C', [0x79], 4); e('OR A', [0xb7], 4)
    jr('JR Z,skip', 0x28, 'skip')
    e('CP 3', [0xfe, 3], 7); n('JP NZ,half', 0xc2, HALF, 10)
    # Existing full copier sets B=2 itself; no redundant LD B,4 here.
    n('CALL paired full rows', 0xcd, labels['cache_copy_rows'], 17)
    rows.append(dict(address=a.pc, instruction='JR done', tstates=12, phase='half_row_cache'))
    a.rel8(0x18, 'done')
    a.label('skip'); n('LD BC,128', 0x01, 128, 10); e('ADD HL,BC', [0x09], 11)
    e('INC D', [0x14], 4); e('LD A,D', [0x7a], 4)
    e('AND 3', [0xe6, 3], 7); e('OR cache page', [0xf6, cache_page], 7); e('LD D,A', [0x57], 4)
    a.label('done'); e('POP BC', [0xc1], 10)
    e('LD A,B', [0x78], 4); e('SUB 4', [0xd6, 4], 7); e('LD B,A', [0x47], 4)
    n('JP NZ,copy', 0xc2, 'copy', 10); e('RET', [0xc9], 10)
    a.label('selector_end')
    if a.pc > SELECTOR_END: raise ValueError('selector exceeds retired metadata space')
    regions = [(SELECTOR, a.resolve())]; out = dict(a.labels)

    a = MiniAssembler(HALF)
    e, n = helpers(a, rows, 'half_row_cache')
    a.label('half'); e('LD B,4', [0x06, 4], 7)
    e('CP 1', [0xfe, 1], 7); jr('JR NZ,row', 0x20, 'row')
    for reg, opcode in (('L', 0x7d), ('E', 0x7b)):
        e('LD A,'+reg, [opcode], 4); e('ADD A,16', [0xc6, 16], 7)
        e('LD '+reg+',A', [0x6f if reg == 'L' else 0x5f], 4)
    a.label('row'); e('PUSH BC', [0xc5], 11)
    for _ in range(16): e('LDI half-row byte', [0xed, 0xa0], 16)
    n('LD BC,16', 0x01, 16, 10); e('ADD HL,BC', [0x09], 11); e('POP BC', [0xc1], 10)
    e('LD A,E', [0x7b], 4); e('ADD A,48', [0xc6, 48], 7); e('LD E,A', [0x5f], 4)
    jr('JR NC,page_ready', 0x30, 'page_ready')
    e('INC D', [0x14], 4); e('LD A,D', [0x7a], 4)
    e('AND 3', [0xe6, 3], 7); e('OR cache page', [0xf6, cache_page], 7); e('LD D,A', [0x57], 4)
    a.label('page_ready')
    rows.append(dict(address=a.pc, instruction='DJNZ row', tstates=[8, 13], phase='half_row_cache'))
    a.rel8(0x10, 'row')
    e('DEC C', [0x0d], 4); n('JP NZ,done', 0xc2, out['done'], 10)
    n('LD BC,-16', 0x01, 65520, 10); e('ADD HL,BC', [0x09], 11)
    e('LD E,1', [0x1e, 1], 7); n('JP done', 0xc3, out['done'], 10)
    a.label('half_end')
    if a.pc > HALF_END: raise ValueError('half copier exceeds retired initializer space')
    regions.append((HALF, a.resolve())); out.update(a.labels)
    return regions, out, rows


def install(read8, put, m):
    if not m.get('resident_audio', {}).get('foreground_audio'):
        raise ValueError('requires measured foreground resident AY baseline')
    recon = m['cached_huffman_lookahead']['implementation']['labels']
    origin, end = recon['cache_copy'], recon['cache_copy_rows']
    original = bytes(read8(i) for i in range(origin, end))
    if not original.startswith(b'\xc5\x3a') or read8(end) != 0x06 or read8(end+1) != 2:
        raise ValueError('expected existing paired cache copier')
    regions, labels, rows = build(recon)
    for address, code in regions:
        if any(read8(i) for i in range(address, address+len(code))):
            raise ValueError(('retired space is occupied', hex(address)))
        put(address, code)
    helper = origin+3
    replacement = b'\xc3'+SELECTOR.to_bytes(2, 'little')+b'\xed\xa0'*5+b'\xc9'
    if len(replacement) > end-origin: raise ValueError('old selector too small')
    put(origin, replacement+bytes(end-origin-len(replacement)))
    rows += [dict(address=origin, instruction='JP half-row selector', tstates=10, phase='half_row_cache')]
    rows += [dict(address=helper+2*i, instruction='LDI cache map', tstates=16, phase='half_row_parser') for i in range(5)]
    rows += [dict(address=helper+10, instruction='RET cache map', tstates=10, phase='half_row_parser')]

    # The cache-map copy has a unique LD DE,BA40 / LD BC,3 / three-LDI prefix.
    p = m['packet_labels']; blob = bytes(read8(i) for i in range(p['read_packet'], p['end']))
    signature = b'\x11\x40\xba\x01\x03\x00'+b'\xed\xa0'*3
    if blob.count(signature) != 1: raise ValueError('cache-map parser layout differs')
    at = p['read_packet']+blob.index(signature)
    before = bytes(read8(at+i) for i in range(12))
    after = b'\x11\x40\xba\x01\x06\x00'+b'\xcd'+helper.to_bytes(2, 'little')+b'\xed\xa0\x00'
    put(at, after)
    parser_rows = [dict(address=at+6, instruction='CALL copy five map bytes', tstates=17, phase='half_row_parser'),
                   dict(address=at+9, instruction='LDI sixth map byte', tstates=16, phase='half_row_parser'),
                   dict(address=at+11, instruction='NOP map padding', tstates=4, phase='half_row_parser')]
    patches = [dict(address=at, before_hex=before.hex(), code_hex=after.hex(),
                    previous_tstates=68, tstates=147, delta_tstates=79)]
    seen = set()
    for row in m['slot_queue_instruction_listing']:
        target = {'LD DE,minimum length': (288, 291),
                  'LD DE,valid length range': (4702-288+1, 4702-291+1),
                  'LD DE,cache+vectors+map+guards': (275, 278)}.get(row['instruction'])
        pc = row['address']
        if target and p['read_packet'] <= pc < p['end'] and pc not in seen:
            old, new = target; seen.add(pc)
            expected = b'\x11'+old.to_bytes(2, 'little')
            if bytes(read8(pc+i) for i in range(3)) != expected:
                raise ValueError(('unexpected packet bound', row))
            coded = b'\x11'+new.to_bytes(2, 'little'); put(pc, coded)
            patches.append(dict(address=pc, before_hex=expected.hex(), code_hex=coded.hex(),
                                previous_tstates=10, tstates=10, delta_tstates=0))
    if len(seen) != 3: raise ValueError('missing packet bound patch')
    m['slot_queue_instruction_listing'] = [r for r in m['slot_queue_instruction_listing']
        if not origin <= r['address'] < end and not at+6 <= r['address'] < at+12]+rows+parser_rows
    m['half_row_cache'] = dict(enabled=True, map_bytes=6, previous_map_bytes=3,
        selector_origin=SELECTOR, half_origin=HALF, labels=labels,
        regions=[dict(address=address, code_hex=code.hex()) for address, code in regions],
        old_selector_sha256=sha(original), replaced_selector_origin=origin,
        replaced_selector_hex=(replacement+bytes(end-origin-len(replacement))).hex(),
        packet_patches=patches, cache_entry_extra_tstates=10,
        parser_delta_tstates=79, additional_map_bytes_per_frame=3,
        unchanged_full_row_helper=recon['cache_copy_rows'],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        timing_excludes=['IRQ', 'ULA', 'TR-DOS ROM', 'disk latency'])
    return m['half_row_cache']
