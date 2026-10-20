"""Test-only short-match specialization copied from the public Wide generator.

A 512-byte two-page table selects a complete XYZ/LL/MMM specialization.
EXX lends HL' to the lookup while preserving input HL; the raw entry saves
the caller's alternate HL once. Handlers restore the main register set before
input/output work. Standard raw-v2 payloads and exact byte EOF are retained.
Derived from the measured independent full-token experiment and the adapted
spke/uniabis fast nibble reader; see the package zlib LICENSE and provenance.
"""
from lzsa._z80 import MiniAssembler

STORAGE_BUDGET = 10000
CALLER_STACK_BYTES = 6


def emit_new_offset_short(a, token, length):
    """BC=negative offset, HL=input, DE=output; return to ReadToken with BC=0.

    The one original offset store is preserved. Save5*n-4 T relative to the
    current Expanded path; add4+2*n code bytes. No additional SMC site or stack.
    """
    a.label('short_ready_'+str(token))
    a.abs16((0xed,0x43),'offset');a.emit(0xe5,0x60,0x69,0x01);a.word(length)
    a.emit(0x19)
    for _ in range(length):a.emit(0xed,0xa0)
    a.emit(0xe1);a.abs16(0xc3,'ReadToken')


def emit_repeat_short(a, token, length):
    """B=0, HL=input, DE=output; inline repeated-offset n-LDI kernel.

    Delta16-5*n T versus Expanded, code growth6+2*n bytes. Length2/3 lose
    6/1 T; length4..8 save4/9/14/19/24 T. Use only explicit selected lengths.
    """
    a.label('short_ready_'+str(token))
    a.emit(0x0e,length,0xe5);a.abs16(0x2a,'offset');a.emit(0x19)
    for _ in range(length):a.emit(0xed,0xa0)
    a.emit(0xe1);a.abs16(0xc3,'ReadToken')


