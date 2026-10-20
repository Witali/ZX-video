"""S01 bounded Standard layouts; private generators and binary cross-checks.

The fixed-vector RST idea is rejected before emission: its 0028h..0036h
helper occupies Spectrum ROM. Only the reset-complete SMC layout and one
baseline-count-selected unconditional JP intermediate are screened.
"""
from collections import Counter
import inspect

from zx0 import codec
from zx0.block import build as standard
from zx0._z80 import MiniAssembler, sha
from profile_branch_mix import instructions


BASELINE_HEX = "01ffffc5033e80cd3580edb087380dcd3580e3e519edb0e1e38730ebc10efecd36800cc8414e23cb18cb19c5010100d43d800318dd0c8720037e2317d887cb11cb1018f2"
KINDS = ("smc", "gamma-jp", "copy-jp")


def _emit(kind, core):
    """Same complete format; SMC substitutes only previous-offset storage."""
    a = MiniAssembler(core)
    def emit(*values): a.emit(*values)
    def call(op, label): a.abs16(op, label)
    def jump(op, label, site=None):
        if (kind, site) in (("gamma-jp", "gamma"), ("copy-jp", "copy")):
            a.abs16(0xc3, label)
        else:
            a.rel8(op, label)
    a.label("dzx0_standard")
    emit(0x01, 0xff, 0xff)
    if kind == "smc":
        # Initialize the writable negative offset on EVERY call, even if the
        # operand was poisoned by an earlier client. This 20T store is part
        # of the measured entry and its four bytes are resident code.
        call((0xed, 0x43), "s01_offset")
    else:
        emit(0xc5)
    emit(0x03, 0x3e, 0x80)
    a.label("dzx0s_literals")
    call(0xcd, "dzx0s_elias"); emit(0xed, 0xb0, 0x87)
    jump(0x38, "dzx0s_new_offset")
    call(0xcd, "dzx0s_elias")
    a.label("dzx0s_copy")
    if kind == "smc":
        # The source occupies the same two temporary stack bytes as a gamma
        # return. Loading the offset replaces both EX(SP),HL instructions:
        # 42T versus70T, excluding the identical LDIR. Peak caller stack4B.
        emit(0xe5)
        a.labels["s01_offset"] = a.pc+1
        emit(0x21, 0xff, 0xff, 0x19, 0xed, 0xb0, 0xe1)
    else:
        emit(0xe3, 0xe5, 0x19, 0xed, 0xb0, 0xe1, 0xe3)
    emit(0x87); jump(0x30, "dzx0s_literals")
    a.label("dzx0s_new_offset")
    if kind != "smc": emit(0xc1)
    emit(0x0e, 0xfe); call(0xcd, "dzx0s_elias_loop")
    emit(0x0c, 0xc8, 0x41, 0x4e, 0x23, 0xcb, 0x18, 0xcb, 0x19)
    if kind == "smc":
        call((0xed, 0x43), "s01_offset")
    else:
        emit(0xc5)
    emit(0x01, 1, 0); call(0xd4, "dzx0s_elias_backtrack")
    emit(0x03); jump(0x18, "dzx0s_copy", "copy")
    # Keep both full 16-bit rotations. Shortening to an eight-bit gamma
    # counter would fail legal lengths256..65535 and is not an S01 option.
    a.label("dzx0s_elias"); emit(0x0c)
    a.label("dzx0s_elias_loop"); emit(0x87)
    jump(0x20, "dzx0s_elias_skip"); emit(0x7e, 0x23, 0x17)
    a.label("dzx0s_elias_skip"); emit(0xd8)
    a.label("dzx0s_elias_backtrack"); emit(0x87, 0xcb, 0x11, 0xcb, 0x10)
    jump(0x18, "dzx0s_elias_loop", "gamma")
    return a


