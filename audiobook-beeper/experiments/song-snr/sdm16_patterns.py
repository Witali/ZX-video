"""Native proof of source-independent shared PDM pattern bodies.

Only standalone experiment assembly/evidence is emitted. The actual player,
table selection, IMA stream, modulation order and quality model are unchanged.
"""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from ram_machine import MemoryMachine


HERE = Path(__file__).resolve().parent
AUDIO = HERE.parents[1]
PROFILES = ('128', 'scorpion', 'pentagon512', 'pentagon1024')


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def pulse(bit):
    return ' OUT (C),D\n' if bit else ' DB 0xED,0x71\n'


def immediate(bit):
    return f' LD A,{16 if bit else 0}\n OUT (0xFE),A\n'


def first_prefix(value):
    return (pulse(value >> 7 & 1) + ' EXX\n OR L\n LD L,A\n LD SP,HL\n' +
            immediate(value >> 6 & 1) + ' POP BC\n' + immediate(value >> 5 & 1) +
            ' POP HL\n' + immediate(value >> 4 & 1) + ' ADD IX,BC\n EXX\n')


def first_suffix(nibble, label):
    return (pulse(nibble >> 3 & 1) + ' LD A,IXH\n LD L,A\n' + pulse(nibble >> 2 & 1) +
            ' LD H,pcm_high >> 8\n LD H,(HL)\n' + pulse(nibble >> 1 & 1) +
            ' LD L,E\n LD SP,HL\n' + pulse(nibble & 1) +
            f'{label}:\n JP (IY)\n DEFB 0\n')


def second_prefix(value, high):
    return (pulse(value >> 7 & 1) + ' POP HL\n' + pulse(value >> 6 & 1) + ' POP IY\n' +
            pulse(value >> 5 & 1) + ' POP DE\n' + pulse(value >> 4 & 1) +
            f' EX AF,AF\x27\n CCF\n JP C,{high}\n')


def low_suffix(nibble):
    return (pulse(nibble >> 3 & 1) + ' EX AF,AF\x27\n EXX\n LD A,(DE)\n EXX\n' +
            pulse(nibble >> 2 & 1) + ' AND 15\n RLCA\n RLCA\n' +
            pulse(nibble >> 1 & 1) + ' JP $+3\n NOP\n NOP\n NOP\n' +
            pulse(nibble & 1) + ' JP (HL)\n')


def high_suffix(nibble):
    return (pulse(nibble >> 3 & 1) + ' EX AF,AF\x27\n EXX\n LD A,(DE)\n EXX\n' +
            pulse(nibble >> 2 & 1) + ' AND 240\n RRCA\n RRCA\n' +
            pulse(nibble >> 1 & 1) + ' EXX\n INC E\n' +
            f' JP Z,page_tail_{nibble & 1}\n EXX\n' + pulse(nibble & 1) + ' JP (HL)\n')


