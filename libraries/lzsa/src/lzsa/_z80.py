"""Small relocation-aware Z80 byte emitter; no converter dependencies."""
from typing import Sequence
from hashlib import sha256

def sha(data):
    return sha256(data).hexdigest()

class MiniAssembler:
    def __init__(self, origin: int):
        self.origin = origin
        self.code = bytearray()
        self.labels: dict[str, int] = {}
        self.abs_fixups: list[tuple[int, str]] = []
        self.rel_fixups: list[tuple[int, str]] = []

    @property
    def pc(self) -> int:
        return self.origin + len(self.code)

    def label(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"Duplicate label: {name}")
        self.labels[name] = self.pc

    def emit(self, *values: int) -> None:
        self.code.extend(v & 0xFF for v in values)

    def word(self, value: int) -> None:
        self.emit(value & 0xFF, value >> 8)

    def abs16(self, opcode: int | Sequence[int], label: str) -> None:
        if isinstance(opcode, int):
            self.emit(opcode)
        else:
            self.emit(*opcode)
        pos = len(self.code)
        self.emit(0, 0)
        self.abs_fixups.append((pos, label))

    def rel8(self, opcode: int, label: str) -> None:
        self.emit(opcode)
        pos = len(self.code)
        self.emit(0)
        self.rel_fixups.append((pos, label))

    def resolve(self, external_labels: dict[str, int] | None = None) -> bytes:
        labels = dict(self.labels)
        labels.update(external_labels or {})
        output = bytearray(self.code)
        for pos, label in self.abs_fixups:
            value = labels[label]
            output[pos] = value & 0xFF
            output[pos + 1] = value >> 8
        for pos, label in self.rel_fixups:
            operand_address = self.origin + pos
            next_address = operand_address + 1
            displacement = labels[label] - next_address
            if not -128 <= displacement <= 127:
                raise ValueError(f"Relative branch to {label} out of range: {displacement}")
            output[pos] = displacement & 0xFF
        return bytes(output)
