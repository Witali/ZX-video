"""Assemble and execute the bounded resident-PCM8, uniform8x56-T mechanism.

No released player or codec is changed. This is a bank-free CPU/precision
proof; file loading, DHA decoding, paging, EOF and UI are outside its scope.
"""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import time

from z80 import Z80Machine


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source() -> str:
    text = """; Resident unsignedPCM8, first-order accumulator, eight uniform56-T holds.
; MainHL=continuous modulo65536 accumulator, DE=PCM8<<8 (E remains zero),
; C=16 EAR mask. MainB/IX/IY/SP/I and alternateBC/HL are preserved.
; AlternateDE points to the NEXT source byte; current byte is already in D.
; AF' holds the prefetched byte only from gap1 to gap8; mainA/F are scratch.
; OUT(FE),A emits EAR0/16, with MIC/border zero. No RAM writes/CALL/PUSH.
; IRQs must be disabled. This bounded kernel has no EOF or bank handoff.
; Enter packet after priming D. All eight output holds are exactly56 T;
; source changes only after output8, for an exact448-T PCM sample period.
 ORG 0x8000
packet:
"""
    for slot in range(8):
        text += f"pulse_{slot}:\n ADD HL,DE\n SBC A,A\n AND C\n OUT (254),A\ngap_{slot}:\n"
        if slot == 0:
            text += """; Gap1: prefetch next target in AF',26 T including7-T dead load.
 EXX
 LD A,(DE)
 EX AF,AF'
 EXX
 LD A,0
"""
        elif slot == 6:
            text += """; Gap7: source advance,14 useful T plus12 T padding.
 EXX
 INC DE
 EXX
 NOP
 NOP
 NOP
"""
        elif slot == 7:
            text += """; Gap8: latch prefetched next target only after current output8.
; The10-T loop jump is included in the26-T gap, not added to the448-T clock.
 EX AF,AF'
 LD D,A
 NOP
 NOP
 JP packet
"""
        else:
            text += """;26 T free scheduling space; R-dependent flags/data are dead.
 LD A,R
 LD A,R
 NOP
 NOP
"""
    return text + "kernel_end:\n NOP\n"


def assemble(folder: Path):
    assembly = source()
    (folder / "kernel.asm").write_text(assembly, encoding="utf-8", newline="\n")
    result = subprocess.run([sys.executable, "-m", "pyz80.pyz80", "--obj=kernel.bin",
                             "--lstfile=kernel.lst", "-s", ".*", "kernel.asm"],
                            cwd=folder, capture_output=True, text=True)
    (folder / "assembler.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    labels = next(ast.literal_eval(line) for line in result.stdout.splitlines()
                  if line.startswith("{"))
    return (folder / "kernel.bin").read_bytes(), labels


