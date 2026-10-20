"""Output-demand coroutine wrapper for the standard raw-v2 wide decoder.

Token boundaries retain the ordinary Fast quota/EOF contract. The complete
input and output history stay resident; partial-input guards are a separate
profile. Caller registers can be overwritten while the private stack holds
AF/AF'/BC/DE/HL and the continuation. HL' is scratch only inside dispatch.
"""
from ._z80 import MiniAssembler
from .wide import build as raw_build, STORAGE_BUDGET

PREFIX, PREFIX_LIMIT, STACK = 0x7c00, 0x7d50, 0x7be0
PRIVATE_STACK_BYTES, CALLER_STACK_BYTES = 16, 4


def build(*, core=0x8000, core_limit=0xb000, shared_literals=False,
          prefix=PREFIX, prefix_limit=PREFIX_LIMIT, stack=STACK, output_base=0xc000):
    """Generate begin/slice_until with unchanged token-boundary minimum quotas.

    Configure input_pointer, block_end and slice_target; call begin once then
    slice_until. Caller SP is restored on every return. AF/AF'/BC/DE/HL and
    alternate pairs may be clobbered, and the caller may overwrite them while
    suspended. IX/IY stay intact. Output must not wrap; keep the complete raw
    input/history resident and code operands writable. IRQ preserves both live
    register sets including AF'. Sixteen private-stack bytes and four caller-
    stack bytes (return plus sync call) are required, plus actual IRQ headroom.
    """
    if not (0 <= prefix < prefix_limit <= 65536 and 0 <= core < core_limit <= 65536):
        raise ValueError('invalid wide coroutine code reservations')
    if not (core_limit <= prefix or prefix_limit <= core):
        raise ValueError('wide coroutine reservations overlap')
    if not (PRIVATE_STACK_BYTES <= stack <= 65535 and 0 <= output_base < 65535):
        raise ValueError('invalid private stack/output address')
    cold = MiniAssembler(prefix)
    def emit(*code):cold.emit(*code)
    def absolute(op, label):cold.abs16(op, label)
    cold.label('slice_until');absolute(0xcd, 'sync')
    absolute(0x2a, 'slice_output');absolute((0xed, 0x5b), 'slice_target')
    emit(0xb7, 0xed, 0x52, 0xd0)
    absolute((0xed, 0x73), 'slice_caller_sp');absolute((0xed, 0x7b), 'slice_decoder_sp')
    emit(0xe1, 0xd1, 0xc1, 8, 0xf1, 8, 0xf1, 0xc9)
    cold.label('begin');absolute(0xcd, 'sync');absolute((0xed, 0x73), 'slice_caller_sp')
    emit(0x31);cold.word(stack);absolute(0x21, 'finished');emit(0xe5)
    absolute(0x2a, 'input_pointer');emit(0x11);cold.word(output_base);absolute(0xc3, 'start')
    cold.label('finished');absolute(0x2a, 'block_end');emit(0xb7, 0xed, 0x52);absolute(0xc2, 'fatal')
    absolute((0xed, 0x53), 'slice_output');absolute((0xed, 0x7b), 'slice_caller_sp');emit(0xc9)
    # Yield only while main registers own input/output. The raw core's saved
    # original HL' remains below this continuation until exact EOF restores it.
    cold.label('slice_yield');absolute((0xed, 0x53), 'slice_output')
    emit(0xf5, 8, 0xf5, 8, 0xc5, 0xd5, 0xe5)
    absolute((0xed, 0x73), 'slice_decoder_sp');absolute((0xed, 0x7b), 'slice_caller_sp');emit(0xc9)
    cold.label('sync');absolute(0x2a, 'slice_target');absolute((0xed, 0x5b), 'block_end')
    emit(0xb7, 0xed, 0x52);absolute(0x2a, 'slice_target');cold.rel8(0x20, 'sync_target')
    # The final output demand must still read EOD. FFFFh is unreachable as an
    # intermediate publication cursor for a valid nonwrapping output block.
    emit(0x21, 0xff, 0xff)
    cold.label('sync_target');emit(0x7c);absolute(0x32, 'high_operand')
    emit(0x7d);absolute(0x32, 'low_operand');emit(0xc9)
    cold.label('fatal');emit(0x76)
    cold.label('state')
    for name in ('slice_output','slice_target','slice_caller_sp','slice_decoder_sp',
                 'block_length','block_end','input_pointer'):
        cold.label(name);cold.word(0)
    cold.label('block_stored');emit(0)
    cold.label('end')
    cold.labels['block_end_high'] = cold.labels['block_end']+1
    def boundary(a):
        # Same high/low comparisons as ordinary Fast: output demand is a
        # minimum, and a token may overshoot. At the exact block end continue
        # until real EOD, so completion does not depend on a previous block.
        a.emit(0x7a);a.labels['high_operand']=a.pc+1;a.emit(0xfe, 0)
        a.abs16(0xda, 'token_body');a.rel8(0x20, 'Yield');a.emit(0x7b)
        a.labels['low_operand']=a.pc+1;a.emit(0xfe, 0);a.abs16(0xda, 'token_body')
        a.label('Yield');a.abs16(0x3a, 'block_end_high');a.emit(0xba);a.rel8(0x20, 'Suspend')
        a.abs16(0x3a, 'block_end');a.emit(0xbb);a.abs16(0xca, 'token_body')
        a.label('Suspend');a.abs16(0xcd, 'slice_yield');a.abs16(0xc3, 'ReadToken')
    hot, labels, metadata = raw_build(core=core, core_limit=core_limit,
        shared_literals=shared_literals, _boundary=boundary, _external_labels=cold.labels)
    labels = cold.labels|labels
    if cold.pc > prefix_limit:raise ValueError('wide coroutine prefix exceeds prefix-limit')
    regions = [(prefix, cold.resolve(labels)), *hot]
    code_bytes = sum(len(blob) for _, blob in regions)
    service = code_bytes+PRIVATE_STACK_BYTES+CALLER_STACK_BYTES
    if service > STORAGE_BUDGET:raise ValueError('wide coroutine exceeds total 10000-byte service budget')
    stack_lo = stack-PRIVATE_STACK_BYTES
    if any(not (stack <= at or stack_lo >= at+len(blob)) for at,blob in regions):
        raise ValueError('wide coroutine private stack overlaps generated regions')
    patched = metadata['patched_addresses']+[labels['high_operand'], labels['low_operand']]
    metadata.update(entry='begin', variant='wide-shared-coroutine' if shared_literals else 'wide-coroutine',
        one_shot=False, prefix_end=cold.pc, code_bytes=code_bytes,
        state_bytes=labels['end']-labels['state'], private_stack=stack,
        private_stack_bytes=PRIVATE_STACK_BYTES, caller_stack_bytes=CALLER_STACK_BYTES,
        decoder_stack_bytes=PRIVATE_STACK_BYTES, output_base=output_base,
        total_storage_bytes=service, service_memory_bytes=service,
        service_memory=dict(code_tables_alignment_state_bytes=code_bytes,
            embedded_mutable_bytes=4, embedded_state_bytes=labels['end']-labels['state'],
            external_state_bytes=0, private_stack_bytes=PRIVATE_STACK_BYTES,
            caller_stack_bytes=CALLER_STACK_BYTES, scratch_bytes=0, internal_buffer_bytes=0),
        patched_addresses=patched, coroutine=True, streaming=False)
    return regions, labels, metadata
