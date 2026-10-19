"""One-shot LZSA2 v2 profile using the project's exact-EOF fast field decoder."""
from .resumable import build as _build


def build(variant='fast',*,core=0x8000,core_limit=0x8400,long_copy=False,near_literals=False,fast_jumps=False,branch_tuned=False,nibble_prefill=False):
    """Return regions/labels/metadata for a valid fully resident raw-v2 block.

    Call start with HL=input, DE=output and the caller stack. AF/AF'/BC/DE/HL
    are clobbered. Output must not wrap; source/history stay resident, patched
    offset code writable. IRQ must preserve working registers including AF'.
    There are no bounds/yield/paging checks: callers validate block/allocation
    and expected output externally. Reentrant calls cannot share patched code.
    wide/wide-shared use full-token tables under a 10,000-byte total budget;
    reserve a larger core_limit explicitly. Their caller stack peaks at six
    bytes including return, plus IRQ headroom; HL' is preserved at raw EOF.
    """
    if variant in ('wide', 'wide-shared'):
        if long_copy or near_literals or fast_jumps or branch_tuned or nibble_prefill:
            raise ValueError('wide profiles use their own copy/branch layout')
        from .wide import build as wide_build
        return wide_build(core=core, core_limit=core_limit, shared_literals=variant=='wide-shared')
    if variant=='small':
        if long_copy or near_literals or fast_jumps or branch_tuned or nibble_prefill:raise ValueError('compact profile does not support fast copy/jump options')
        from .compact import build as compact_build
        return compact_build(core=core,core_limit=core_limit)
    if variant!='fast':raise ValueError('unknown block decoder')
    return _build(core=core,core_limit=core_limit,long_copy=long_copy,
                  near_literals=near_literals,fast_jumps=fast_jumps,branch_tuned=branch_tuned,nibble_prefill=nibble_prefill,_one_shot=True)
