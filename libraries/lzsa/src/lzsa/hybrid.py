"""Fixed raw LZSA2 Hybrid speed/space profiles under the service-memory cap.

All standard token/literal/offset/length forms remain valid. These selectors
only share duplicate handler bodies and choose their fall-through member.
Vectors were frozen after complete 675-case native proofs on 2026-10-20;
the installed package needs no repository evidence, tests or input corpus.
"""
from .wide import build as _wide_build


# Index order: (XYZ << 5) | MMM, with XYZ outer and MMM inner.
_BODY_BASES = tuple((cls << 5) | field for cls in range(8) for field in range(8))
_LL_RANKS = (
    (0, 1, 3, 2),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 3, 2),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 3, 2),
    (0, 1, 3, 2),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (1, 0, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 3, 2),
    (0, 1, 2, 3),
    (1, 0, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 3, 2),
    (0, 1, 3, 2),
    (0, 1, 3, 2),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 3, 2),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 3, 2),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3),
    (1, 3, 2, 0),
    (1, 3, 2, 0),
    (1, 3, 2, 0),
    (1, 3, 2, 0),
    (1, 3, 2, 0),
    (1, 3, 2, 0),
    (1, 3, 2, 0),
    (1, 3, 2, 0),
)

_GROUP_COUNTS = {
    'compact': (
        1, 1, 1, 1, 1, 1, 1, 1, 4, 2, 1, 1, 1, 1, 1, 1,
        3, 2, 2, 2, 1, 1, 1, 2, 2, 2, 2, 1, 1, 1, 1, 2,
        1, 3, 2, 2, 1, 1, 1, 2, 1, 3, 2, 2, 1, 1, 1, 2,
        1, 1, 1, 1, 1, 1, 1, 2, 3, 3, 2, 1, 1, 1, 2, 4,
    ),
    'balanced': (
        3, 2, 1, 1, 1, 1, 1, 1, 4, 4, 2, 2, 1, 1, 2, 2,
        3, 4, 4, 2, 2, 2, 1, 4, 3, 4, 3, 2, 2, 1, 1, 4,
        1, 4, 4, 3, 2, 2, 2, 4, 1, 4, 4, 3, 2, 2, 2, 4,
        1, 1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3, 2, 2, 4,
    ),
    'fast': (
        4, 4, 4, 3, 2, 3, 3, 4, 4, 4, 4, 4, 3, 3, 4, 4,
        4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 3, 4, 4,
        4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
        2, 4, 4, 4, 3, 3, 2, 4, 3, 3, 3, 3, 3, 3, 3, 4,
    ),
    'compact-base': (
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4,
    ),
    'balanced-base': (
        2, 1, 1, 1, 1, 1, 1, 1, 4, 2, 2, 2, 1, 1, 1, 1,
        3, 4, 4, 2, 2, 2, 2, 3, 3, 4, 3, 2, 2, 1, 1, 2,
        1, 4, 3, 2, 2, 2, 1, 2, 1, 4, 3, 2, 2, 2, 2, 2,
        1, 1, 1, 1, 1, 1, 1, 2, 3, 3, 3, 3, 3, 3, 3, 4,
    ),
    'fast-base': (
        4, 2, 1, 1, 1, 1, 1, 1, 4, 4, 3, 2, 2, 2, 3, 2,
        3, 4, 4, 4, 3, 2, 2, 4, 4, 4, 4, 3, 2, 2, 2, 4,
        2, 4, 4, 4, 3, 3, 2, 4, 2, 4, 4, 4, 3, 3, 3, 4,
        1, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 4,
    ),
}

_SELECTOR_INFO = {
    'compact': ('short-budget-5000', 4999, 15048469, '78bb1bd440ac23d95d8bd7c6337c075c47d68fe10ac36435c15c2c1d09ce2e51'),
    'balanced': ('short-budget-6500', 6500, 14983119, '79b37ae3c5bee81646974096a6c005775b391a04bea43e227840bb94c4c87124'),
    'fast': ('short-budget-9500', 9500, 14944429, '9d25fccf551fa821c6894356e01dc4c9e1328b3ff20da15f4534cbec37101abd'),
    'compact-base': ('basic-budget-3452', 3452, 15822353, '2c1f8cc001d1005fcacaeb2edc248c34626f6681b4fef852759028b8c564b140'),
    'balanced-base': ('basic-budget-4500', 4499, 15683583, 'ebb181368a0006780c52bf8f594920dafad1b40f3e425a534d53eeef81f46690'),
    'fast-base': ('basic-budget-5500', 5500, 15643493, '3386fa41cd5fdb757f370e9c20a9fa2ea47d3b4e7fae743f7e6be4cb236d67c6'),
}


def build(profile="fast", *, core=0x8000, core_limit=0xc000):
    """Return resident raw regions/labels/metadata for a fixed Hybrid layout.

    compact/balanced/fast include new-offset2..8 and repeat-offset4..8
    kernels. Their -base counterparts retain the original copy paths. All
    preserve the raw Wide ABI: HL=input, DE=output, exact EOD, six-byte caller
    stack including return, IX/IY and other alternate pairs preserved. AF/AF'
    and BC/DE/HL may be clobbered; IRQ preserves both live register sets.
    Source and full output/history stay resident and separate from service
    storage. Add actual IRQ/hardware stack headroom separately. Writable
    operands are nonreentrant. No output quota or partial-input API is exposed.
    """
    if not isinstance(profile, str) or profile not in _GROUP_COUNTS:
        raise ValueError("unknown Hybrid profile; use compact, balanced, fast or their -base variants")
    counts = _GROUP_COUNTS[profile]
    groups = {}
    ranks = {}
    for base, count, rank in zip(_BODY_BASES, counts, _LL_RANKS):
        # The hottest count-1 literal forms are singletons; the remaining
        # forms share one body, with their highest-ranked member falling
        # through. This changes layout only, never the accepted token set.
        groups[base] = tuple((literal,) for literal in rank[:count-1]) + (rank[count-1:],)
        ranks[base] = rank
    specialized = not profile.endswith("-base")
    regions, labels, metadata = _wide_build(core=core, core_limit=core_limit,
        short_lengths=range(2,9) if specialized else (),
        repeat_lengths=range(4,9) if specialized else (),
        _groups_by_body=groups, _fallthrough_order=ranks)
    selector, aligned_service, real_tstates, aligned_sha = _SELECTOR_INFO[profile]
    metadata.update(variant="hybrid-"+profile+"-block", hybrid_profile=profile,
        hybrid_selector=selector, raw_only=True,
        nominal_aligned_service_bytes=aligned_service,
        reference_real_tstates=real_tstates, reference_aligned_blob_sha256=aligned_sha,
        literal_fallthrough_ranks=[list(rank) for rank in _LL_RANKS])
    return regions, labels, metadata
