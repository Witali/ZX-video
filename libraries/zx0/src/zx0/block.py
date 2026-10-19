"""Resident-block ZX0 v2 profiles; no coroutine, quota or paging wrappers."""
from ._z80 import MiniAssembler,sha
from .codec import emit_decoder
from .resumable import emit_fast


def build(variant='fast',*,core=0x8000,core_limit=0x8400,fast_jumps=False,branch_tuned=False,literal_prefix=False,inline_tail_refill=False,mega_tuned=False,_assembler=None):
    """Call metadata entry with HL=input, DE=nonwrapping output, caller stack.

    Supply a complete valid block and resident input/history. AF/BC/DE/HL
    are clobbered; preserve them across IRQ. Fast removes the persistent IX
    continuation as in the coroutine; caller IX/alternate registers survive.
    Standard is ROM-compatible; other variants patch two offset bytes in RAM.
    Bounds, expected size and reentrancy are the caller's responsibility.
    fast_jumps changes only unconditional JR to JP in Standard/Turbo/Mega:
    12 -> 10 T per execution, one extra byte per site. Fast already uses JP.
    literal_prefix adds one LDI before LDIR only when the literal count is
    at least two: saves 5 T per such run for two extra code bytes in Fast.
    inline_tail_refill removes the repeat-gamma tail's redundant CALL/RET;
    Fast only, +3 bytes, -18/-5 T at an exhausted reservoir (stop bit 1/0).
    mega_tuned removes dead offset shifts and tunes four reuse exits in Mega:
    -4 bytes, same resident ABI, no coroutine equivalent. Defaults stay exact.
    """
    if mega_tuned and variant!='mega':raise ValueError('mega tuning requires the Mega decoder')
    if branch_tuned:
        if variant!='fast':raise ValueError('branch tuning requires the Fast decoder')
        from ._branch_tuning import tune
        return tune(build,dict(variant=variant,core=core,core_limit=core_limit,fast_jumps=fast_jumps,
                               literal_prefix=literal_prefix,inline_tail_refill=inline_tail_refill,mega_tuned=mega_tuned),'zx0')
    if literal_prefix and variant!='fast':raise ValueError('literal prefix requires the Fast decoder')
    if inline_tail_refill and variant!='fast':raise ValueError('inline tail refill requires the Fast decoder')
    if not 0<=core<core_limit<=65536:raise ValueError('invalid code reservation')
    a=(_assembler or MiniAssembler)(core)
    if variant=='fast':
        emit_fast(a,lambda a,site,**kwargs:False,literal_prefix=literal_prefix,inline_tail_refill=inline_tail_refill);entry='DecompressZX0';offset='PrevOffset+1'
    else:
        entry=emit_decoder(a,variant,fast_jumps=fast_jumps,mega_tuned=mega_tuned);offset=f'dzx0{variant[0]}_last_offset+1'
    patches=[] if variant=='standard' else [a.labels[offset]+i for i in (0,1)]
    if a.pc>core_limit:raise ValueError('one-shot ZX0 exceeds core-limit')
    return [(core,a.resolve())],a.labels,dict(entry=entry,variant=variant+'-block',one_shot=True,
        code_bytes=a.pc-core,core_end=a.pc,state_bytes=0,private_stack_bytes=0,
        patched_addresses=patches,source_commit='ecde3a2ae05061fe06469ed46df81a33b7de7d86',
        code_sha256=sha(a.resolve()),
        **(dict(literal_prefix=True,literal_prefix_bytes=1,literal_prefix_minimum=2,
                literal_copy_delta_tstates=-5,additional_sync_tstates=0) if literal_prefix else {}),
        **(dict(mega_tuned=True,dead_offset_shift_sites=4,reuse_exit_jump_sites=4,
                mega_code_delta_bytes=-4,coroutine_supported=False,
                max_decoder_stack_bytes=4,workspace_bytes=a.pc-core+4,
                stack_count_includes_caller_return=True) if mega_tuned else {}),
        **(dict(inline_tail_refill=True,tail_refill_code_delta_bytes=3,
                tail_refill_delta_tstates_stop_1=-18,tail_refill_delta_tstates_stop_0=-5) if inline_tail_refill else {}),
        **(dict(fast_jumps=True,fast_jump_sites={'fast':0,'standard':2,'turbo':1,'mega':1}[variant],
                unconditional_jump_tstates_before=12,unconditional_jump_tstates_after=10) if fast_jumps else {}))
