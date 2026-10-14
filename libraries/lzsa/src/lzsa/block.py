"""One-shot LZSA2 v2 profile using the project's exact-EOF fast field decoder."""
from .resumable import build as _build


def build(variant='fast',*,core=0x8000,core_limit=0x8400,long_copy=False,near_literals=False):
    """Return regions/labels/metadata for a valid fully resident raw-v2 block.

    Call start with HL=input, DE=output and the caller stack. AF/AF'/BC/DE/HL
    are clobbered. Output must not wrap; source/history stay resident, patched
    offset code writable. IRQ must preserve working registers including AF'.
    There are no bounds/yield/paging checks: callers validate block/allocation
    and expected output externally. Reentrant calls cannot share patched code.
    """
    if variant=='small':
        if long_copy or near_literals:raise ValueError('compact profile has shared LDIR helpers')
        from .compact import build as compact_build
        return compact_build(core=core,core_limit=core_limit)
    if variant!='fast':raise ValueError('unknown block decoder')
    return _build(core=core,core_limit=core_limit,long_copy=long_copy,
                  near_literals=near_literals,_one_shot=True)