def assembly(firsts, seconds, variant):
    shared_first = variant in ('first-and-high', 'both-halves')
    shared_low = variant == 'both-halves'
    shared_high = variant != 'baseline'
    text = '''; Standalone literal-pattern compression proof. No decoder/table or source change.
; Main BC=00FE/10FE,D=16,E=feedback*6,HL dispatch,IX predictor,IY SECOND.
; Alternate HL=IMA row,BC delta,DE compressed cursor; AF' retains phase/code.
; SP is the live table pointer; no CALL/RET or ordinary stack use is permitted.
; All extra transfers below are fixed JP10, independent of pattern and phase.
 ORG 0x8000
pcm_high: EQU 0x5E00
'''
    # Preserve the ordinary page and non-UI descriptor tails instruction for
    # instruction. Scorpion patches the JP below to three NOPs, as the player.
    for bit in (0, 1):
        text += f'page_tail_{bit}:\n INC D\n JP Z,bank_handoff_{bit}\n EXX\n'
        text += pulse(bit) + ' JP (HL)\n'
        text += f'bank_handoff_{bit}:\n EX AF,AF\x27\n EXX\n LD B,{bit * 16}\n EXX\n JP bank_jump\n'
    text += '''bank_jump: JP stream_bank_tail
stream_bank_tail:
 LD (stream_tail_hl),HL
 LD HL,(stream_next_record)
 LD A,(HL)
 OR A
 JP Z,exhausted
 LD (stream_paging),A
 INC HL
 LD D,(HL)
 LD E,0
 INC HL
 LD A,(HL)
 INC HL
 LD (stream_next_record),HL
 LD HL,(stream_tail_hl)
stream_high_switch: JP stream_high_done
 LD BC,0x1FFD
 OUT (C),A
stream_high_done:
 LD BC,0x7FFD
 LD A,(stream_paging)
stream_page_event: OUT (C),A
 EXX
 SCF
 EX AF,AF'
 OUT (C),B
 JP (HL)
exhausted: HALT
hardware_delay: NOP
 NOP
 NOP
 NOP
 JP (IY)
stream_tail_hl: DEFW 0
stream_next_record: DEFW descriptor
stream_paging: DEFB 0
descriptor: DEFB 25,192,0,0
 DS 0x8340-$
first_begin:
; FIRST prefixes decode the next IMA nibble. A shared suffix retains the
; exact same predictor lookup work; its extra JP preserves all registers/F.
'''
    for value in firsts:
        text += f'first_{value}:\n' + first_prefix(value)
        if shared_first:
            text += f' JP first_suffix_{value & 15}\n'
        else:
            text += first_suffix(value & 15, f'first_dispatch_{value}')
    if shared_first:
        for nibble in range(16):
            text += f'first_suffix_{nibble}:\n' + first_suffix(nibble, f'first_dispatch_{nibble}')
    text += '''first_end:
second_begin:
; SECOND's existing constant-time phase JP can directly reach one of sixteen
; shared high suffixes. This redirection costs no additional instruction.
'''
    for value in seconds:
        high = f'high_suffix_{value & 15}' if shared_high else f'high_{value}'
        if shared_low:
            high = f'high_transfer_{value & 15}'
        text += f'second_{value}:\n' + second_prefix(value, high)
        if shared_low:
            text += f' JP low_suffix_{value & 15}\n'
        else:
            text += low_suffix(value & 15)
        if not shared_high:
            text += f'high_{value}:\n' + high_suffix(value & 15)
            text += f' DS second_{value}+64-$\n'
    if shared_high:
        for nibble in range(16):
            if shared_low:
                # Both phase branches must pay the same additional JP10.
                text += f'high_transfer_{nibble}: JP high_suffix_{nibble}\n'
                text += f'low_suffix_{nibble}:\n' + low_suffix(nibble)
            text += f'high_suffix_{nibble}:\n' + high_suffix(nibble)
    return text + 'second_end:\ncomplete: NOP\n'


