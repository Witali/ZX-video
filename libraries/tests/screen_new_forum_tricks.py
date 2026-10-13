"""Screen forum primitives; this does not apply or qualify a codec change."""
import argparse
import json
from pathlib import Path

from measure_tricks import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    # Shift one indexed RAM byte. Memory and F agree; the new form leaves A
    # untouched, so it cannot replace a path that consumes the shifted A.
    indexed = 0
    for value in range(256):
        for carry in (0, 1):
            registers = dict(ix=0x6000, af=0x7300 | carry)
            old, ot = run('dd 7e 04 cb 3f dd 77 04', registers,
                          memory=((0x6004, bytes([value])),))
            new, nt = run('dd cb 04 3e', registers,
                          memory=((0x6004, bytes([value])),))
            assert old.memory[0x6004] == new.memory[0x6004] == value >> 1
            assert old.f == new.f and (ot, nt) == (46, 23)
            assert all(getattr(old, key) == getattr(new, key)
                       for key in ('bc', 'de', 'hl', 'ix', 'iy', 'sp'))
            indexed += 1

    # Decrement A without crossing 23, assuming A already lies in 23..255.
    # The forum sequence misses the bound by one. Even the corrected result
    # has different F, so this is only an A-value equivalence demonstration.
    lower_checks = flag_differences = 0
    first_failure = None
    for value in range(23, 256):
        old, ot = run('3d fe 17 30 01 3c', dict(af=value << 8))
        original, _ = run('d6 17 ce 16', dict(af=value << 8))
        corrected, nt = run('d6 18 ce 17', dict(af=value << 8))
        assert old.a == corrected.a == max(23, value - 1)
        assert ot == (22 if value == 23 else 23) and nt == 14
        flag_differences += old.f != corrected.f
        lower_checks += 1
        if original.a != old.a and first_failure is None:
            first_failure = dict(input=value, expected=old.a,
                                 forum_sequence_result=original.a)
    assert first_failure == dict(input=23, expected=23, forum_sequence_result=22)

    # Clear two adjacent state bytes in one word store. AF/HL differ, and
    # interrupt-visible ordering needs a caller-specific proof before use.
    old, ot = run('af 32 04 60 32 05 60', dict(hl=0x7373, af=0x9737))
    new, nt = run('21 00 00 22 04 60', dict(hl=0x7373, af=0x9737))
    assert bytes(old.memory[0x6004:0x6006]) == bytes(new.memory[0x6004:0x6006]) == bytes(2)
    assert (ot, nt) == (30, 26)

    report = dict(
        date='2026-10-13', baseline_revision='12d4eeac', complete=True,
        release=False, scope=__doc__, decoder_changes=0,
        indexed_shift=dict(
            checks=indexed, before_tstates=46, after_tstates=23, delta=-23,
            code_bytes_before=8, code_bytes_after=4, source_post=534511,
            condition='A result must be dead; preserve index, address and memory ownership.'),
        bounded_decrement=dict(
            checks=lower_checks, input_range=[23, 255], source_posts=[170101, 170717],
            first_source_counterexample=first_failure, corrected_bytes='d6 18 ce 17',
            before_tstates=[22, 23], after_tstates=14,
            code_bytes_before=6, code_bytes_after=4,
            flag_differences=flag_differences,
            condition='Input already within the bound; final flags must be dead.'),
        adjacent_byte_clear=dict(
            checks=1, before_tstates=30, after_tstates=26, delta=-4,
            code_bytes_before=7, code_bytes_after=6,
            condition='Contiguous two bytes; AF/HL side effects must be dead and IRQ may not observe a forbidden intermediate state.'),
        applied_to_codecs=False, full_decoder_replay=False,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(indexed_shift_checks=indexed,
                          bounded_decrement_checks=lower_checks,
                          source_counterexample=first_failure, codec_changes=0)))


if __name__ == '__main__':
    main()
