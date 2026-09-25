"""Experimental resumable ZX0 with input and history in the same RAM bank.

Banks 1/3/4: compressed input C000..DFFF, decoded output E000..FFFF.
The caller must page the slot before every invocation. This module supplies
the decoder, not the queue, disk producer or publication scheduler.
The existing token-boundary suspension contract and private stack are kept.
inline_literals=True accepts ZX0 blocks only; the general default retains
stored-block support. Literal copying then falls through without CALL/RET.
"""
from build_zxv_trd import MiniAssembler
import incremental_zx0

CODE, INPUT, OUTPUT = 0x7c00, 0xc000, 0xe000
STACK_BOTTOM, STACK_TOP = 0x7b70, 0x7be0
BANKS = (1, 3, 4)


def build(*, dynamic_input=False, inline_literals=False):
    a = MiniAssembler(CODE)
    incremental_zx0.emit_decoder(a, output_base=OUTPUT, input_base=INPUT,
        stack_top=STACK_TOP, wrap_output=True, token_boundaries=True,
        inline_matches=True,input_pointer_label='input_pointer' if dynamic_input else None,
        inline_literals=inline_literals)
    a.labels['begin'] = a.labels['slice_begin']
    a.label('fatal'); a.emit(0x76)
    a.label('state')
    incremental_zx0.emit_variables(a)
    for name in ('block_length', 'block_end'):
        a.label(name); a.word(0)
    a.label('block_stored'); a.emit(0)
    if dynamic_input:a.label('input_pointer');a.word(INPUT)
    a.label('end')
    if a.pc > 0x7e90:
        raise ValueError('decoder overlaps the current packet reader')
    return a.resolve(), a.labels
