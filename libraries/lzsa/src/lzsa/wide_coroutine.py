"""Output-demand coroutine wrapper for the standard raw-v2 wide decoder.

Token boundaries retain the ordinary Fast quota/EOF contract. Optional
streaming guards retain the original page frontier and final-input bypass.
Complete output history stays resident. Caller registers may be overwritten
while the private stack holds
AF/AF'/BC/DE/HL and the continuation. HL' is scratch only inside dispatch.
"""
from ._z80 import MiniAssembler
from .wide import build as raw_build, STORAGE_BUDGET

PREFIX, PREFIX_LIMIT, STACK = 0x7c00, 0x7d50, 0x7be0
PRIVATE_STACK_BYTES, CALLER_STACK_BYTES = 16, 4


def build(*, core=0x8000, core_limit=0xb000, shared_literals=False,
          prefix=PREFIX, prefix_limit=PREFIX_LIMIT, stack=STACK, output_base=0xc000,
          streaming=False, direct_header=False):
    """Generate begin/slice_until with unchanged token-boundary minimum quotas.

    Configure input_pointer, block_end and slice_target; call begin once then
    slice_until. Caller SP is restored on every return. AF/AF'/BC/DE/HL and
    alternate pairs may be clobbered, and the caller may overwrite them while
    suspended. IX/IY stay intact. Output must not wrap; keep input/history
    resident and code operands writable. Streaming input may arrive one page
    at a time while suspended. Publish input_high/header_frontier/literal_frontier
    and all_loaded, then call update_guards with A=all_loaded after saving the
    final shared-sector tail. Both live register sets including AF' survive IRQ.
    Required private stack is16 bytes ordinary or24 guarded; caller stack is
    four bytes (return plus sync call). Add actual IRQ headroom separately.
    """
    if direct_header and not streaming:raise ValueError('direct header requires streaming input')
    private_stack_bytes=24 if streaming else PRIVATE_STACK_BYTES
    if not (0 <= prefix < prefix_limit <= 65536 and 0 <= core < core_limit <= 65536):
        raise ValueError('invalid wide coroutine code reservations')
    if not (core_limit <= prefix or prefix_limit <= core):
        raise ValueError('wide coroutine reservations overlap')
    if not (private_stack_bytes <= stack <= 65535 and 0 <= output_base < 65535):
        raise ValueError('invalid private stack/output address')
    cold = MiniAssembler(prefix)
    def emit(*code):cold.emit(*code)
    def absolute(op, label):cold.abs16(op, label)
    cold.label('slice_until')
    if streaming:absolute(0x3a,'finished');emit(0xb7,0xc0)
    absolute(0xcd, 'sync')
    if not streaming:
        absolute(0x2a, 'slice_output');absolute((0xed, 0x5b), 'slice_target')
        emit(0xb7, 0xed, 0x52, 0xd0)
    absolute((0xed, 0x73), 'slice_caller_sp');absolute((0xed, 0x7b), 'slice_decoder_sp')
    emit(0xe1, 0xd1, 0xc1, 8, 0xf1, 8, 0xf1, 0xc9)
    cold.label('begin');absolute(0xcd, 'sync');absolute((0xed, 0x73), 'slice_caller_sp')
    if streaming:emit(0xaf);absolute(0x32,'finished');absolute(0x32,'input_needed')
    emit(0x31);cold.word(stack);absolute(0x21, 'finish' if streaming else 'finished');emit(0xe5)
    absolute(0x2a, 'input_pointer');emit(0x11);cold.word(output_base);absolute(0xc3, 'start')
    cold.label('finish' if streaming else 'finished');absolute(0x2a, 'block_end');emit(0xb7, 0xed, 0x52);absolute(0xc2, 'fatal')
    if streaming:emit(0x3e,1);absolute(0x32,'finished')
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
    if streaming:
        # A 32-byte readable prefix covers every short token: <=17 literals,
        # its header, offset and match length. Long literals separately require
        # BC bytes plus seven bytes of lookahead. AF' always retains the nibble.
        # Supply whole pages while suspended, then use emit_guard_update to
        # bypass all guards only after the final page/shared tail are saved.
        cold.label('guard_header')
        if not direct_header:cold.label('header_patch');emit(0xf5)
        emit(0x7d,0xc6,31,0x7c,0xce,0);cold.rel8(0x38,'header_short')
        emit(0xfe);cold.label('header_frontier');emit(0)
        if direct_header:
            absolute(0xda,'token_body');cold.label('header_short')
            absolute(0xcd,'input_wait');absolute(0xc3,'ReadToken')
        else:
            cold.rel8(0x38,'header_ready');cold.label('header_short')
            emit(0xf1);absolute(0xcd,'input_wait');cold.rel8(0x18,'guard_header')
            cold.label('header_ready');emit(0xf1,0xc9)
        cold.label('guard_long8');absolute(0xcd,'guard_literals');absolute(0xc3,'long8_complete')
        cold.label('guard_long16');absolute(0xcd,'guard_literals');absolute(0xc3,'long16_complete')
        cold.label('guard_literals');emit(0xf5,0xe5,0x09);cold.rel8(0x38,'literal_short')
        emit(0x7d,0xc6,7,0x7c,0xce,0);cold.rel8(0x38,'literal_short')
        emit(0xfe);cold.label('literal_frontier');emit(0);cold.rel8(0x38,'literal_ready')
        cold.label('literal_short');emit(0xe1,0xf1);absolute(0xcd,'input_wait');cold.rel8(0x18,'guard_literals')
        cold.label('literal_ready');emit(0xe1,0xf1,0xc9)
        cold.label('input_wait');emit(0xf5,0x3e,1);absolute(0x32,'input_needed')
        absolute(0xcd,'slice_yield');emit(0xaf);absolute(0x32,'input_needed');emit(0xf1,0xc9)
        # Include the required final-input patcher in the service footprint.
        # Call with A=all_loaded only while suspended, after publishing both
        # frontiers; it restores guards for a new partial block as well.
        from .streaming import emit_guard_update
        cold.label('update_guards')
        guard_labels={name:name for name in ('guard_literals','token_body','guard_long8','guard_long16',
            'long8_complete','long16_complete','CopyMoreLiterals','NextUseBC','token_high_target',
            'token_low_target','token_end_target','long8_target','long16_target')}
        if not direct_header:guard_labels['header_patch']='header_patch'
        guard_labels['token_guard']='guard_header' if direct_header else 'Token'
        emit_guard_update(cold,guard_labels);emit(0xc9)
        cold.label('update_guards_end')
    cold.label('state')
    for name in ('slice_output','slice_target','slice_caller_sp','slice_decoder_sp',
                 'block_length','block_end','input_pointer'):
        cold.label(name);cold.word(0)
    cold.label('block_stored');emit(0)
    if streaming:
        for name in ('input_high','all_loaded','input_needed','finished'):cold.label(name);emit(0)
    cold.label('end')
    cold.labels['block_end_high'] = cold.labels['block_end']+1
    def boundary(a):
        # Same high/low comparisons as ordinary Fast: output demand is a
        # minimum, and a token may overshoot. At the exact block end continue
        # until real EOD, so completion does not depend on a previous block.
        a.emit(0x7a);a.labels['high_operand']=a.pc+1;a.emit(0xfe, 0)
        if streaming:a.labels['token_high_target']=a.pc+1
        a.abs16(0xda, 'guard_header' if direct_header else 'Token');a.rel8(0x20, 'Yield');a.emit(0x7b)
        a.labels['low_operand']=a.pc+1;a.emit(0xfe, 0)
        if streaming:a.labels['token_low_target']=a.pc+1
        a.abs16(0xda, 'guard_header' if direct_header else 'Token')
        a.label('Yield');a.abs16(0x3a, 'block_end_high');a.emit(0xba);a.rel8(0x20, 'Suspend')
        a.abs16(0x3a, 'block_end');a.emit(0xbb)
        if streaming:a.labels['token_end_target']=a.pc+1
        a.abs16(0xca, 'guard_header' if direct_header else 'Token')
        a.label('Suspend');a.abs16(0xcd, 'slice_yield');a.abs16(0xc3, 'ReadToken')
        a.label('Token')
        if streaming and not direct_header:a.abs16(0xcd,'guard_header')
    hot, labels, metadata = raw_build(core=core, core_limit=core_limit,
        shared_literals=shared_literals, _boundary=boundary, _external_labels=cold.labels,
        _literal_guards=streaming)
    labels = cold.labels|labels
    if streaming:
        labels['token_guard']=labels['guard_header'] if direct_header else labels['Token']
        # Existing producer adapters resolve both old and explicit complete
        # continuation names. These aliases have identical HL/BC ownership.
        labels['CopyMoreLiterals']=labels['long8_complete']
        labels['NextUseBC']=labels['long16_complete']
    if cold.pc > prefix_limit:raise ValueError('wide coroutine prefix exceeds prefix-limit')
    regions = [(prefix, cold.resolve(labels)), *hot]
    code_bytes = sum(len(blob) for _, blob in regions)
    service = code_bytes+private_stack_bytes+CALLER_STACK_BYTES
    if service > STORAGE_BUDGET:raise ValueError('wide coroutine exceeds total 10000-byte service budget')
    stack_lo = stack-private_stack_bytes
    if any(not (stack <= at or stack_lo >= at+len(blob)) for at,blob in regions):
        raise ValueError('wide coroutine private stack overlaps generated regions')
    patched = metadata['patched_addresses']+[labels['high_operand'], labels['low_operand']]
    if streaming:
        patched += [labels[k] for k in (('header_patch',) if 'header_patch' in labels else ())+
                    ('guard_literals','header_frontier','literal_frontier')]
        patched += [labels[k]+i for k in ('token_high_target','token_low_target','token_end_target',
                                         'long8_target','long16_target') for i in (0,1)]
    metadata.update(entry='begin', variant='wide-shared-coroutine' if shared_literals else 'wide-coroutine',
        one_shot=False, prefix_end=cold.pc, code_bytes=code_bytes,
        state_bytes=labels['end']-labels['state'], private_stack=stack,
        private_stack_bytes=private_stack_bytes, caller_stack_bytes=CALLER_STACK_BYTES,
        decoder_stack_bytes=private_stack_bytes, output_base=output_base,
        total_storage_bytes=service, service_memory_bytes=service,
        service_memory=dict(code_tables_alignment_state_bytes=code_bytes,
            embedded_mutable_bytes=len(set(patched)), embedded_state_bytes=labels['end']-labels['state'],
            external_state_bytes=0, private_stack_bytes=private_stack_bytes,
            caller_stack_bytes=CALLER_STACK_BYTES, scratch_bytes=0, internal_buffer_bytes=0),
        patched_addresses=patched, coroutine=True, streaming=streaming,
        **(dict(direct_header_guard=direct_header,available_header_tstates=46 if direct_header else 96)
           if streaming else {}))
    if streaming:
        metadata['guard_update_code_bytes']=labels['update_guards_end']-labels['update_guards']
        metadata['service_memory_scope']='consumer decoder only, including embedded guard helper and required decoder/caller stacks; input supplier and IRQ resources are additional'
        metadata['consumer_service_memory_bytes']=service
        metadata['input_supplier_memory']='caller-owned; published input remains readable until consumed; carry is not intrinsic to every valid page supplier'
        metadata['reference_inplace_input_supplier']=dict(shared_sector_carry_bytes=256,
            additional_code_state_stacks=True,included_in_consumer_service=False)
    return regions, labels, metadata