class Runner:
    def __init__(self, blob, labels):
        self.m = Z80Machine()
        self.m.memory[0x8000:0x8000 + len(blob)] = blob
        self.labels = labels
        self.bits = []
        self.times = []
        self.samples = b""
        self.count = 0
        self.budget = 0
        self.expected_state = 0
        self.m.set_output_callback(self.output)

    def output(self, port, value):
        index, slot = divmod(len(self.bits), 8)
        assert port in (0x00FE, 0x10FE) and value in (0, 16)
        assert self.m.de == self.samples[index] << 8, (index, slot, self.m.de)
        assert self.m.iff1 == self.m.iff2 == 0
        total = self.expected_state + (self.samples[index] << 8)
        self.expected_state = total & 65535
        assert self.m.hl == self.expected_state
        assert value >> 4 == int(total >= 65536)
        self.bits.append(value >> 4)
        self.times.append(self.budget - self.m.ticks_to_stop)
        if len(self.bits) == self.count * 8:
            self.m.set_breakpoint(self.labels["packet"])

    def run(self, samples: bytes, count: int, accumulator: int):
        assert 1 <= count < len(samples) <= 16384
        m = self.m
        m.clear_breakpoint(self.labels["packet"])
        m.memory[0xC000:0xC000 + len(samples)] = samples
        for key, value in dict(hl=accumulator, de=samples[0] << 8, bc=0xA510,
                               ix=0x1234, iy=0x5678, sp=0xBEEF,
                               alt_de=0xC001, alt_hl=0x1357, alt_bc=0x2468,
                               alt_af=0x5A7F).items():
            setattr(m, key, value)
        m.i = 0x36
        m.r = 0xFF
        m.iff1 = m.iff2 = False
        self.bits, self.times = [], []
        self.samples, self.count = samples, count
        self.expected_state = accumulator
        self.budget = max(10000, count * 448 + 1000)
        before = bytes(m.memory)
        m.pc = self.labels["packet"]
        m.ticks_to_stop = self.budget
        while len(self.bits) < count * 8 or m.pc != self.labels["packet"]:
            event = m.run()
            assert not event & m._TICKS_LIMIT_HIT, "Native execution timeout"
        state, expected = accumulator, []
        for target in samples[:count]:
            for _ in range(8):
                total = state + (target << 8)
                expected.append(int(total >= 65536))
                state = total & 65535
        assert self.bits == expected
        assert all(b - a == 56 for a, b in zip(self.times, self.times[1:]))
        assert self.budget - m.ticks_to_stop == count * 448
        assert m.hl == state and m.de == samples[count] << 8
        assert m.alt_de == (0xC001 + count) & 65535
        assert m.bc == 0xA510 and m.ix == 0x1234 and m.iy == 0x5678 and m.sp == 0xBEEF
        assert m.alt_hl == 0x1357 and m.alt_bc == 0x2468 and m.i == 0x36
        assert bytes(m.memory) == before
        return dict(samples=count, outputs=len(self.bits), tstates=count * 448,
                    first_OUT_callback_tstate=self.times[0], final_accumulator=state,
                    bit_sha256=sha(bytes(self.bits)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    folder = args.output.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    blob, labels = assemble(folder)
    runner = Runner(blob, labels)
    # Exhaust all input/phase pairs. The low accumulator byte is a nonzero
    # canary: zero-low-byte PCM8 steps must leave it completely unchanged.
    for phase in range(256):
        for target in range(256):
            runner.run(bytes([target, 0xA5]), 1, (phase << 8) | 0x5A)
    # One complete resident-bank sequence exercises real source-page carries.
    # The final byte is prefetched. The last cursor increment wraps to zero,
    # but execution stops before any out-of-bank read; handoff remains absent.
    word = 0x12345678
    samples = bytearray(range(256))
    while len(samples) < 16384:
        word = (1664525 * word + 1013904223) & 0xFFFFFFFF
        samples.append(word >> 24)
    trajectory = runner.run(bytes(samples), 16383, 0)
    bit_data = bytes(runner.bits)
    time_data = struct.pack("<" + "I" * len(runner.times), *runner.times)
    (folder / "trajectory.pcm8").write_bytes(samples)
    (folder / "trajectory-bits.u8.gz").write_bytes(gzip.compress(bit_data, mtime=0))
    (folder / "trajectory-times.u32.gz").write_bytes(gzip.compress(time_data, mtime=0))
    # A common phase witnesses that one PCM8 LSB changes a real output bit.
    witnesses = []
    for target in (127, 128):
        result = runner.run(bytes([target, 0xA5]), 1, 128 << 8)
        result.update(target=target, bits=runner.bits)
        witnesses.append(result)
    assert witnesses[0]["bits"][0] == 0 and witnesses[1]["bits"][0] == 1
    report = dict(
        schema=1, date="2026-10-19", elapsed_seconds=time.monotonic() - started,
        mechanism="Resident unsigned PCM8, modulo16 first-order accumulator, eight equally timed pulses per sample; no DHA decoding during playback.",
        code_bytes=len(blob), code_sha256=sha(blob), labels=labels,
        native=dict(engine="z80.Z80Machine", all_input_phase_pairs=65536,
                    all_input_phase_outputs=65536 * 8, all_input_phase_tstates=65536 * 448,
                    trajectory=trajectory, total_outputs=65536 * 8 + 16383 * 8 + 16,
                    all_bits_and_accumulator_states_exact=True,
                    all_actual_OUT_holds_tstates=56, sample_period_tstates=448,
                    preserved_registers=["B", "C=16", "IX", "IY", "SP", "I", "alternateBC", "alternateHL"],
                    no_RAM_writes=True, no_CALL_PUSH=True, source_bytes_prefetched_and_held=True),
        arithmetic=dict(target="unsignedPCM8<<8", accumulator_bits=16,
                        effective_target_levels=256, signed_pcm16_mapping="(PCM8-128)*256",
                        order=1, physical_time_weighted=True,
                        physical_area_identity="56*sum(target/65536-bit)=56*(final_accumulator-initial_accumulator)/65536",
                        uniform_holds_necessary_for_this_identity=True),
        clocks=dict(pentagon_hz=3584000, sample_hz=8000, output_decisions_hz=64000,
                    scorpion_hz=3500000, unchanged_kernel_scorpion_sample_hz=7812.5,
                    other_clone_clock_support_proved=False),
        timing=dict(pulse=[dict(instruction="ADD HL,DE", tstates=11),
                            dict(instruction="SBC A,A", tstates=4),
                            dict(instruction="AND C", tstates=4),
                            dict(instruction="OUT (FE),A", tstates=11)],
                    pulse_total=30, every_gap_total=26,
                    gap_useful_tstates=[19, 0, 0, 0, 0, 0, 14, 18],
                    gap_free_tstates=[7, 26, 26, 26, 26, 26, 12, 8],
                    gap8_loop_jump_included=True,
                    first_OUT_callback_tstate=29,
                    CPU_output_instruction_completion_tstate=30,
                    previous_source_DHA_live_decode_tstates=800,
                    previous_source_clock_hz=20000000,
                    delta_versus_source_sample_period_tstates=-352,
                    existing_Spectrum_449_packet_tstates=449,
                    delta_versus_existing_Spectrum_449_packet_tstates=-1,
                    existing_Spectrum_448_experiment_packet_tstates=448,
                    delta_versus_existing_Spectrum_448_packet_tstates=0,
                    comparison_scope="Counts compare different mechanisms: decoding moved to loading. This is not a drop-in 352-T optimization of the old DHA live decoder."),
        one_LSB_witnesses=witnesses,
        artifacts=dict(pcm8_sha256=sha(bytes(samples)), trajectory_bits_sha256=sha(bit_data),
                       trajectory_times_sha256=sha(time_data)),
        not_proved=["DHA file decode or quality", "whole song RAM allocation", "bank handoff", "Spectrum 128/Scorpion clock adaptation", "loading or progress UI", "EOF and bootable TRD", "Fuse/physical playback", "second-order modulation"],
    )
    (folder / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("code_bytes", "elapsed_seconds", "native")}, indent=2))


if __name__ == "__main__":
    main()