def build(*, core=0x8000, core_limit=0xc000, shared_literals=False,
          _boundary=None, _external_labels=None, _literal_guards=False,
          short_lengths=range(2,9), skip_tokens=(), repeat_lengths=(),
          allow_oversize=False):
    """Return resident regions/labels/metadata; no input or output bounds checks.

    Call start with HL=input, DE=output and a valid caller stack. AF/AF'/BC/
    DE/HL are clobbered. IX/IY and the other alternate pairs, including HL',
    are preserved. Reserve six caller-stack bytes including the return word,
    plus actual IRQ headroom. IRQ must preserve both main and alternate live
    registers: HL' temporarily holds a dispatch address between the EXXs.
    Code and offset operand must be writable and nonreentrant. Retain the
    complete source/history; output must not wrap. Caller validates the block.
    Service memory (code/tables/alignment/state/stack/scratch) obeys a 10,000-
    byte cap. Compressed input and complete output/history are separate caller
    buffers. Add actual hardware-return/IRQ-handler stack headroom separately.
    """
    if not (0 <= core < core_limit <= 65536):
        raise ValueError('invalid wide code reservation')
    short_lengths=frozenset(short_lengths)
    repeat_lengths=frozenset(repeat_lengths)
    skip_tokens=frozenset(skip_tokens)
    if not short_lengths<=set(range(2,9)) or not repeat_lengths<=set(range(2,9)):
        raise ValueError('short kernels require token lengths 2..8')
    table = (core+255)&~255
    a = MiniAssembler(core)
    a.emit(*([0]*(table-core)))
    a.label('dispatch_low');a.emit(*([0]*256))
    a.label('dispatch_high');a.emit(*([0]*256))
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
    if _boundary is not None: _boundary(a)
    a.label('token_body')
    # Lookup: 54 T including token fetch/advance, followed by handler EXX 4 T.
    # Only HL' is scratch. Two pages contain the target low and high bytes.
    emit(0x7e);inc();emit(0xd9, 0x6f, 0x26, table>>8,
        0x7e, 0x24, 0x66, 0x6f, 0xe9)
    # EOD is recognized before any dummy word fetch. The saved alternate HL
    # belongs to the caller even if no match/literal has ever been copied.
    a.label('done');emit(0xd9, 0xe1, 0xd9, 0xc9)
    a.label('LongLiterals')
    nibble('LongLiteralNibble')
    emit(0x3c);jr(0x28, 'ManyLiterals');emit(0xd6, 238, 0x4f)
    ldi();ldi();ldir();emit(0xc9)
    a.label('ManyLiterals');emit(0x3e, 18, 0x86);inc()
    jr(0x38, 'WordLiterals');emit(0x4f)
    if _literal_guards:
        # The token prefix protects <=17 literals. Byte/word long forms
        # suspend with BC=count and HL=literal source until extent+7 is read.
        a.labels['long8_target']=a.pc+1;jp(0xc3, 'guard_long8')
    a.label('long8_complete');ldir();emit(0xc9)
    a.label('WordLiterals');emit(0x4e);inc();emit(0x46);inc()
    if _literal_guards:
        a.labels['long16_target']=a.pc+1;jp(0xc3, 'guard_long16')
    a.label('long16_complete');ldir();emit(0xc9)
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
        length = token&7
        n=length+2
        if cls != 7 and n in short_lengths and token not in skip_tokens:
            # BC still contains the complete negative offset. Preserve the
            # existing SMC store for subsequent repeats, then move BC to HL
            # before LD BC,n clears the high count and installs the low count.
            # Relative to clear-B/LDC/JP/common immediate load, this saves6 T
            # even for n=2; each removed LDIR repeat saves another5 T.
            emit_new_offset_short(a,token,n);return
        if cls == 7 and n in repeat_lengths and token not in skip_tokens:
            # B=0 at repeat entry. The shared SMC operand is read as data
            # (+6 T); these inline kernels break even only at n>=4.
            emit_repeat_short(a,token,n);return
        if cls != 7:
            a.abs16((0xed, 0x43), 'offset');emit(0x06, 0)
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
    if a.pc > core_limit:
        raise ValueError('wide LZSA2 exceeds core-limit; reserve table and handler code explicitly')
    if a.pc-core+CALLER_STACK_BYTES > STORAGE_BUDGET and not allow_oversize:
        raise ValueError('wide LZSA2 exceeds the total 10000-byte code/table/alignment/stack budget')
    blob = bytearray(a.resolve(_external_labels))
    for token, target in enumerate(handlers):
        blob[table-core+token] = target&255
        blob[table-core+256+token] = target>>8
    return [(core, bytes(blob))], a.labels, dict(entry='start', variant='wide-shared-block' if shared_literals else 'wide-block',
        one_shot=True, code_bytes=len(blob), table_bytes=512, alignment_padding=table-core,
        shared_literal_bodies=shared_literals,
        wide_short_experiment=True,short_lengths=sorted(short_lengths),
        skip_tokens=sorted(skip_tokens),repeat_lengths=sorted(repeat_lengths),
        test_only_oversize=allow_oversize,
        budget_valid=a.pc-core+CALLER_STACK_BYTES<=STORAGE_BUDGET,
        full_token_dispatch=True, token_handlers=256,
        storage_budget_bytes=STORAGE_BUDGET, total_storage_bytes=len(blob)+CALLER_STACK_BYTES,
        service_memory_bytes=len(blob)+CALLER_STACK_BYTES,
        service_memory=dict(code_tables_alignment_bytes=len(blob),
            embedded_mutable_bytes=2, external_state_bytes=0,
            caller_stack_bytes=CALLER_STACK_BYTES, scratch_bytes=0, internal_buffer_bytes=0),
        storage_budget_scope='service code/tables/alignment/state/decoder stack/scratch/internal buffers',
        external_buffers='complete compressed input plus complete decoded output/history; counted separately',
        irq_headroom='add actual hardware-return and register-preserving handler stack separately',
        caller_stack_bytes=CALLER_STACK_BYTES, decoder_stack_bytes=CALLER_STACK_BYTES-2,
        core_end=a.pc, state_bytes=0, private_stack_bytes=0,
        patched_addresses=[a.labels['offset'], a.labels['offset']+1],
        dispatch_tstates=58, alternate_hl_preservation_tstates=37,
        upstream_commit='15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
