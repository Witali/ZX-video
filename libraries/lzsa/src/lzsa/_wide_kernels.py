"""Fixed short-match emitters for the raw Wide and Hybrid profiles.

These kernels retain the existing two-byte offset operand and caller stack.
All copies are forward, including distance-one overlap. AF' remains the
nibble reservoir; no helper uses alternate register pairs or new scratch.
"""


def emit_new_offset_short(a, token_context, length):
    """BC=negative offset, HL=input, DE=output; return to ReadToken with BC=0.

    Copy offset registers before installing the count. The single existing
    SMC store remains available to later repeats. Save5*n-4 T and add4+2*n
    code bytes relative to the old Expanded path for token lengths2..8.
    token_context distinguishes duplicated grouped bodies in exported labels.
    """
    a.label('short_ready_'+str(token_context))
    a.abs16((0xed,0x43),'offset')
    a.emit(0xe5,0x60,0x69,0x01);a.word(length)
    a.emit(0x19)
    for _ in range(length):a.emit(0xed,0xa0)
    a.emit(0xe1);a.abs16(0xc3,'ReadToken')


def emit_repeat_short(a, token_context, length):
    """B=0, HL=input, DE=output; copy from the shared negative-offset operand.

    LD HL,(offset) costs6 T more than the original immediate load. Removing
    LDIR repeats still saves5*n-16 T for lengths4..8, adding6+2*n code bytes.
    Lengths2/3 deliberately stay on the old path. The last LDI leaves BC=0.
    """
    a.label('short_ready_'+str(token_context))
    a.emit(0x0e,length,0xe5);a.abs16(0x2a,'offset');a.emit(0x19)
    for _ in range(length):a.emit(0xed,0xa0)
    a.emit(0xe1);a.abs16(0xc3,'ReadToken')