def assemble(output, firsts, seconds, variant):
    folder = output / variant
    folder.mkdir(parents=True, exist_ok=True)
    source = assembly(firsts, seconds, variant)
    (folder / 'kernel.asm').write_text(source, encoding='utf-8', newline='\n')
    result = subprocess.run([sys.executable, '-m', 'pyz80.pyz80', '--obj=kernel.bin',
                             '--lstfile=kernel.lst', '-s', '.*', 'kernel.asm'],
                            cwd=folder, capture_output=True, text=True)
    (folder / 'assembler.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    labels = next(ast.literal_eval(line) for line in result.stdout.splitlines() if line.startswith('{'))
    blob = (folder / 'kernel.bin').read_bytes()
    save(folder / 'addresses.json', dict(first={value: labels[f'first_{value}'] for value in firsts},
                                       second={value: labels[f'second_{value}'] for value in seconds},
                                       labels=labels))
    return blob, labels


def snapshot(machine):
    return {name: getattr(machine, name) for name in ('af', 'bc', 'de', 'hl', 'ix', 'iy', 'sp',
                                                     'alt_af', 'alt_bc', 'alt_de', 'alt_hl')}


def make_machine(profile, blob, labels):
    machine = MemoryMachine(profile, b'', labels)
    machine.banks[2][:len(blob)] = blob
    machine.low = 24
    machine.selected = 0
    if profile == 'scorpion':
        for offset in range(3):
            machine.write(labels['stream_high_switch'] + offset, 0)
    # The complete256-entry PCM selector is deliberately constant in this
    # literal-body proof. Full16-bit selection belongs to the separate selector.
    for high in range(256):
        machine.write(0x5E00 + high, 0x70)
    for nibble in range(16):
        at = 0x7200 + 4 * nibble
        for offset, value in enumerate((17, 0, 0, 0x72)):
            machine.write(at + offset, value)
    return machine


def run_packet(machine, labels, first, second, phase, tail, pacing, shared_first):
    m = machine.m
    # The low nibble fetch does not advance the source cursor. The high nibble
    # fetch additionally exercises ordinary, page and bank descriptor tails.
    cursor = {'ordinary': 0xC000, 'page': 0xC0FF, 'bank': 0xFFFF}[tail]
    descriptor = labels['descriptor']
    for offset, value in enumerate((25, 192, 0, 0)):
        machine.write(descriptor + offset, value)
    machine.write(labels['stream_next_record'], descriptor & 255)
    machine.write(labels['stream_next_record'] + 1, descriptor >> 8)
    machine.write(labels['stream_tail_hl'], 0)
    machine.write(labels['stream_tail_hl'] + 1, 0)
    machine.write(labels['stream_paging'], 0)
    machine.low = 24
    machine.high = machine.eff = 0
    machine.selected = 0
    for bank_id, bank in enumerate(machine.banks):
        if bank_id not in (2, 5):
            bank[0] = 0xA7
            bank[255] = 0xA7
            bank[-1] = 0xA7
    # The next six-byte record and current IMA row contain the same values
    # for both layouts; no new code or table address leaks into live registers.
    for offset, value in enumerate((0x40, 0, 0x77, 0x77, 0x30, 16)):
        machine.write(0x7030 + offset, value)
    for name, value in dict(af=0x0C00, bc=0x00FE, de=0x1030, hl=0xFFFF,
                            ix=0x9000, iy=second, sp=0x7777,
                            alt_af=0xA500 | phase, alt_bc=0x3456,
                            alt_de=cursor, alt_hl=0x7200).items():
        setattr(m, name, value)
    m.iff1 = False
    m.iff2 = bool(phase & 1)
    m.r = 127 if phase & 1 else 0
    # Existing Pentagon pacing is a fixed26 T. For the maximally shared
    # prototype INC HL6 can replace those26 T after the two added JP10.
    # HL is dead after LD SP,HL and is overwritten by SECOND's first POP.
    dispatch = labels[f'first_dispatch_{first & 15 if shared_first else first}']
    original = bytes(machine.read(dispatch + i) for i in range(3))
    if pacing == 'legacy26':
        target = labels['hardware_delay']
        replacement = bytes((0xC3, target & 255, target >> 8))
    elif pacing == 'direct6':
        replacement = bytes.fromhex('23FDE9')
    elif pacing == 'direct16':
        # Two harmless INC HL6 plus NOP4 cost16 T after the one added JP10.
        # This longer alternative is not byte-patched into the three-byte slot.
        raise ValueError('direct16 is not implemented in the three-byte dispatch slot')
    else:
        replacement = bytes.fromhex('FDE900')
    for index, value in enumerate(replacement):
        machine.write(dispatch + index, value)
    budget = 100000
    events = []
    def output(port, value):
        if port & 255 == 254:
            events.append((port, value, budget - m.ticks_to_stop))
        machine.output(port, value)
    m.set_output_callback(output)
    machine.page_writes.clear()
    before = [bytes(bank) for bank in machine.banks]
    m.pc = labels[f'first_{first}']
    m.ticks_to_stop = budget
    while m.pc != 0x40:
        result = m.run()
        if result & m._TICKS_LIMIT_HIT:
            raise AssertionError(('timeout', hex(m.pc), first, second, phase, tail))
    elapsed = budget - m.ticks_to_stop
    # Only the descriptor cursors are mutable during this standalone hot path.
    allowed = {labels['stream_next_record'], labels['stream_next_record'] + 1,
               labels['stream_tail_hl'], labels['stream_tail_hl'] + 1, labels['stream_paging']}
    for bank_id, bank in enumerate(machine.banks):
        for offset in np.flatnonzero(np.frombuffer(before[bank_id], 'u1') != np.frombuffer(bank, 'u1')):
            assert bank_id == 2 and 0x8000 + offset in allowed, ('memory guard', bank_id, int(offset))
    for index, value in enumerate(original):
        machine.write(dispatch + index, value)
    assert len(events) == 16, ('source pulse count', len(events))
    return dict(elapsed=elapsed, events=events, registers=snapshot(m), iff1=m.iff1, iff2=m.iff2,
                selected=machine.selected, page_writes=machine.page_writes.copy())


def verify(output, firsts, seconds, assembled):
    pairs = [(value, seconds[i % len(seconds)]) for i, value in enumerate(firsts)]
    pairs += [(firsts[i % len(firsts)], value) for i, value in enumerate(seconds)]
    reports = {}
    for variant, (blob, labels) in assembled.items():
        if variant == 'baseline':
            continue
        shared_first = variant in ('first-and-high', 'both-halves')
        ordinary_delta = 10 * shared_first + 10 * (variant == 'both-halves')
        profile_reports = {}
        for profile in PROFILES:
            original_blob, original_labels = assembled['baseline']
            old = make_machine(profile, original_blob, original_labels)
            new = make_machine(profile, blob, labels)
            baseline_pacing = 'legacy26' if profile.startswith('pentagon') else 'none'
            # Zero-extra sharing preserves the original clone pacing exactly.
            # The maximal variant can exchange26 T for6 T, leaving449 T total.
            pacing = ('direct6' if variant == 'both-halves' else 'legacy26') if profile.startswith('pentagon') else 'none'
            cases = 0
            maxima = {}
            for first, second in pairs:
                for phase in (0, 1):
                    for tail in ('ordinary', 'page', 'bank'):
                        before = run_packet(old, original_labels, first, original_labels[f'second_{second}'], phase,
                                            tail, baseline_pacing, False)
                        after = run_packet(new, labels, first, labels[f'second_{second}'], phase, tail, pacing, shared_first)
                        assert after['registers'] == before['registers'], (variant, profile, first, second, phase, tail, 'registers', before, after)
                        assert (after['iff1'], after['iff2'], after['selected'], after['page_writes']) == (before['iff1'], before['iff2'], before['selected'], before['page_writes'])
                        assert [row[:2] for row in after['events']] == [row[:2] for row in before['events']]
                        expected = []
                        for index, (port, value, time) in enumerate(before['events']):
                            delta = 10 if shared_first and index >= 4 else 0
                            if variant == 'both-halves' and index >= 12:
                                delta += 10
                            if variant == 'both-halves' and profile.startswith('pentagon') and index >= 8:
                                delta -= 20
                            expected.append((port, value, time + delta))
                        assert after['events'] == expected, (variant, profile, first, second, phase, tail, 'timing', before['events'], after['events'])
                        wanted_delta = 0 if variant == 'both-halves' and profile.startswith('pentagon') else ordinary_delta
                        assert after['elapsed'] == before['elapsed'] + wanted_delta
                        maxima[tail] = max(maxima.get(tail, 0), after['elapsed'])
                        cases += 1
            profile_reports[profile] = dict(complete=True, native_before_after_cases=cases,
                all_first_patterns=len(firsts), all_second_patterns=len(seconds),
                both_source_nibble_phases=True, ordinary_page_and_bank_tails=True,
                all16_source_pulse_ports_and_values_identical=True, complete_live_registers_flags_and_IFF_exact=True,
                physical_bank_selection_and_prefetch_state_identical=True, memory_guards_passed=True,
                deterministic_timestamp_deltas_exact=True, maximum_packet_native_tstates=maxima,
                clone_pacing=pacing)
        reports[variant] = profile_reports
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'evidence/sdm16-patterns')
    parser.add_argument('--catalogue', type=Path, default=HERE / 'evidence/sdm16-architecture/model-b-all-pcm16-cells.npz')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = np.load(args.catalogue)
    words, nxt = archive['words'], archive['successors']
    reached = {16}
    while True:
        after = reached | set(map(int, nxt[:, sorted(reached)].ravel()))
        if after == reached:
            break
        reached = after
    active = words[:, sorted(reached)]
    firsts = sorted(map(int, np.unique(active >> 8)))
    seconds = sorted(map(int, np.unique(active & 255)))
    assert len(firsts) == 138 and len(seconds) == 124 and len(reached) == 18
    assembled = {variant: assemble(output, firsts, seconds, variant) for variant in
                 ('baseline', 'high-only', 'first-and-high', 'both-halves')}
    sizes = {variant: dict(first_code_bytes=labels['first_end'] - labels['first_begin'],
                          second_code_bytes=labels['second_end'] - labels['second_begin'],
                          pattern_code_bytes=labels['second_end'] - labels['first_begin'])
             for variant, (_, labels) in assembled.items()}
    save(output / 'size-partial.json', dict(complete=False, sizes=sizes))
    verification = verify(output, firsts, seconds, assembled)
    report = dict(complete=True, date='2026-10-19', all_input_bins=65536, reachable_feedback_states=sorted(reached),
        first_patterns=len(firsts), second_patterns=len(seconds), sizes=sizes,
        catalogue_sha256=hashlib.sha256(args.catalogue.read_bytes()).hexdigest(), verification=verification,
        source_modulation_or_encoder_changed=False, current_player_changed=False,
        old_ordinary_tstates=dict(spectrum128=423, scorpion=423, pentagon=449),
        high_only_ordinary_tstates=dict(spectrum128=423, scorpion=423, pentagon=449),
        first_and_high_ordinary_tstates=dict(spectrum128=433, scorpion=433, pentagon=459),
        both_halves_ordinary_tstates=dict(spectrum128=443, scorpion=443, pentagon=449),
        timing_table=dict(JP_nn=10, JP_HL=4, JP_IY=8, INC_HL=6,
                          existing_Pentagon_padding=26, both_halves_Pentagon_padding=6),
        source_8khz_preservation='The zero-added-cycle high-only variant preserves every native source OUT timestamp. Other prototypes alter intra-packet holds and require their own table model and complete actual-clock/quality checks.',
        page_extra_tstates=14, bank_extra_tstates=dict(spectrum128=243, scorpion=267, pentagon=243),
        scope='Exhaustive literal FIRST/SECOND coverage, both source phases and ordinary/page/bank tails on four coherent-bank native profiles. No integrated16-bit selector, cold disk, ULA, UI, Fuse or audio-quality acceptance proof.',
        main_release_modified=False, physical_hardware_tested=False, release_accepted=False)
    save(output / 'report.json', report)
    (output / 'generator.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(), mtime=0))
    artifacts = []
    for path in sorted(output.rglob('*')):
        if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts:
            artifacts.append(dict(path=path.relative_to(output).as_posix(), bytes=path.stat().st_size,
                                  sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    save(output / 'manifest.json', dict(artifacts=artifacts, files=len(artifacts)))
    print(json.dumps(dict(complete=True, sizes=sizes, native_cases=sum(
        row['native_before_after_cases'] for profiles in verification.values() for row in profiles.values()))))


if __name__ == '__main__':
    main()
