"""Assemble upstream ZX0, with optional bounded-copy and input-paging hooks.

Upstream: einar-saukas/ZX0, ecde3a2ae05061fe06469ed46df81a33b7de7d86.
Decoder/reference algorithm copyright (c) 2021 Einar Saukas. All rights reserved.
See third_party/zx0/LICENSE for the BSD-3-Clause conditions and disclaimer.
"""
from pathlib import Path


def decompress(data: bytes, limit: int = 8192, *, on_match=None, on_literals=None) -> bytes:
    """ZX0 v2 reference decoder, adapted from Einar Saukas' BSD-licensed dzx0.c."""
    position = 0
    mask = value = last_byte = 0
    backtrack = False
    output = bytearray()

    def byte():
        nonlocal position, last_byte
        if position >= len(data): raise ValueError('truncated ZX0 data')
        last_byte = data[position]; position += 1
        return last_byte

    def bit():
        nonlocal backtrack, mask, value
        if backtrack:
            backtrack = False
            return last_byte & 1
        mask >>= 1
        if not mask: mask = 128; value = byte()
        return int(bool(value & mask))

    def gamma(inverted=0):
        result = 1
        while not bit():
            result = (result << 1) | (bit() ^ inverted)
            if result > 65535: raise ValueError('oversized ZX0 gamma value')
        return result

    def copy(offset, length):
        if not 0 < offset <= len(output) or len(output)+length > limit:
            raise ValueError('invalid ZX0 match')
        if on_match is not None: on_match(len(output), offset, length)
        for _ in range(length): output.append(output[-offset])

    offset = 1
    mode = 'literal'
    while True:
        if mode == 'literal':
            length = gamma()
            if len(output)+length > limit: raise ValueError('oversized ZX0 output')
            if on_literals is not None: on_literals(len(output), length)
            for _ in range(length): output.append(byte())
            if not bit():
                copy(offset, gamma())
                if not bit(): continue
        offset = gamma(1)
        if offset == 256:
            if position != len(data): raise ValueError('trailing ZX0 bytes')
            return bytes(output)
        offset = offset*128-(byte() >> 1)
        backtrack = True
        copy(offset, gamma()+1)
        mode = 'offset' if bit() else 'literal'


def emit_decoder(a, variant="turbo", *, copy_hook=None, literal_hook=None, source_wrap=None, source_page_wrap=None, label_prefix="", inline_match=None):
    if variant not in ("standard", "turbo"):
        raise ValueError(variant)
    if copy_hook and variant != 'turbo': raise ValueError('suspension requires turbo')
    if source_wrap and source_page_wrap:
        raise ValueError('choose one source wrap mode')
    if (literal_hook or source_wrap or source_page_wrap) and not copy_hook:
        raise ValueError('input paging requires the bounded turbo copier')
    if inline_match and not copy_hook: raise ValueError('inline match requires a bounded copy hook')
    source = Path(__file__).parent / 'third_party/zx0' / f'dzx0_{variant}.asm'
    start = a.pc
    simple = {
        'push bc': (0xC5,), 'push hl': (0xE5,), 'pop bc': (0xC1,), 'pop hl': (0xE1,),
        'inc bc': (0x03,), 'inc c': (0x0C,), 'inc hl': (0x23,),
        'ldir': (0xED,0xB0), 'add a,a': (0x87,), 'add hl,de': (0x19,),
        'ex (sp),hl': (0xE3,), 'ld b,c': (0x41,), 'ld c,(hl)': (0x4E,),
        'ld a,(hl)': (0x7E,), 'rr b': (0xCB,0x18), 'rr c': (0xCB,0x19),
        'rl b': (0xCB,0x10), 'rl c': (0xCB,0x11), 'rla': (0x17,),
        'ret': (0xC9,), 'ret z': (0xC8,), 'ret nz': (0xC0,), 'ret c': (0xD8,),
    }
    aliases = {}; copy_index=0; inline_delta=0
    for original in source.read_text().splitlines():
        line = ' '.join(original.split(';')[0].strip().split()).replace(', ', ',')
        if not line: continue
        if label_prefix:line=line.replace("dzx0",label_prefix+"dzx0")
        if line == 'ldir' and copy_hook:
            if not copy_index and inline_match:
                before=a.pc; inline_match(a); inline_delta=a.pc-before-3
            else: a.abs16(0xCD,literal_hook if copy_index and literal_hook else copy_hook)
            copy_index+=1;continue
        if line == 'inc hl' and source_wrap:
            a.emit(0x23,0xCB,0x7C);a.abs16(0xCC,source_wrap);continue
        if line == 'inc hl' and source_page_wrap:
            # A 256-byte aligned fixed input window: preserve carry, return
            # to low byte zero and refill before the next input access.
            a.emit(0x2c);a.abs16(0xCC,source_page_wrap);continue
        if line.endswith(':'):
            a.label(line[:-1]); continue
        if line in simple:
            a.emit(*simple[line]); continue
        instruction, operands = line.split(' ', 1)
        if instruction in ('call', 'jr', 'jp'):
            condition, label = operands.split(',',1) if ',' in operands else ('', operands)
            opcodes = {'call': {'':0xCD,'nc':0xD4},
                       'jr': {'':0x18,'c':0x38,'nc':0x30,'nz':0x20},
                       'jp': {'':0xC3,'nz':0xC2}}
            (a.rel8 if instruction == 'jr' else a.abs16)(opcodes[instruction][condition],label)
        elif instruction == 'ld':
            dest, value = operands.split(',')
            if dest.startswith('(') and value == 'bc':
                expression = dest[1:-1]
                label, offset = expression.split('+')
                aliases[expression]=(label,int(offset))
                a.abs16((0xED,0x43),expression)
            else:
                number = int(value[1:],16) if value.startswith('$') else int(value)
                a.emit({'bc':0x01,'hl':0x21,'c':0x0E,'a':0x3E}[dest])
                if dest in ('bc','hl'): a.word(number)
                else: a.emit(number)
        else:
            raise ValueError(f'unsupported ZX0 instruction: {line}')
    for alias,(label,offset) in aliases.items(): a.labels[alias]=a.labels[label]+offset
    assert a.pc-start == {'standard':68,'turbo':126}[variant]+(2 if copy_hook else 0)+(30 if source_wrap else 0)+(18 if source_page_wrap else 0)+inline_delta
    return f'{label_prefix}dzx0_{variant}'
