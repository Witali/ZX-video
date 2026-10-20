"""Fixed raw Hybrid hot-path specializations, with no corpus dependency.

The literal clone specializes token248 and the nibble pair specializes only
body167_0. All other token forms retain the fixed fast Hybrid layout. These
are complete resident block decoders, without quota or partial-input hooks.
"""
from hashlib import sha256
import json

from . import hybrid
from ._z80 import MiniAssembler


_PROFILES = {"literals": 9529, "nibble": 9515, "combined": 9545}
_REAL_TSTATES = {"literals": 14913435, "nibble": 14918596, "combined": 14905725}
# Canonical code/fixup/label fingerprints exclude only placement and the
# required page-alignment padding. They cover the entire emitted decoder,
# including the unchanged kernels and both static dispatch pages.
_FINGERPRINTS = {
    "literals": "febff507e2536cb3dc9cffe9d3ddd6faea0b1868fcf4577101d5e2c7fa9c7572",
    "nibble": "8cc5cab46c5dc3b9f7ecf26cd0d9ec64d59af5866043f393657c51b2de42c95a",
    "combined": "75d583a822db0362193f1e59e29037702318c111908b99e6d494378463ee8c43",
}


class _HotAssembler(MiniAssembler):
    """Replace two bounded emitter event sequences; reject generator drift."""

    def __init__(self, origin, profile):
        super().__init__(origin)
        self.profile = profile
        self.literals = profile in ("literals", "combined")
        self.nibbles = profile in ("nibble", "combined")
        self._internal = False
        self._reader = None
        self._body_events = None
        self._body_index = 0
        self._clone_count = self._cold_count = self._pair_count = 0
        self._validated = False

    def _raw(self, method, *args):
        previous = self._internal
        self._internal = True
        try:
            return method(*args)
        finally:
            self._internal = previous

    def _event(self, event):
        if self._body_events is None:
            return False
        if event != self._body_events[self._body_index]:
            raise ValueError("Hot nibble body emitter drift")
        self._body_index += 1
        if self._body_index == len(self._body_events):
            self._body_events = None
            self._emit_pair()
            self._pair_count += 1
        return True

    def label(self, name):
        if self._internal:
            return super().label(name)
        if self._event(("label", name)):
            return
        super().label(name)
        if self.nibbles and name == "body_167_0":
            # Suppress only the exact old reader/offset/length body. Keep PC
            # stationary until its terminal JP, then emit the specialized
            # pair. The enclosing generator consequently records its true
            # replacement body size and subsequent absolute label names.
            target = "nibble_167_" + str(self.pc)
            self._body_events = (
                ("emit", (0x37, 8)), ("rel8", 0x30, target),
                ("emit", (0x7e, 0xb7, 8, 0x7e)), ("emit", (0x23,)),
                ("emit", (0x0f, 0x0f, 0x0f, 0x0f)), ("label", target),
                ("emit", (0xf6, 0xf0)), ("emit", (0x3d, 0x87)),
                ("emit", (0x47, 0x4e)), ("emit", (0x23,)),
                ("abs16", (0xed, 0x43), "offset"),
                ("emit", (0x06, 0)), ("abs16", 0xc3, "LongerMatch"),
            )
            self._body_index = 0

    def emit(self, *values):
        if self._internal:
            return super().emit(*values)
        if self._event(("emit", values)):
            return
        if self._reader is not None:
            address, target = self._reader
            if self.pc != address or values != (0x7e, 0xb7, 8, 0x7e):
                raise ValueError("Hot nibble reader emitter drift")
            super().label("e03_known_empty_" + target)
            self._reader = None
        super().emit(*values)

    def rel8(self, opcode, label):
        if self._internal:
            return super().rel8(opcode, label)
        if self._event(("rel8", opcode, label)):
            return
        self._raw(super().rel8, opcode, label)
        if self.nibbles and opcode == 0x30 and (
                label in ("LongMatchNibble", "LongLiteralNibble") or
                label.startswith("nibble_")):
            self._reader = (self.pc, label)

    def abs16(self, opcode, label):
        if self._internal:
            return super().abs16(opcode, label)
        if self._event(("abs16", opcode, label)):
            return
        if self.literals and opcode == 0xcd and label == "LongLiterals" and (
                self.pc == self.labels.get("token_248", -2) + 1):
            if self.code[-1:] != b"\xd9" or self._clone_count:
                raise ValueError("Hot literal call-site emitter drift")
            self._emit_clone()
            self._clone_count += 1
            return
        cold = self.literals and opcode == 0xc3 and label == "MatchUseC" and (
            self.pc == self.labels.get("body_224_1", -3) + 2)
        if cold and (self.code[-2:] != b"\x0e\x02" or self._cold_count):
            raise ValueError("Hot literal cold-block emitter drift")
        self._raw(super().abs16, opcode, label)
        if cold:
            # The old body has already ended in JP MatchUseC. Its cold
            # literal escape can therefore live here without a new hot jump.
            self._raw(super().label, "E02CloneCold")
            self._raw(super().abs16, 0xcd, "ManyLiterals")
            self._raw(super().abs16, 0xc3, "E02CloneContinue")
            self._cold_count += 1

    def _emit_clone(self):
        # Token248's LL3 nibble form falls into its original match body.
        # Removing CALL/RET saves27T. Byte/word escapes CALL the unchanged
        # helper in the unreachable cold block, then JP back (+10T).
        self._raw(super().label, "E02CloneStart")
        self._raw(super().emit, 0x37, 8)
        self._raw(super().rel8, 0x30, "E02CloneNibble")
        if self.nibbles:
            self._raw(super().label, "e03_known_empty_E02CloneNibble")
        self._raw(super().emit, 0x7e, 0xb7, 8, 0x7e, 0x23,
                  0x0f, 0x0f, 0x0f, 0x0f)
        self._raw(super().label, "E02CloneNibble")
        self._raw(super().emit, 0xf6, 0xf0, 0x3c)
        self._raw(super().rel8, 0x28, "E02CloneCold")
        self._raw(super().emit, 0xd6, 238, 0x4f,
                  0xed, 0xa0, 0xed, 0xa0, 0xed, 0xb0)
        self._raw(super().label, "E02CloneContinue")

    def _emit_pair(self):
        # A cached offset nibble consumes AF' and proves the next reservoir
        # empty. Route only that arm past LongMatch's SCF/EX/JR (-15T).
        # A refill still leaves a cached nibble and uses ordinary LongerMatch.
        # Both arms store the same negative offset and restore B=0. No new
        # mutable state, stack word or assumption about the next length arises.
        self._raw(super().label, "e03_hot_first")
        self._raw(super().emit, 0x37, 8)
        self._raw(super().rel8, 0x30, "e03_hot_cached")
        self._raw(super().emit, 0x7e, 0xb7, 8, 0x7e, 0x23,
                  0x0f, 0x0f, 0x0f, 0x0f, 0xf6, 0xf0,
                  0x3d, 0x87, 0x47, 0x4e, 0x23)
        self._raw(super().abs16, (0xed, 0x43), "offset")
        self._raw(super().emit, 0x06, 0)
        self._raw(super().abs16, 0xc3, "LongerMatch")
        self._raw(super().label, "e03_hot_cached")
        self._raw(super().emit, 0xf6, 0xf0, 0x3d, 0x87, 0x47, 0x4e, 0x23)
        self._raw(super().abs16, (0xed, 0x43), "offset")
        self._raw(super().emit, 0x06, 0)
        self._raw(super().abs16, 0xc3, "e03_known_empty_LongMatchNibble")

    def _fingerprint(self, resolved):
        table = (self.origin + 255) & ~255
        padding = table - self.origin
        normalized = bytearray(resolved[padding:])
        # Every absolute code/state reference is generated through abs16;
        # normalize its address against the dispatch table's page boundary.
        for position, label in self.abs_fixups:
            value = self.labels[label] - table
            normalized[position-padding:position-padding+2] = value.to_bytes(2, "little")
        normalized[self.labels["token_body"]-table+5] = 0

        def name(label):
            if label.startswith(("nibble_", "short_ready_", "e03_known_empty_nibble_")):
                head, _, address = label.rpartition("_")
                return head + "_" + str(int(address)-table)
            return label

        contract = dict(code=normalized.hex(),
            labels=sorted((name(key), value-table) for key, value in self.labels.items()),
            absolute=[(position-padding, name(label)) for position, label in self.abs_fixups],
            relative=[(position-padding, name(label)) for position, label in self.rel_fixups])
        return sha256(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()

    def resolve(self, external_labels=None):
        if external_labels is not None:
            raise ValueError("Hot profiles do not support external wrapper labels")
        if (self._body_events is not None or self._reader is not None or
                self._clone_count != int(self.literals) or
                self._cold_count != int(self.literals) or
                self._pair_count != int(self.nibbles)):
            raise ValueError("Hot emitter did not encounter its complete fixed layout")
        result = super().resolve()
        padding = ((self.origin+255) & ~255)-self.origin
        if len(result)-padding+6 != _PROFILES[self.profile]:
            raise ValueError("Hot decoder size drift")
        fingerprint = self._fingerprint(result)
        if fingerprint != _FINGERPRINTS[self.profile]:
            raise ValueError("Hot decoder canonical fingerprint drift: " + fingerprint)
        self._validated = True
        return result


def build(profile="combined", *, core=0x8000, core_limit=0xc000):
    """Return regions, labels and actual service inventory for one raw block.

    HL=input and DE=output; start performs all required per-block setup and
    exact EOF restores the saved alternate HL. IX/IY and alternate BC/DE/HL
    survive. AF/AF'/BC/DE/HL may change. Reserve six caller-stack bytes,
    including the return word, plus real IRQ headroom. IRQ preserves both
    live register sets. The two-byte offset operand is writable, counted in
    code, and nonreentrant. Input and complete output/history stay resident
    in separate caller buffers. There is no quota/partial-input wrapper.

    Dispatch pages are static bytes in the emitted image. There is no target
    initializer or omitted preparation cost; entry through EOF is the whole
    decode call. The host Python generator is not target service memory.
    """
    if not isinstance(profile, str) or profile not in _PROFILES:
        raise ValueError("unknown Hot profile; use combined, literals or nibble")
    if type(core) is not int or type(core_limit) is not int:
        raise ValueError("Hot code reservation must use integer addresses")
    assemblers = []

    def factory(origin):
        assembler = _HotAssembler(origin, profile)
        assemblers.append(assembler)
        return assembler

    regions, labels, metadata = hybrid.build("fast", core=core, core_limit=core_limit,
        cold_match_extension=True, _assembler=factory)
    if len(assemblers) != 1 or not assemblers[0]._validated:
        raise ValueError("Hot assembler hook was not applied exactly once")
    # Wide fills dispatch pages after resolve(). Authenticate that final
    # image step as well as the assembler's complete code/fixup contract.
    if len(regions) != 1 or regions[0][0] != core:
        raise ValueError("Hot decoder region layout drift")
    blob = regions[0][1]
    padding = ((core+255) & ~255)-core
    if len(blob) != _PROFILES[profile]-6+padding:
        raise ValueError("Hot final code size drift")
    for token in range(256):
        target = blob[padding+token] | (blob[padding+256+token] << 8)
        if target != labels["token_"+str(token)]:
            raise ValueError("Hot final token dispatch table drift")
    metadata = {key: value for key, value in metadata.items()
                if not key.startswith(("reference_", "classic_reference_", "nominal_"))}
    code = sum(len(blob) for _, blob in regions)
    service = dict(code_tables_alignment_and_embedded_state_bytes=code,
        extra_variables=0, caller_stack_bytes=6, scratch_bytes=0, internal_buffer_bytes=0)
    metadata.update(variant="hot-"+profile+"-block", hot_profile=profile,
        raw_only=True, code_bytes=code, service_memory=service,
        service_memory_bytes=code+6, total_storage_bytes=code+6,
        nominal_aligned_service_bytes=_PROFILES[profile],
        reference_real_tstates=_REAL_TSTATES[profile],
        reference_real_tstates_scope="frozen 21 real raw blocks; complete entry setup through EOF; no IRQ/ULA/disk",
        caller_stack_bytes=6, decoder_stack_bytes=4, embedded_mutable_bytes=2,
        embedded_state_counted_once_in_code=True,
        target_initializer_required=False, runtime_generated_table_bytes=0,
        static_dispatch_table_bytes=512,
        benchmark_call_scope="complete start entry, per-block setup and exact EOF return",
        hot_literal_clone=profile in ("literals", "combined"),
        hot_nibble_pair=profile in ("nibble", "combined"),
        hot_path_delta_tstates=dict(
            token248_nibble=-27 if profile in ("literals", "combined") else 0,
            token248_byte_or_word=10 if profile in ("literals", "combined") else 0,
            body167_0_cached_offset=-15 if profile in ("nibble", "combined") else 0,
            body167_0_refilled_offset=0))
    return regions, labels, metadata