def binary_oracle(kind, core):
    """Independently remap pinned Standard instructions and their branches."""
    baseline = standard("standard", core=core, core_limit=core+256)
    assert standard("standard")[0][0][1].hex() == BASELINE_HEX
    blob = baseline[0][0][1]
    replacements = {}
    if kind == "smc":
        replacements = {3: bytes.fromhex("ed430000"), 18: b"\xe5",
            19: bytes.fromhex("21ffff"), 24: b"", 28: b"",
            43: bytes.fromhex("ed430000")}
    elif kind in ("gamma-jp", "copy-jp"):
        replacements[66 if kind == "gamma-jp" else 51] = b"\xc3\x00\x00"
    output = bytearray(); mapping = {}; entries = list(instructions(blob, core))
    for address, opcode in entries:
        offset = address-core
        mapping[offset] = len(output)
        output.extend(replacements.get(offset, opcode))
    mapping[len(blob)] = len(output)
    labels = {name: core+mapping[address-core] for name, address in baseline[1].items()}
    if kind == "smc": labels["s01_offset"] = core+mapping[19]+1
    for address, opcode in entries:
        offset = address-core; at = mapping[offset]
        if offset in replacements:
            if kind == "smc" and offset in (3, 43):
                output[at+2:at+4] = labels["s01_offset"].to_bytes(2, "little")
            elif kind != "smc":
                target = offset+2+int.from_bytes(opcode[1:], "little", signed=True)
                output[at+1:at+3] = (core+mapping[target]).to_bytes(2, "little")
        elif opcode[0] in (0xcd, 0xd4):
            target = int.from_bytes(opcode[1:], "little")-core
            output[at+1:at+3] = (core+mapping[target]).to_bytes(2, "little")
        elif opcode[0] in (0x18, 0x20, 0x30, 0x38):
            target = offset+2+int.from_bytes(opcode[1:], "little", signed=True)
            displacement = mapping[target]-(at+2)
            assert -128 <= displacement <= 127
            output[at+1] = displacement & 255
    return [(core, bytes(output))], labels


def build(kind, *, core=0x8000):
    if kind not in KINDS+("standard",): raise ValueError(kind)
    a = _emit(kind, core)
    regions = [(core, a.resolve())]
    assert (regions, a.labels) == binary_oracle(kind, core)
    stack = 4 if kind == "smc" else 6
    expected = {"standard": 68, "smc": 74, "gamma-jp": 69, "copy-jp": 69}[kind]
    assert len(regions[0][1]) == expected
    patches = [a.labels["s01_offset"], a.labels["s01_offset"]+1] if kind == "smc" else []
    service = dict(code_tables_alignment_and_embedded_state_bytes=expected,
        caller_stack_bytes=stack, variables=0, scratch_bytes=0, internal_buffer_bytes=0)
    return regions, a.labels, dict(entry="dzx0_standard", variant="next-s01-zx0-"+kind,
        test_only=True, raw_only=True, code_bytes=expected,
        service_memory=service, service_memory_bytes=sum(service.values()),
        caller_stack_bytes=stack, patched_addresses=patches,
        embedded_mutable_bytes=len(patches), embedded_state_counted_once_in_code=True,
        target_initializer_required=False,
        initialization_scope="all required setup is inside each start-through-EOF call",
        ROM_compatible=not patches, nonreentrant=bool(patches), code_sha256=sha(regions[0][1]))


_host_source = inspect.getsource(codec.decompress)
assert _host_source.count("        return result\n") == 1
_host_source = _host_source.replace("        return result\n", """        _s01_counts['gamma_backtracks'] += result.bit_length()-1
        _s01_counts['new_offset_entries'] += bool(inverted)
        return result
""")
_host_namespace = dict(vars(codec), _s01_counts=Counter())
exec(compile(_host_source, "<S01 host gamma counters>", "exec"), _host_namespace)


def host_counts(payload, raw):
    counts = _host_namespace["_s01_counts"]
    counts.clear()
    def match(*args): counts["match_copies"] += 1
    decoded = _host_namespace["decompress"](payload, limit=len(raw), on_match=match)
    assert decoded == raw
    result = dict(counts)
    result.setdefault("match_copies", 0)
    result["copy_back_jumps"] = result["new_offset_entries"]-1
    return result


def predicted_delta(kind, counts):
    if kind == "smc": return -28*counts["match_copies"]-counts["new_offset_entries"]
    if kind == "gamma-jp": return -2*counts["gamma_backtracks"]
    if kind == "copy-jp": return -2*counts["copy_back_jumps"]
    raise ValueError(kind)
