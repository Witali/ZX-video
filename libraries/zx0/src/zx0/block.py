"""Resident-block ZX0 v2 profiles; no coroutine, quota or paging wrappers."""
from ._z80 import MiniAssembler,sha
from .codec import emit_decoder
from .resumable import emit_fast


def build(variant='fast',*,core=0x8000,core_limit=0x8400,fast_jumps=False):
    """Call metadata entry with HL=input, DE=nonwrapping output, caller stack.

    Supply a complete valid block and resident input/history. AF/BC/DE/HL
    are clobbered; preserve them across IRQ. Fast removes the persistent IX
    continuation as in the coroutine; caller IX/alternate registers survive.
    Standard is ROM-compatible; other variants patch two offset bytes in RAM.
    Bounds, expected size and reentrancy are the caller's responsibility.
    fast_jumps changes only unconditional JR to JP in Standard/Turbo/Mega:
    12 -> 10 T per execution, one extra byte per site. Fast already uses JP.
    """
    if not 0<=core<core_limit<=65536:raise ValueError('invalid code reservation')
    a=MiniAssembler(core)
    if variant=='fast':
        emit_fast(a,lambda a,site:None);entry='DecompressZX0';offset='PrevOffset+1'
    else:
        entry=emit_decoder(a,variant,fast_jumps=fast_jumps);offset=f'dzx0{variant[0]}_last_offset+1'
    patches=[] if variant=='standard' else [a.labels[offset]+i for i in (0,1)]
    if a.pc>core_limit:raise ValueError('one-shot ZX0 exceeds core-limit')
    return [(core,a.resolve())],a.labels,dict(entry=entry,variant=variant+'-block',one_shot=True,
        code_bytes=a.pc-core,core_end=a.pc,state_bytes=0,private_stack_bytes=0,
        patched_addresses=patches,source_commit='ecde3a2ae05061fe06469ed46df81a33b7de7d86',
        code_sha256=sha(a.resolve()),
        **(dict(fast_jumps=True,fast_jump_sites={'fast':0,'standard':2,'turbo':1,'mega':1}[variant],
                unconditional_jump_tstates_before=12,unconditional_jump_tstates_after=10) if fast_jumps else {}))
