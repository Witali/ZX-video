"""Logical S/P branches for the small component CPU, independently cross-checked.

The base emulator models Z/C only. Support S/P produced by AND/OR/XOR in
the current basic block; fail if a new branch depends on any other flag flow.
This is deliberately not a general implementation of arithmetic overflow.
"""
from validate_fast_sparse import CPU


class LogicalFlags:
    def instruction(self):
        op = CPU.read8(self, self.pc)
        if op in (0xEA, 0xF2, 0xFA):
            if not getattr(self, '_logical_flags_ready', False):
                raise AssertionError('S/P branch without modeled logical flags')
            self.pc = (self.pc + 1) & 65535
            target = self.fetch16()
            take = {0xEA: self._logical_parity, 0xF2: not self._logical_sign,
                    0xFA: self._logical_sign}[op]
            if take:
                self.pc = target
            self._logical_flags_ready = False
            return 10
        if op == 0x37:
            self.pc = (self.pc + 1) & 65535
            self.carry = True
            self._logical_flags_ready = False
            return 4
        result = super().instruction()
        if 0xA0 <= op <= 0xB7 or op in (0xE6, 0xEE, 0xF6):
            self._logical_sign = bool(self.a & 128)
            self._logical_parity = self.a.bit_count() % 2 == 0
            self._logical_flags_ready = True
        elif op != 0x23:  # INC HL preserves all flags between OR (HL) and JP M.
            self._logical_flags_ready = False
        return result
