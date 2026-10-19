"""Independent oversized LZSA2 token-dispatch experiment, not a public profile.

A 512-byte two-page table selects a complete XYZ/LL/MMM specialization.
EXX lends HL' to the lookup while preserving input HL; the raw entry saves
the caller's alternate HL once. Handlers restore the main register set before
input/output work. This tests a speed bound with all table/handler bytes counted.
"""
from lzsa._z80 import MiniAssembler


def build(*, core=0x8000, core_limit=0xc000, shared_literals=False):
    table = (core+255)&~255
    a = MiniAssembler(core)
    a.emit(*([0]*(table-core+512)))
    def emit(*code): a.emit(*code)
    def jp(op, label): a.abs16(op, label)
    def jr(op, label): a.rel8(op, label)
    def inc(): emit(0x23)
    def ldi(): emit(0xed, 0xa0)
    def ldir(): emit(0xed, 0xb0)
    def nibble(label):
        # Main carry=1 marks the old cached nibble consumed. AF' is retained
        # across EXX and IRQ probes; high-nibble refills advance input once.
        emit(0x37, 8);jr(0x30, label)
        emit(0x7e, 0xb7, 8, 0x7e);inc()
        emit(0x0f, 0x0f, 0x0f, 0x0f)
        a.label(label);emit(0xf6, 0xf0)
    a.label('start')
    emit(0xd9, 0xe5, 0xd9, 0x06, 0, 0x37, 8)
    jp(0xc3, 'ReadToken')
    a.label('LongerMatch')
    nibble('LongMatchNibble')
    emit(0xd6, 231, 0xfe, 24);jp(0xda, 'CopyMatchA')
    emit(0x86);inc();jp(0xd2, 'CopyMatchA');jp(0xca, 'done')
    emit(0x4e);inc();emit(0x46);inc();jp(0xc3, 'MatchUseC')
    a.label('CopyMatchA');emit(0x4f)
    a.label('MatchUseC');emit(0xe5)
    a.labels['offset'] = a.pc+1;emit(0x21, 0, 0, 0x19)
    ldi();ldir();emit(0xe1)
    a.label('ReadToken')
    # Lookup: 54 T including token fetch/advance, followed by handler EXX 4 T.
    # Only HL' is scratch. Two pages contain the target low and high bytes.
    emit(0x7e);inc();emit(0xd9, 0x6f, 0x26, table>>8,
        0x7e, 0x24, 0x66, 0x6f, 0xe9)
    a.label('done');emit(0xd9, 0xe1, 0xd9, 0xc9)
    a.label('LongLiterals')
    nibble('LongLiteralNibble')
    emit(0x3c);jr(0x28, 'ManyLiterals');emit(0xd6, 238, 0x4f)
    ldi();ldi();ldir();emit(0xc9)
    a.label('ManyLiterals');emit(0x3e, 18, 0x86);inc()
    jr(0x38, 'WordLiterals');emit(0x4f);ldir();emit(0xc9)
    a.label('WordLiterals');emit(0x4e);inc();emit(0x46);inc();ldir();emit(0xc9)
    handlers = [None]*256
    def literal_prefix(literal, cls):
        if literal in (1, 2):
            # A following new-offset parser replaces both B and C before
            # match copying, so the fixed one/two LDIs may wrap BC from zero.
            # No PV/count test consumes that temporary value. Repeat-offset
            # tokens need B=0 and retain the explicit literal count.
            if cls == 7: emit(0x0e, literal)
            for _ in range(literal): ldi()
        elif literal == 3:
            jp(0xcd, 'LongLiterals')
    def token_body(token):
        cls = token>>5
        if cls in (0, 1):
            nibble('nibble_'+str(token));emit(0x87)
            if cls == 0: emit(0x3c)
            emit(0x4f, 0x06, 255)
        elif cls in (2, 3):
            emit(0x06, 255 if cls == 2 else 254, 0x4e);inc()
        elif cls in (4, 5):
            nibble('nibble_'+str(token));emit(0x3d, 0x87)
            if cls == 4: emit(0x3c)
            emit(0x47, 0x4e);inc()
        elif cls == 6:
            emit(0x46);inc();emit(0x4e);inc()
        if cls != 7:
            a.abs16((0xed, 0x43), 'offset');emit(0x06, 0)
        length = token&7
        if length == 7:
            jp(0xc3, 'LongerMatch')
        else:
            emit(0x0e, length+2);jp(0xc3, 'MatchUseC')
    if shared_literals:
        # Share offset/length bodies across the four LL forms. The most
        # frequent prefix (zero literals) falls through; nonempty literal
        # prefixes pay a 10-T jump to the same body.
        for cls in range(8):
            for length in range(8):
                token = (cls<<5)|length
                body = 'body_'+str(token)
                for literal in (1, 2, 3, 0):
                    value = token|(literal<<3)
                    a.label('token_'+str(value));handlers[value]=a.pc;emit(0xd9)
                    literal_prefix(literal, cls)
                    if literal != 0: jp(0xc3, body)
                a.label(body);token_body(token)
    else:
        for token in range(256):
            a.label('token_'+str(token));handlers[token]=a.pc;emit(0xd9)
            literal_prefix((token>>3)&3, token>>5);token_body(token)
    assert a.pc <= core_limit, ('oversized decoder', a.pc-core)
    blob = bytearray(a.resolve())
    for token, target in enumerate(handlers):
        blob[table-core+token] = target&255
        blob[table-core+256+token] = target>>8
    return [(core, bytes(blob))], a.labels, dict(entry='start', variant='full-token-experiment',
        one_shot=True, code_bytes=len(blob), table_bytes=512, alignment_padding=table-core,
        shared_literal_bodies=shared_literals,
        core_end=a.pc, state_bytes=0, private_stack_bytes=0,
        patched_addresses=[a.labels['offset'], a.labels['offset']+1],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
