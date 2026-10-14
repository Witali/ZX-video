"""Check outside-site Z80 primitives; no codec integration or release qualification."""
import argparse
import json
from pathlib import Path

from measure_tricks import run
from test_libraries import profiles, ROOT


def residue_copy():
    # Derived residue-entry loop at 0200. AF is saved while A patches the JR
    # displacement. No DI/EI is inserted: the caller must own writable code,
    # forbid reentrant calls, and preserve live registers in its IRQ handler.
    # BC must be positive. LDI computes P/V immediately before each JP PE.
    code = 'f5 af 91 e6 0f 87 32 0b 02 f1 18 00 ' + 'ed a0 ' * 16 + 'ea 0c 02'
    checks = overlap_checks = 0
    lengths = list(range(1, 513)) + [513, 767, 768, 1023, 1024, 2048, 4096]
    examples = []
    for count in lengths:
        registers = dict(hl=0x3000, de=0x6000, bc=count, af=0x7355)
        raw = bytes(index % 251 for index in range(count))
        old, ot = run('ed b0', registers, memory=((0x3000, raw),))
        new, nt = run(code, registers, memory=((0x3000, raw),))
        assert bytes(old.memory[0x6000:0x6000+count]) == raw
        assert bytes(new.memory[0x6000:0x6000+count]) == raw
        assert tuple(getattr(old, key) for key in ('hl', 'de', 'bc', 'af', 'sp')) == tuple(
            getattr(new, key) for key in ('hl', 'de', 'bc', 'af', 'sp'))
        assert (ot, nt) == (21*count-5, 65+16*count+10*((count+15)//16))
        checks += 1
        if count in (1, 16, 17, 18, 19, 36, 37, 64, 256, 4096):
            row = dict(bytes=count, ldir_tstates=ot, residue_loop_tstates=nt, delta=nt-ot)
            if count >= 17:
                row['sixteen_ldi_then_ldir_tstates'] = 21*count-85
                row['delta_from_sixteen_prefix'] = nt-(21*count-85)
            examples.append(row)
    for distance in (1, 2):
        for count in (1, 15, 16, 17, 18, 31, 32, 33, 255, 256, 257, 4096):
            registers = dict(hl=0x6000-distance, de=0x6000, bc=count, af=0x9741)
            seed = bytes(range(65, 65+distance))
            memory = ((0x6000-distance, seed),)
            old, _ = run('ed b0', registers, memory=memory)
            new, _ = run(code, registers, memory=memory)
            expected = bytes(seed[index % distance] for index in range(count))
            assert bytes(old.memory[0x6000:0x6000+count]) == expected
            assert bytes(new.memory[0x6000:0x6000+count]) == expected
            overlap_checks += 1
    return dict(checks=checks, overlapping_match_checks=overlap_checks,
        positive_counts_only=True, code_bytes_before=2, code_bytes_after=47,
        code_bytes_added=45, setup_tstates=65, examples=examples,
        condition='Preserved AF; nonzero BC, readable/writable extents, writable private code, no reentrant use; streaming/IRQ integration remains untested.')


def stack_exchange():
    checks = 0
    for hl in (0, 0xff, 0x1234, 0xffff):
        for de in (0, 0x5678, 0xffff):
            for word in (0, 1, 0x9abc, 0xffff):
                for carry in (0, 1):
                    registers = dict(hl=hl, de=de, af=0x7300 | carry, bc=0x2468)
                    memory = ((0xbff0, word.to_bytes(2, 'little')),)
                    old, ot = run('eb e1 d5', registers, memory=memory)
                    new, nt = run('e3', registers, memory=memory)
                    assert (old.hl, old.sp, old.af, old.bc) == (new.hl, new.sp, new.af, new.bc)
                    assert bytes(old.memory[0xbff0:0xbff2]) == bytes(new.memory[0xbff0:0xbff2]) == hl.to_bytes(2, 'little')
                    assert (ot, nt) == (25, 19)
                    checks += 1
    return dict(checks=checks, before_tstates=25, after_tstates=19, delta=-6,
        code_bytes_before=3, code_bytes_after=1,
        condition='DE must be dead: the old form puts the original HL in DE, while EX (SP),HL leaves DE unchanged. The stack word must be owned.')


def byte_add():
    checks = 0
    for hl in (0, 1, 0xff, 0x100, 0x1234, 0x7fff, 0x8000, 0xff00, 0xffff):
        for value in range(256):
            for carry in (0, 1):
                registers = dict(hl=hl, de=0x4567, af=(value << 8) | carry)
                old, ot = run('d5 5f 16 00 19 d1', registers)
                # Our fixed-time variant of WikiTI's byte-add construction.
                # ADD produces the low-byte carry; ADC/SUB recover the new H.
                new, nt = run('85 6f 8c 95 67', registers)
                assert old.hl == new.hl == (hl+value) & 65535
                assert old.de == new.de == 0x4567 and old.sp == new.sp
                assert (ot, nt) == (43, 20)
                checks += 1
    return dict(checks=checks, before_tstates_with_de_saved=43,
        before_tstates_with_de_scratch=22, after_tstates=20,
        code_bytes_before_with_de_saved=6, code_bytes_before_with_de_scratch=4,
        code_bytes_after=5, condition='A and final flags must be dead; DE is preserved. If the high byte of an available scratch pair is already zero, its cheaper form may win.')


def constant_subtract():
    checks = 0
    for hl in (0, 1, 0xff, 0x100, 0x1234, 0x7fff, 0x8000, 0xff00, 0xffff):
        for value in (0, 1, 42, 0x8000, 0xffff):
            registers = dict(hl=hl, af=0x7355)
            old, ot = run('01 '+value.to_bytes(2, 'little').hex(' ')+' b7 ed 42', registers)
            negative = (-value) & 65535
            new, nt = run('01 '+negative.to_bytes(2, 'little').hex(' ')+' 09', registers)
            assert old.hl == new.hl == (hl-value) & 65535
            assert (ot, nt) == (29, 21)
            checks += 1
    return dict(checks=checks, before_tstates=29, after_tstates=21, delta=-8,
        code_bytes_before=6, code_bytes_after=4,
        condition='Arithmetic result only; BC and all resulting flags must be dead. Not a replacement for an unsigned bounds comparison.')


def loops():
    checks = 0
    for count in range(1, 257):
        registers = dict(bc=(count & 255) << 8, hl=0x3000, af=0x7301)
        old, ot = run('23 05 20 fc', registers)
        new, nt = run('23 10 fd', registers)
        assert old.hl == new.hl == 0x3000+count and old.b == new.b == 0
        assert (ot, nt) == (22*count-5, 19*count-5)
        checks += 1
    return dict(checks=checks, before_tstates='22*n-5', after_tstates='19*n-5',
        delta='-3*n', code_bytes_before=4, code_bytes_after=3,
        condition='Body is INC HL; final DEC flags must be dead. B must not simultaneously be modified by LDI/LDIR or used as a token byte.')


def compare_restore():
    # LZSA2 sync reloads its target after subtracting block_end. Adding the
    # same DE restores HL instead. ADD retains S/Z/PV and its carry equals
    # the subtraction borrow: only a wrapped difference overflows on restore.
    # H/N/undocumented flags differ, so they must not be consumed afterwards.
    checks = 0
    values = (0, 1, 0xff, 0x100, 0x1234, 0x7fff, 0x8000, 0xc000,
              0xfeff, 0xff00, 0xfffe, 0xffff)
    for target in values:
        for end in values:
            for carry in (0, 1):
                registers = dict(hl=target, de=end, af=0x7300 | carry)
                memory = ((0x6004, target.to_bytes(2, 'little')),)
                old, ot = run('b7 ed 52 2a 04 60', registers, memory=memory)
                new, nt = run('b7 ed 52 19', registers, memory=memory)
                assert old.hl == new.hl == target and old.de == new.de == end
                assert old.a == new.a and ((old.f ^ new.f) & 0xc5) == 0
                assert bool(new.f & 1) == (target < end)
                assert bool(new.f & 0x40) == (target == end)
                assert (ot, nt) == (35, 30)
                checks += 1
    return dict(checks=checks, before_tstates=35, after_tstates=30, delta=-5,
        code_bytes_before=6, code_bytes_after=4,
        condition='HL restored from the same DE just subtracted; S/Z/PV/C agree, H/N and undocumented flags may differ. Proposed LZSA2 sync mapping not integrated.')


def repeat_fill():
    # Our sixteen-byte distance-1 specialization. Use full INC HL, so no
    # page-alignment assumption is hidden. Reconstruct HL=DE-1 at exit and
    # preserve A/AF' and the private stack. Final F differs from LDIR.
    code = 'f5 7e eb ' + '77 23 ' * 16 + '54 5d 2b 01 00 00 f1'
    checks = 0
    for destination in (0x6000, 0x60f0, 0x60ff):
        for value in range(256):
            registers = dict(hl=destination-1, de=destination, bc=16, af=0x7395)
            memory = ((destination-1, bytes([value])),)
            old, ot = run('ed b0', registers, memory=memory)
            new, nt = run(code, registers, memory=memory)
            assert bytes(old.memory[destination:destination+16]) == bytes([value])*16
            assert bytes(new.memory[destination:destination+16]) == bytes([value])*16
            assert tuple(getattr(old, key) for key in ('hl', 'de', 'bc', 'a', 'sp')) == tuple(
                getattr(new, key) for key in ('hl', 'de', 'bc', 'a', 'sp'))
            assert ((old.f ^ new.f) & 0xc1) == 0
            assert (ot, nt) == (331, 264)
            checks += 1
    return dict(checks=checks, exact_length=16, distance=1,
        before_tstates=331, after_tstates=264, delta=-67,
        code_bytes_before=2, code_bytes_after=42,
        condition='Exact distance 1 and length 16 already known, final F dead except preserved carry/S/Z. Excludes dispatch/length checks, variable remainder, streaming guards and IRQ validation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    defaults = profiles()
    assert defaults == json.loads((ROOT/'tests/decoder_baseline.json').read_text())['profiles']
    report = dict(date='2026-10-14', baseline_revision='5abac404', complete=True,
        release=False, scope=__doc__, default_profiles=len(defaults), default_layouts_exact=True,
        residue_copy=residue_copy(), stack_exchange=stack_exchange(),
        byte_add=byte_add(), constant_subtract=constant_subtract(),
        djnz_loop=loops(), compare_restore=compare_restore(), distance_one_fill=repeat_fill(),
        decoder_changes=0, complete_decoder_replay=False, irq_delivery_measured=False,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(primitive_groups=7,
        native_cases=sum(report[name]['checks'] for name in (
            'residue_copy','stack_exchange','byte_add','constant_subtract','djnz_loop','compare_restore','distance_one_fill'))
            + report['residue_copy']['overlapping_match_checks'],
        defaults=len(defaults), codec_changes=0)))


if __name__ == '__main__':
    main()
