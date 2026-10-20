"""One private E04 cap255 extension of the accepted cap228 fast layout.

Only two local cap whitelists change. The 61 frozen E01 contractions remain
at their existing sites. An independent binary oracle inserts 27 LDIs at each
of the 12 shared word-chain entries and relocates every reference and label.
No public generator or global module object is patched.
"""
import ast
from bisect import bisect_left, bisect_right
from functools import lru_cache
import inspect

from zx0 import maximum, _shared_prefixes
from zx0.maximum_branches import build as baseline, _ContractedAssembler, _SITES
from profile_branch_mix import instructions


FAMILIES = ("length", "literals", "reuse")
PHASES = (1, 3, 5, 7)
EXTRA_LDI = 27
EXPECTED_SERVICE = 8165
EXPECTED_REAL_TSTATES = 139546674


def transformed_sources():
    shared = inspect.getsource(_shared_prefixes.transform)
    source = inspect.getsource(maximum.build)
    whitelist = "(31, 63, 127, 227, 228)"
    assert source.count(whitelist) == shared.count(whitelist) == 1
    source = source.replace(whitelist, "(31, 63, 127, 227, 228, 255)")
    shared = shared.replace(whitelist, "(31, 63, 127, 227, 228, 255)")
    imported = "        from ._shared_prefixes import transform\n"
    assert source.count(imported) == 1
    source = source.replace(imported, "        transform = _e04_transform\n")
    return source, shared


@lru_cache(None)
def private_builder():
    source, shared = transformed_sources()
    helper_namespace = dict(vars(_shared_prefixes))
    exec(compile(ast.parse(shared), "<private E04 shared cap255>", "exec"), helper_namespace)
    namespace = dict(vars(maximum), _e04_transform=helper_namespace["transform"])
    exec(compile(ast.parse(source), "<private E04 Maximum cap255>", "exec"), namespace)
    return namespace["build"]


def binary_oracle(core):
    """Preserve target entries before inserted bytes, old instructions after.

    Word-entry JPs must execute all 255 LDIs. Their old228-entry label is
    renamed255 and remains before the 27 inserted LDIs. Every original
    instruction at that address moves after the insertion. Other labels and
    references move past insertions strictly before their old addresses.
    """
    before = baseline(core=core, prefix_cap=228, policy="fast")
    (origin, blob), = before[0]
    names = [f"shared_zero_{family}_{phase}_228" for family in FAMILIES for phase in PHASES]
    points = sorted(before[1][name] for name in names)
    assert len(set(points)) == 12
    assert all({name for name, at in before[1].items() if at == point} <= set(names) for point in points)

    def reference(address):
        return address + 2*EXTRA_LDI*bisect_left(points, address)

    def instruction(address):
        return address + 2*EXTRA_LDI*bisect_right(points, address)

    out = bytearray(); relative = []
    for at, original in instructions(blob, origin):
        if at in points:
            out.extend(b"\xed\xa0"*EXTRA_LDI)
        code = bytearray(original)
        absolute = len(code) == 3 and (code[0] & 0xc7 in (0xc2, 0xc4) or code[0] in (0xc3, 0xcd, 0x2a))
        operand = 1 if absolute else 2 if len(code) == 4 and code[:2] == b"\xed\x43" else None
        if operand is not None:
            target = int.from_bytes(code[operand:operand+2], "little")
            assert origin <= target < origin+len(blob)
            code[operand:operand+2] = reference(target).to_bytes(2, "little")
        elif code[0] in (0x18, 0x20, 0x28, 0x30, 0x38):
            old_span = int.from_bytes(code[1:], "little", signed=True)
            target = at+2+old_span
            span = reference(target)-instruction(at)-2
            assert span == old_span and -128 <= span <= 127
            code[1] = span & 255
            relative.append(dict(before=at, after=instruction(at), target=reference(target), displacement=span))
        out.extend(code)
    labels = {(name[:-3]+"255" if name in names else name): reference(at)
              for name, at in before[1].items()}
    assert len(out) == len(blob)+648
    assert len(relative) == 61
    return [(origin, bytes(out))], labels, dict(insertions=[dict(address=point,
        relocated_entry=reference(point), extra_LDI=EXTRA_LDI, extra_bytes=54) for point in points],
        unchanged_relative_spans=relative)


def build(*, core=0x8000, prefix_cap=255):
    if prefix_cap not in (228, 255):
        raise ValueError("E04 contains only the cap228 self-check and one cap255 candidate")
    instances = []
    def factory(origin):
        result = _ContractedAssembler(origin, _SITES[228])
        instances.append(result)
        return result
    regions, labels, metadata = private_builder()(core=core, prefix_cap=prefix_cap,
        shared_prefixes=True, _assembler=factory)
    assembler, = instances
    assert len(assembler.changes) == 61
    assert {row["baseline_offset"] for row in assembler.changes} == {row[0] for row in _SITES[228]}
    if prefix_cap == 228:
        assert (regions, labels) == baseline(core=core, prefix_cap=228, policy="fast")[:2]
        oracle = dict(cap228_public_self_check_exact=True)
    else:
        expected_regions, expected_labels, oracle = binary_oracle(core)
        assert (regions, labels) == (expected_regions, expected_labels)
        assert metadata["service_memory_bytes"] == EXPECTED_SERVICE
    metadata = dict(metadata, test_only=True, measured_frontier=False,
        variant="next-e04-cap"+str(prefix_cap), caller_stack_bytes=4,
        startup_tstates=46, offset_reset_tstates=20,
        target_initializer_required=False,
        benchmark_call_scope="complete entry including offset reset, all parser/copy work, EOF and RET",
        conditional_branch_site_count=61, conditional_branch_sites=assembler.changes,
        independent_binary_and_label_oracle_exact=True, e04_oracle=oracle)
    return regions, labels, metadata


def boundary_cases():
    """Four reservoir phases for each existing family and length255..257.

    Changing the initial literal gamma depth by one consumes two more bits,
    cycling through the four odd phase entries without narrowing the format.
    Offset2 forces a new offset; initial offset1 forces reuse. A small new
    match separates the long literal from its initial seed.
    """
    from zx0.tokens import Token, encode
    for family in FAMILIES:
        seeds = (2, 4, 8, 16) if family != "reuse" else (1, 2, 4, 8)
        for seed_length in seeds:
            for count in (255, 256, 257):
                raw = bytearray(index % 251 for index in range(seed_length))
                tokens = [Token(0, len(raw))]
                if family == "literals":
                    tokens.append(Token(len(raw), 2, 2))
                    for _ in range(2): raw.append(raw[-2])
                    tokens.append(Token(len(raw), count))
                    raw.extend(index % 251 for index in range(count))
                else:
                    offset = 1 if family == "reuse" else 2
                    tokens.append(Token(len(raw), count, offset))
                    for _ in range(count): raw.append(raw[-offset])
                raw = bytes(raw)
                yield f"boundary-{family}-seed{seed_length}-length{count}", encode(raw, tokens), raw, dict(
                    family=family, decoded_length=count, seed_length=seed_length)
