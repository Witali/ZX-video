"""Assemble and execute the specialized raw LZMA1 decoder on a native Z80 CPU.

Dependencies: pyz80==1.3.0, z80==1.2.0. No ROM/disk/ULA timing is included.
Use the archived 21-block fixture; never recompress it for the comparison.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import lzma
from pathlib import Path
import pickle
import random
import struct
import subprocess
import sys

from z80 import Z80Machine

ROOT = Path(__file__).resolve().parents[1]
TOOLKIT = ROOT / "toolkit"
FILTERS = [dict(id=lzma.FILTER_LZMA1, preset=9 | lzma.PRESET_EXTREME,
                dict_size=16384, lc=0, lp=0, pb=2)]
STOP, INPUT, OUTPUT, STACK = 0x100, 0x4000, 0xC000, 0xBFF0


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assemble(fast: bool, folder: Path) -> tuple[bytes, dict]:
    folder.mkdir(parents=True, exist_ok=True)
    base = folder / ("fast" if fast else "loop")
    subprocess.run([sys.executable, "-m", "pyz80.pyz80", "-D", f"FAST_MUL={int(fast)}",
                    f"--obj={base}.bin", f"--exportfile={base}.symbols",
                    f"--lstfile={base}.lst", str(TOOLKIT / "lzma_z80.asm")],
                   check=True, capture_output=True, text=True)
    # Only load the local symbol file just produced by our own assembler.
    symbols = pickle.loads(base.with_suffix(".symbols").read_bytes())
    return base.with_suffix(".bin").read_bytes(), symbols


def word(m: Z80Machine, addr: int) -> int:
    return m.memory[addr] | (m.memory[addr + 1] << 8)


def put_word(m: Z80Machine, addr: int, value: int) -> None:
    m.memory[addr:addr + 2] = value.to_bytes(2, "little")


def instruction_tstates(m: Z80Machine) -> int:
    """Independent timing table for the emitted instruction subset (Zilog UM0080)."""
    op = m.memory[m.pc]
    z, c = bool(m.f & 64), bool(m.f & 1)
    conditions = {0: not z, 1: z, 2: not c, 3: c}
    if op == 0xCB:
        sub = m.memory[m.pc + 1]
        return (12 if 0x40 <= sub < 0x80 else 15) if sub & 7 == 6 else 8
    if op == 0xED:
        sub = m.memory[m.pc + 1]
        if sub == 0xB0:
            return 16 if m.bc == 1 else 21
        if sub & 0xCF in (0x43, 0x4B):
            return 20
        if sub & 0xCF in (0x42, 0x4A):
            return 15
        raise AssertionError(f"unaccounted ED {sub:02x}")
    if 0x40 <= op <= 0x7F and op != 0x76:
        return 7 if (op & 7 == 6 or (op >> 3) & 7 == 6) else 4
    if 0x80 <= op <= 0xBF:
        return 7 if op & 7 == 6 else 4
    if op in (0x01, 0x11, 0x21, 0x31):
        return 10
    if op < 0x40 and op & 7 == 6:
        return 10 if op == 0x36 else 7
    if op in (0x22, 0x2A):
        return 16
    if op in (0x32, 0x3A):
        return 13
    if op in (0x02, 0x0A, 0x12, 0x1A):
        return 7
    if op in (0x03, 0x13, 0x23, 0x33, 0x0B, 0x1B, 0x2B, 0x3B):
        return 6
    if op < 0x40 and op & 7 in (4, 5):
        return 11 if op in (0x34, 0x35) else 4
    if op in (0x09, 0x19, 0x29, 0x39):
        return 11
    if op in (0x00, 0x07, 0x08, 0x0F, 0x17, 0x1F, 0x2F, 0x37, 0x3F, 0xD9, 0xEB):
        return 4
    if op in (0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE):
        return 7
    if op in (0xC5, 0xD5, 0xE5, 0xF5):
        return 11
    if op in (0xC1, 0xD1, 0xE1, 0xF1):
        return 10
    if op in (0xC3, 0xC2, 0xCA, 0xD2, 0xDA):
        return 10
    if op == 0xC9:
        return 10
    if op in (0xC0, 0xC8, 0xD0, 0xD8):
        return 11 if conditions[(op >> 3) & 3] else 5
    if op == 0x18:
        return 12
    if op in (0x20, 0x28, 0x30, 0x38):
        return 12 if conditions[(op >> 3) & 3] else 7
    if op == 0x10:
        return 13 if m.b != 1 else 8
    if op == 0xCD:
        return 17
    raise AssertionError(f"unaccounted opcode {op:02x} at {m.pc:04x}")


def execute(binary: bytes, s: dict, packed: bytes, size: int, *, trace=False,
            audit=False, interrupts=False, input_address=INPUT, output_address=OUTPUT) -> dict:
    input_base, output_base = input_address, output_address
    assert len(packed) <= 0x4000 and 0 <= size <= 15873
    m = Z80Machine()
    m.memory[:] = bytes([0xA5]) * 65536
    m.set_memory_block(s["lzma_decode"], binary)
    m.set_memory_block(input_base, packed)
    put_word(m, s["input_end"], input_base + len(packed))
    put_word(m, STACK - 2, STOP)
    m.pc, m.sp, m.hl, m.de, m.bc = s["lzma_decode"], STACK - 2, input_base, output_base, size
    m.ix, m.iy, m.alt_af = 0x1234, 0xABCD, 0x9876
    if interrupts:
        # IM1 / EI / NOP / JP decoder. Test a register-preserving ISR only;
        # the emulator frame event is 100000 T, not the Spectrum 50-Hz clock.
        m.set_memory_block(0x200, b"\xed\x56\xfb\x00\xc3\x00\x80")
        irq = bytes.fromhex("f5 c5 d5 e5 08 d9 f5 c5 d5 e5 21 00 03 34 e1 d1 c1 f1 d9 08 e1 d1 c1 f1 fb ed 4d")
        m.set_memory_block(0x38, irq)
        m.memory[0x300] = 0
        m.pc = 0x200
    m.set_breakpoint(STOP)
    m.ticks_to_stop = budget = 500_000_000
    high_water, min_sp = output_base, STACK - 2
    counts: dict[str, int] = {}
    prob_popcount = 0
    watched = {s[k]: k for k in ["multiply_bound", "literal", "literal_matched",
        "short_rep", "rep_one", "rep_two_three", "rep_three", "long_rep",
        "new_match", "distance_direct", "end_marker", "copy_match"]} if trace else {}

    # Guard all writes; permit model/state natively, track output and stack.
    m.mark_addrs(0, 65536, m.WRITE_MARK | m.READ_MARK)
    for start, end in [(s["lzma_decode"], s["code_end"]),
                       (s["probs"], s["probs_end"]),
                       (s["entry_sp"], s["state_end"]),
                       (STACK - 256, STACK), (input_base, input_base + len(packed))]:
        m.unmark_addrs(start, end - start, m.READ_MARK)
    for start, end in [(s["probs"], s["probs_end"]),
                       (s["entry_sp"], s["state_end"])]:
        m.unmark_addrs(start, end - start, m.WRITE_MARK)
    for addr in watched:
        m.mark_addr(addr, m.READ_MARK)
    if interrupts:
        m.unmark_addrs(0x38, len(irq), m.READ_MARK)
        m.unmark_addrs(0x200, 7, m.READ_MARK)
        m.unmark_addrs(0x300, 1, m.READ_MARK | m.WRITE_MARK)

    def read(addr: int) -> int:
        nonlocal prob_popcount
        if addr in watched:
            name = watched[addr]
            counts[name] = counts.get(name, 0) + 1
            if name == "multiply_bound":
                prob_popcount += m.bc.bit_count()
        elif not output_base <= addr < high_water:
            raise AssertionError(f"invalid read {addr:04x}, PC={m.pc:04x}")
        return m.memory[addr]

    def write(addr: int, value: int) -> None:
        nonlocal high_water, min_sp
        if output_base <= addr < output_base + min(size, 15872):
            assert addr <= high_water, (addr, high_water)
            high_water = max(high_water, addr + 1)
        elif STACK - 256 <= addr < STACK:
            min_sp = min(min_sp, addr)
        else:
            raise AssertionError(f"invalid write {addr:04x}, PC={m.pc:04x}")
        m.memory[addr] = value

    m.set_read_callback(read)
    m.set_write_callback(write)
    audited_tstates, instructions, irq_count = 0, 0, 0
    while m.pc != STOP:
        if audit:
            expected_t = instruction_tstates(m)
            before = m.frame_tick
            m.ticks_to_stop = 1
        events = m.run()
        if audit:
            actual_t = (m.frame_tick - before) % 100000
            assert actual_t == expected_t, (m.pc, actual_t, expected_t)
            audited_tstates += actual_t
            instructions += 1
            assert audited_tstates < budget
        elif events & m._TICKS_LIMIT_HIT:
            raise AssertionError(f"decoder timed out, PC={m.pc:04x}")
        if interrupts and m.pc != STOP and events & m._END_OF_FRAME:
            m.on_handle_active_int()
            assert m.pc == 0x38
            irq_count += 1
    assert (m.sp, m.ix, m.iy, m.alt_af) == (STACK, 0x1234, 0xABCD, 0x9876)
    assert (m.a, m.f & 1) in ((0, 0), (1, 1))
    if interrupts:
        assert m.memory[0x300] == irq_count % 256 and m.iff1
    return dict(ok=m.a == 0 and not (m.f & 1),
                tstates=audited_tstates if audit else budget - m.ticks_to_stop,
                decoded=bytes(m.memory[output_base:high_water]),
                consumed=word(m, s["input_ptr"]) - input_base,
                produced=high_water - output_base, stack_bytes=STACK - min_sp,
                counts=counts, probability_popcount=prob_popcount,
                audited_instructions=instructions, injected_interrupts=irq_count)


def arithmetic_checks(binary: bytes, s: dict, fast: bool) -> dict:
    """Every 11-bit probability, boundary/random 21-bit operands; exact cycle formula."""
    m = Z80Machine()
    m.set_memory_block(s["lzma_decode"], binary)
    m.set_breakpoint(STOP)
    rng = random.Random(1729)
    count = 0
    for prob in range(1, 2048):
        for q in (0, 1, 0x1FFFFF, rng.randrange(0x200000)):
            m.pc, m.sp = s["multiply_bound"], STACK - 2
            put_word(m, STACK - 2, STOP)
            m.de, m.alt_de, m.bc = q & 65535, q >> 16, prob
            m.ticks_to_stop = 10000
            while m.pc != STOP:
                m.run()
            assert (m.alt_hl << 16) | m.hl == q * prob
            expected = (598 if fast else 1060) + 29 * prob.bit_count()
            assert 10000 - m.ticks_to_stop == expected
            count += 1
    return dict(cases=count, formula=("598" if fast else "1060") + " + 29*popcount(prob)",
                includes="Entry through RET; caller CALL excluded")


def fixture() -> list[tuple[bytes, bytes]]:
    raw = gzip.decompress((TOOLKIT / "row_lzsa_evidence/video.raw.gz").read_bytes())
    assert sha(raw) == "5adefa050587757e9b203d3f8b9d4724e06f2fc3ddcbc8549fc87e7e0c2a01d6"
    stream = gzip.decompress((TOOLKIT / "modern_codec_evidence/lzma1_extreme_lc0.stream.gz").read_bytes())
    assert sha(stream) == "f9566ee18bf270e58a80c6aeb241652a12f5ff55a00fc78ccc1a0e821f1adb9e"
    assert len(stream) == 133084
    rows, pos, out = [], 0, 0
    while pos < len(stream):
        unpacked, packed = struct.unpack_from("<HH", stream, pos)
        pos += 4
        data = stream[pos:pos + packed]
        expected = raw[out:out + unpacked]
        assert lzma.decompress(data, format=lzma.FORMAT_RAW, filters=FILTERS) == expected
        rows.append((expected, data))
        pos += packed
        out += unpacked
    assert pos == len(stream) and out == len(raw) and len(rows) == 21
    return rows


def run_case(binary, symbols, raw, packed=None, **kwargs):
    if packed is None:
        packed = lzma.compress(raw, format=lzma.FORMAT_RAW, filters=FILTERS)
    result = execute(binary, symbols, packed, len(raw), **kwargs)
    assert result["ok"], {k: v for k, v in result.items() if k != "decoded"}
    assert result.pop("decoded") == raw, "native output mismatch"
    assert result["consumed"] == len(packed)
    return dict(decoded_bytes=len(raw), packed_bytes=len(packed),
                raw_sha256=sha(raw), packed_sha256=sha(packed), **result)


def invalid_checks(binary, symbols) -> dict:
    raw = b"abcabcabcXabcabcabcY" * 7
    packed = lzma.compress(raw, format=lzma.FORMAT_RAW, filters=FILTERS)
    cases = [(f"prefix_{i}", packed[:i], len(raw)) for i in range(len(packed))]
    cases += [("wrong_initial_byte", b"\x01" + packed[1:], len(raw)),
              ("invalid_initial_code", b"\0" + b"\xff" * 4, 0),
              ("extra_input", packed + b"\0", len(raw)),
              ("output_one_short", packed, len(raw) - 1),
              ("output_one_long", packed, len(raw) + 1),
              ("output_over_limit", packed, 15873)]
    for name, data, size in cases:
        result = execute(binary, symbols, data, size)
        assert not result["ok"], name
    # Bit flips are not all invalid: valid altered streams must match liblzma.
    rng = random.Random(773)
    rejected, accepted = 0, 0
    for _ in range(64):
        damaged = bytearray(packed)
        damaged[rng.randrange(len(damaged))] ^= 1 << rng.randrange(8)
        try:
            oracle = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=FILTERS)
            expected = oracle.decompress(damaged, max_length=15873)
            valid = oracle.eof and not oracle.unused_data and len(expected) == len(raw)
        except lzma.LZMAError:
            valid = False
        result = execute(binary, symbols, damaged, len(raw))
        assert result["ok"] == valid
        if valid:
            assert result["decoded"] == expected
            accepted += 1
        else:
            rejected += 1
    return dict(required_rejections=len(cases), bit_flips=64,
                bit_flips_rejected=rejected, bit_flips_valid_exact=accepted)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--output", type=Path, default=TOOLKIT / "lzma_z80_benchmark.json")
    args = p.parse_args()
    folder = ROOT / ".tmp/lzma-z80-build"
    variants = {name: assemble(fast, folder) for name, fast in [("loop", False), ("fast", True)]}
    rng = random.Random(0x1A2B)
    cases = [("empty", b""), ("one", b"A"), ("short_repeat", b"A" * 31),
             ("long_overlap", b"A" * 15872), ("alphabet", bytes(range(256)) * 40),
             ("noise", rng.randbytes(15872)),
             ("matched_literals", (b"abcabcabcXabcabcabcY" * 500))]
    cases += [(f"length_{n}", b"abcd" + b"A" * n + b"abcd")
              for n in (2, 3, 8, 9, 16, 17, 272, 273, 274)]
    far_prefix = rng.randbytes(32)
    cases.append(("distance_15840", far_prefix + rng.randbytes(15808) + far_prefix))
    results = {}
    for name, (binary, symbols) in variants.items():
        arithmetic = arithmetic_checks(binary, symbols, name == "fast")
        invalid = invalid_checks(binary, symbols)
        rows = []
        for case, raw in cases:
            r = run_case(binary, symbols, raw, trace=True)
            rows.append(dict(case=case, **r))
            print(f"{name} {case}: {r['tstates']} T", flush=True)
        results[name] = dict(code_bytes=len(binary), binary_sha256=sha(binary),
                             probability_bytes=symbols["probs_end"]-symbols["probs"],
                             state_bytes=symbols["state_end"]-symbols["entry_sp"],
                             arithmetic=arithmetic, invalid=invalid, edges=rows, blocks=[])
        audit_raw = bytes(range(256)) + b"abcabcabcXabcabcabcY" * 30
        results[name]["instruction_audit"] = run_case(binary, symbols, audit_raw, audit=True)
        ordinary = run_case(binary, symbols, audit_raw)
        assert results[name]["instruction_audit"]["tstates"] == ordinary["tstates"]
        results[name]["interrupt_preservation"] = run_case(binary, symbols, audit_raw, interrupts=True)
        results[name]["unaligned_buffers"] = run_case(binary, symbols, audit_raw,
            input_address=INPUT + 17, output_address=OUTPUT + 93)
    if not args.smoke:
        for i, (raw, packed) in enumerate(fixture()):
            for name, (binary, symbols) in variants.items():
                r = run_case(binary, symbols, raw, packed, trace=True)
                results[name]["blocks"].append(dict(block=i, **r))
            print(f"block {i}: exact", flush=True)
    for group in ("edges", "blocks"):
        for baseline, fast in zip(results["loop"][group], results["fast"][group]):
            bits = baseline["counts"]["multiply_bound"]
            assert baseline["counts"] == fast["counts"]
            assert baseline["tstates"] - fast["tstates"] == 462 * bits
    summary = {}
    for name, r in results.items():
        t = sum(row["tstates"] for row in r["blocks"])
        bits = sum(row["counts"]["multiply_bound"] for row in r["blocks"])
        ones = sum(row["probability_popcount"] for row in r["blocks"])
        summary[name] = dict(tstates=t, adaptive_bits=bits,
            multiply_tstates=bits * (598 if name == "fast" else 1060) + 29 * ones,
            maximum_stack_bytes=max(row["stack_bytes"] for row in r["edges"] + r["blocks"]))
    if not args.smoke:
        summary["saved_tstates"] = summary["loop"]["tstates"] - summary["fast"]["tstates"]
        summary["saved_percent"] = 100 * summary["saved_tstates"] / summary["loop"]["tstates"]
        summary["versus_lzsa2_decoder_ratio"] = summary["fast"]["tstates"] / 19844626
        summary["decoder_only_seconds_at_3_5MHz"] = summary["fast"]["tstates"] / 3500000
        summary["decoder_only_fps_ceiling_at_3_5MHz"] = 192 * 3500000 / summary["fast"]["tstates"]
        summary["raw_video_bytes"] = 323940
        summary["compressed_video_bytes_including_headers"] = 133084
        summary["video_sectors"] = 520
    report = dict(complete=not args.smoke, release=False,
                  source_sha256_lf=sha((TOOLKIT / "lzma_z80.asm").read_text().encode()),
                  harness_sha256_lf=sha(Path(__file__).read_text().encode()),
                  packages={n: importlib.metadata.version(n) for n in ("pyz80", "z80")},
                  scope="Standalone CPU; no contention, interrupts, paging, producer or disk latency.",
                  summary=summary, variants=results)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
