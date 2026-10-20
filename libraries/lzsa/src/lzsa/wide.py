"""Wide raw LZSA2 decoders with complete token specialization.

A 512-byte two-page table selects a complete XYZ/LL/MMM specialization.
EXX lends HL' to the lookup while preserving input HL; the raw entry saves
the caller's alternate HL once. Handlers restore the main register set before
input/output work. Standard raw-v2 payloads and exact byte EOF are retained.
Derived from the measured independent full-token experiment and the adapted
spke/uniabis fast nibble reader; see the package zlib LICENSE and provenance.
"""
from ._z80 import MiniAssembler

STORAGE_BUDGET = 10000
CALLER_STACK_BYTES = 6


def build(*, core=0x8000, core_limit=0xc000, shared_literals=False,
          short_lengths=(), repeat_lengths=(), cold_match_extension=False,
          _boundary=None, _external_labels=None, _literal_guards=False,
          _groups_by_body=None, _fallthrough_order=None):
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
    Optional new-offset short_lengths2..8 and repeat_lengths4..8 specialize
    only known token lengths. Word-escaped counts keep their existing path.
    These options and internal grouped layouts are raw-only; quota/guard hooks
    are rejected until their complete feature-equivalent profiles are proved.
    cold_match_extension moves the byte/word/EOF length escape after the raw
    return, so nibble-length matches fall through a shorter conditional JR.
    It is raw-only and restricted to the six qualified fixed Wide selections
    (plain Expanded/Shared, Shared new2..8 with/without repeat4..8, Expanded
    new3..8 or new2..8), plus the internal fixed Hybrid layouts.
    """
    if not (0 <= core < core_limit <= 65536):
        raise ValueError('invalid wide code reservation')
    try:
        short_lengths=frozenset(short_lengths);repeat_lengths=frozenset(repeat_lengths)
    except TypeError as error:
        raise ValueError('short length options must be integer iterables') from error
    if (any(type(n) is not int for n in short_lengths|repeat_lengths) or
            not short_lengths<=set(range(2,9)) or not repeat_lengths<=set(range(4,9))):
        raise ValueError('new-offset lengths 2..8 and positive-gain repeats 4..8 only')
    grouped_layout=_groups_by_body is not None or _fallthrough_order is not None
    if type(cold_match_extension) is not bool:
        raise ValueError('cold_match_extension must be bool')
    if (short_lengths or repeat_lengths or grouped_layout or cold_match_extension) and (
            _boundary is not None or _external_labels is not None or _literal_guards):
        raise ValueError('short/grouped Wide profiles require fully resident raw input without wrapper hooks')
    if cold_match_extension and not grouped_layout:
        qualified={(False,frozenset(),frozenset()),(True,frozenset(),frozenset()),
            (True,frozenset(range(2,9)),frozenset()),
            (True,frozenset(range(2,9)),frozenset(range(4,9))),
            (False,frozenset(range(3,9)),frozenset()),
            (False,frozenset(range(2,9)),frozenset())}
        if (bool(shared_literals),short_lengths,repeat_lengths) not in qualified:
            raise ValueError('cold match extension requires a qualified fixed Wide or Hybrid selection')
    groups_by_body={int(k):tuple(tuple(g) for g in v) for k,v in (_groups_by_body or {}).items()}
    fallthrough_order={int(k):tuple(v) for k,v in (_fallthrough_order or {}).items()}
    bases={(cls<<5)|length for cls in range(8) for length in range(8)}
    if not (set(groups_by_body)|set(fallthrough_order))<=bases:
        raise ValueError('internal group selectors require XYZ/MMM body bases')
    if any(sorted(rank)!=[0,1,2,3] for rank in fallthrough_order.values()):
        raise ValueError('internal fallthrough ranks must contain every literal form exactly once')
    for selected in groups_by_body.values():
        if sorted(v for group in selected for v in group)!=[0,1,2,3] or any(not group for group in selected):
            raise ValueError('internal groups must partition all four literal forms exactly once')
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
    def extended_match():
        # A>=24 is a byte escape, exact EOF, or a little-endian word count.
        # Preserve carry/Z until their existing exits; B/C and the offset
        # operand keep the ordinary copy ABI, including legal short words.
        emit(0x86);inc();jp(0xd2, 'CopyMatchA');jp(0xca, 'done')
        emit(0x4e);inc();emit(0x46);inc();jp(0xc3, 'MatchUseC')
    a.label('start')
    emit(0xd9, 0xe5, 0xd9, 0x06, 0, 0x37, 8)
    jp(0xc3, 'ReadToken')
    a.label('LongerMatch')
    nibble('LongMatchNibble')
    emit(0xd6, 231, 0xfe, 24)
    if cold_match_extension:
        # Hot nibble lengths use JR not-taken7 instead of JP10; escapes pay
        # JR taken12. Moving the intact escape costs no additional exit jump
        # and removes one byte. Both branch forms preserve the tested flags.
        jr(0x30, 'ColdExtendedMatch')
    else:
        jp(0xda, 'CopyMatchA');extended_match()
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
    if cold_match_extension:
        a.label('ColdExtendedMatch');extended_match()
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
            nibble('nibble_'+str(token)+('_'+str(a.pc) if grouped_layout else ''));emit(0x87)
            if cls == 0: emit(0x3c)
            emit(0x4f, 0x06, 255)
        elif cls in (2, 3):
            emit(0x06, 255 if cls == 2 else 254, 0x4e);inc()
        elif cls in (4, 5):
            nibble('nibble_'+str(token)+('_'+str(a.pc) if grouped_layout else ''));emit(0x3d, 0x87)
            if cls == 4: emit(0x3c)
            emit(0x47, 0x4e);inc()
        elif cls == 6:
            emit(0x46);inc();emit(0x4e);inc()
        length = token&7
        n=length+2
        context=str(token)+'_'+str(a.pc) if grouped_layout else token
        if cls!=7 and n in short_lengths:
            from ._wide_kernels import emit_new_offset_short
            emit_new_offset_short(a,context,n);return
        if cls==7 and n in repeat_lengths:
            from ._wide_kernels import emit_repeat_short
            emit_repeat_short(a,context,n);return
        if cls != 7:
            a.abs16((0xed, 0x43), 'offset');emit(0x06, 0)
        if length == 7:
            jp(0xc3, 'LongerMatch')
        else:
            emit(0x0e, length+2);jp(0xc3, 'MatchUseC')
    shared_hit_tokens=[];body_layout=[]
    if grouped_layout:
        # Every group retains its unchanged literal parser. One member falls
        # through; other shared hits pay JP10. Singletons are fully specialized.
        # Groups and ranking are fixed package data, never input-dependent.
        for cls in range(8):
            for length in range(8):
                token=(cls<<5)|length
                selected=groups_by_body.get(token,((0,1,2,3),))
                emitted=[]
                for group_index,members in enumerate(selected):
                    rank=fallthrough_order.get(token,(0,1,2,3))
                    last=next(v for v in rank if v in members)
                    body=f'body_{token}_{group_index}'
                    ordered=[v for v in sorted(members) if v!=last]+[last]
                    for literal in ordered:
                        value=token|(literal<<3)
                        a.label('token_'+str(value));handlers[value]=a.pc;emit(0xd9)
                        literal_prefix(literal,cls)
                        if literal!=last:
                            jp(0xc3,body);shared_hit_tokens.append(value)
                    a.label(body);body_start=a.pc;token_body(token)
                    emitted.append(dict(literals=list(members),fallthrough=last,body_bytes=a.pc-body_start))
                body_layout.append(dict(base_token=token,groups=emitted))
    elif shared_literals:
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
    if a.pc-core+CALLER_STACK_BYTES > STORAGE_BUDGET:
        raise ValueError('wide LZSA2 exceeds the total 10000-byte code/table/alignment/stack budget')
    blob = bytearray(a.resolve(_external_labels))
    for token, target in enumerate(handlers):
        blob[table-core+token] = target&255
        blob[table-core+256+token] = target>>8
    return [(core, bytes(blob))], a.labels, dict(entry='start', variant='wide-shared-block' if shared_literals else 'wide-block',
        one_shot=True, code_bytes=len(blob), table_bytes=512, alignment_padding=table-core,
        shared_literal_bodies=shared_literals or grouped_layout,
        **(dict(cold_match_extension=True,raw_only=True,
            match_extension_path_delta_tstates=dict(nibble_length=-3,extended_length=2))
           if cold_match_extension else {}),
        **(dict(short_lengths=sorted(short_lengths),repeat_lengths=sorted(repeat_lengths))
           if short_lengths or repeat_lengths or grouped_layout else {}),
        **(dict(grouped_bodies=True,body_layout=body_layout,
                group_counts=[len(item['groups']) for item in body_layout],
                shared_hit_tokens=sorted(shared_hit_tokens),shared_hit_tstates=10)
           if grouped_layout else {}),
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
