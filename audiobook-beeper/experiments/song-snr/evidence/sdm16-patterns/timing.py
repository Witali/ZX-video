"""Independent instruction-table totals for the standalone pattern proof."""
import json
from pathlib import Path


def main():
    # Each row runs from immediately after one OUT to completion of the next.
    # Both literal values use12-T OUT(C),r/OUT(C),0, and both nibble branches
    # have the same count. Unreachable slot padding is never CPU work.
    rows = [
        [('EXX', 4), ('OR L', 4), ('LD L,A', 4), ('LD SP,HL', 6), ('LD A,n', 7), ('OUT(n),A', 11)],
        [('POP BC', 10), ('LD A,n', 7), ('OUT(n),A', 11)],
        [('POP HL', 10), ('LD A,n', 7), ('OUT(n),A', 11)],
        [('ADD IX,BC', 15), ('EXX', 4), ('OUT(C),r', 12)],
        [('LD A,IXH', 8), ('LD L,A', 4), ('OUT(C),r', 12)],
        [('LD H,n', 7), ('LD H,(HL)', 7), ('OUT(C),r', 12)],
        [('LD L,E', 4), ('LD SP,HL', 6), ('OUT(C),r', 12)],
        [('JP(IY)', 8), ('OUT(C),r', 12)],
        [('POP HL', 10), ('OUT(C),r', 12)],
        [('POP IY', 14), ('OUT(C),r', 12)],
        [('POP DE', 10), ('OUT(C),r', 12)],
        [("EX AF,AF'", 4), ('CCF', 4), ('JP cc,nn', 10), ('OUT(C),r', 12)],
        [("EX AF,AF'", 4), ('EXX', 4), ('LD A,(DE)', 7), ('EXX', 4), ('OUT(C),r', 12)],
        [('AND n', 7), ('RLCA/RRCA', 4), ('RLCA/RRCA', 4), ('OUT(C),r', 12)],
        [('JP nn', 10), ('NOP', 4), ('NOP', 4), ('NOP', 4), ('OUT(C),r', 12)],
        [('JP(HL)', 4), ('OUT(C),r', 12)],
    ]
    holds = [sum(time for _, time in row) for row in rows]
    assert holds == [36,28,28,31,24,26,22,20,22,26,22,30,31,27,34,16]
    assert sum(holds) == 423
    high_tail = [('EXX',4),('INC E',4),('JP Z,nn not taken',10),('EXX',4),('OUT(C),r',12)]
    assert sum(time for _,time in high_tail) == holds[14]
    before_descriptor = [('EXX',4),('INC E',4),('JP Z,nn taken',10),('INC D',4),
                         ('JP Z,nn taken',10),("EX AF,AF'",4),('EXX',4),('LD B,n',7),
                         ('EXX',4),('JP bank_jump',10),('JP stream_bank_tail',10)]
    descriptor = [('LD(nn),HL',16),('LD HL,(nn)',16),('LD A,(HL)',7),('OR A',4),
                  ('JP Z,nn not taken',10),('LD(nn),A',13),('INC HL',6),('LD D,(HL)',7),
                  ('LD E,n',7),('INC HL',6),('LD A,(HL)',7),('INC HL',6),('LD(nn),HL',16),
                  ('LD HL,(nn)',16),('JP high_done',10),('LD BC,7FFD',10),('LD A,(nn)',13),
                  ('OUT(C),A',12),('EXX',4),('SCF',4),("EX AF,AF'",4),('OUT(C),B',12)]
    bank = sum(time for _,time in before_descriptor + descriptor)
    assert bank == 277 and bank - holds[14] == 243
    scorpion_high_switch = [('NOP',4),('NOP',4),('NOP',4),('LD BC,1FFD',10),('OUT(C),A',12)]
    scorpion_extra = sum(time for _,time in scorpion_high_switch) - 10
    assert scorpion_extra == 24 and bank + scorpion_extra - holds[14] == 267
    result = dict(instruction_timing_reference='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='Deterministic native CPU counts only. No ULA waits, TR-DOS ROM or physical floppy latency.',
        ordinary_instruction_intervals=rows, ordinary_holds=holds, ordinary_total=423,
        high_phase_interval14=high_tail, page_additional_instructions=[('INC D',4),('JP Z,nn not taken',10)],
        page_extra_tstates=14, bank_interval14_before_descriptor=before_descriptor,
        bank_interval14_descriptor=descriptor, bank_interval14_total=bank, bank_extra_tstates=243,
        scorpion_high_switch=scorpion_high_switch, scorpion_bank_interval14_total=301, scorpion_bank_extra_tstates=267,
        high_only_delta_tstates=0,
        first_and_high_extra_instructions=[('JP shared_FIRST_suffix',10)],
        both_halves_extra_instructions=[('JP shared_FIRST_suffix',10),('JP shared_SECOND_suffix, both phases',10)],
        legacy_pentagon_extra_instructions=[('JP delay',10),('NOP',4),('NOP',4),('NOP',4),('NOP',4)],
        both_halves_pentagon_extra_instructions=[('INC HL while dead after LD SP,HL',6)],
        both_halves_pentagon_total=423+20+6, both_halves_pentagon_delta_from449=0,
        both_halves_spectrum128_scorpion_total=443, both_halves_spectrum128_scorpion_delta=20)
    Path(__file__).with_name('timing.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(ordinary=423,pentagon=449,page_extra=14,bank_extra=243,scorpion_bank_extra=267)))


if __name__ == '__main__':
    main()
