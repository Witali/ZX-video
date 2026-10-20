"""Prove a static, isolated 28-T PDM bank bridge in native Z80 execution.

This does not decode IMA, select a PDM word, load a disk, or model actual
Pentagon paging. The old source byte and decoder delta must already be dead.
The source-high/page word is patched before each bounded test; a real player
still needs descriptor lookahead, EOF, allocation and full playback proofs.
"""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from z80 import Z80Machine


HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def normal_pulse(bit):
    return " OUT (C),D\n" if bit else " DB 0xED,0x71\n"


def assembly():
    text = """; Bounded uncontended Z80 component, not a complete audio player.
; Main BC ends in FE, D=16, E and HL/IX/IY/SP retain their caller values.
; ALT HL is the live IMA row and must survive. ALT BC delta and ALT DE source
; are dead: both nibbles of the last source byte were already consumed/cached.
; AF' remains live and is untouched. Main A/F are scratch.
;
; The source-high/page immediate word is a host-patched static descriptor.
; ALT DE first holds D=page byte/E=next source high, then returns to the next
; source address (high<<8). No lookup SP, stack, RAM workspace or calls are used.
;
; Normal OUT(C),r takes12T, immediate OUT(FE),A takes11T. Count from one real
; speaker-write callback to the next; the NEXT output instruction belongs to
; each interval. The switch gap therefore has17T body plus11T immediate OUT.
; The page gap is pageOUT12 + EXX4 + normalOUT12 =28T, with no ULA port alias.
 ORG 0x8000
"""
    for word in range(128):
        bits = [(word >> (6-k)) & 1 for k in range(7)]
        text += f"bridge_{word}:\n" + normal_pulse(bits[0])
        text += f""" ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,{16*bits[1]}
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,{16*bits[2]}
 OUT (0xFE),A
descriptor_{word}:
 LD DE,0x18C0
 LD A,{16*bits[3]}
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
""" + normal_pulse(bits[4])
        text += """ ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
""" + normal_pulse(bits[5])
        text += """ EXX
 XOR A
 LD E,A
 EXX
""" + normal_pulse(bits[6])
        text += " JP complete\n"
    return text + "complete:\n NOP\n"


def build(folder):
    (folder / "bridge.asm").write_text(assembly(), encoding="utf-8", newline="\n")
    result = subprocess.run([sys.executable, "-m", "pyz80.pyz80", "--obj=bridge.bin",
                             "--lstfile=bridge.lst", "-s", ".*", "bridge.asm"],
                            cwd=folder, capture_output=True, text=True)
    (folder / "assembler.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    labels = next(ast.literal_eval(line) for line in result.stdout.splitlines()
                  if line.startswith("{"))
    blob = (folder / "bridge.bin").read_bytes()
    assert 0x8000 + len(blob) < 0xC000
    return blob, labels


class Runner:
    def __init__(self, blob, labels):
        self.m = Z80Machine()
        self.m.memory[0x8000:0x8000 + len(blob)] = blob
        self.labels = labels
        self.events = []
        self.budget = 1000
        self.m.set_output_callback(self.output)
        self.m.set_breakpoint(labels["complete"])
        self.cases = 0
        self.digest = hashlib.sha256()

    def output(self, port, value):
        self.events.append((self.budget - self.m.ticks_to_stop, port, value))

    def run(self, word, paging, source_high, main_bc=0x00FE):
        m = self.m
        at = self.labels[f"descriptor_{word}"] + 1
        m.memory[at:at+2] = bytes([source_high, paging])
        initial = dict(af=0xA5A5, bc=main_bc, de=0x1042, hl=0x9876,
                       ix=0x8125, iy=0x1234, sp=0x6006, alt_af=0x4201,
                       alt_bc=0xABCD, alt_de=0xFFFF, alt_hl=0x6400)
        for key, value in initial.items():
            setattr(m, key, value)
        m.i = 0x36
        m.iff1 = m.iff2 = False
        m.pc = self.labels[f"bridge_{word}"]
        m.ticks_to_stop = self.budget
        self.events = []
        # The emulator can return an intermediate frame event even though this
        # short component does not span a frame; its internal frame clock is
        # persistent across cases. Resume until the explicit code breakpoint.
        while m.pc != self.labels["complete"]:
            event = m.run()
            assert not event & m._TICKS_LIMIT_HIT
        elapsed = self.budget - m.ticks_to_stop
        assert elapsed == 190, (word, paging, source_high, elapsed)
        speakers = [(t, v) for t, p, v in self.events if p & 255 == 0xFE]
        pages = [(t, p, v) for t, p, v in self.events if p & 255 != 0xFE]
        expected = [16*((word >> (6-k)) & 1) for k in range(7)]
        assert speakers == list(zip((11, 39, 67, 95, 123, 151, 179), expected))
        assert pages == [(107, 0x7FFD, paging)]
        assert all(p in (main_bc, 0x00FE, 0x10FE, 0x7FFD)
                   for _, p, _ in self.events)
        for key in ("bc", "de", "hl", "ix", "iy", "sp", "alt_af", "alt_hl"):
            assert getattr(m, key) == initial[key], (key, getattr(m, key), initial[key])
        assert m.alt_bc == 0x7FFD and m.alt_de == source_high << 8
        assert m.a == 0 and m.f == 0x44 and m.i == 0x36
        assert m.iff1 == m.iff2 == 0
        self.cases += 1
        self.digest.update(bytes([word, paging, source_high, main_bc >> 8]))
        return dict(word=word, paging_byte=paging, next_source_high=source_high,
                    main_BC=main_bc, events=self.events, elapsed_tstates=elapsed)


def run(folder, quick=False):
    folder = folder.resolve()
    if folder.exists() and any(folder.iterdir()):
        raise ValueError("Use a fresh output directory; preserve previous attempts")
    folder.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    blob, labels = build(folder)
    runner = Runner(blob, labels)
    examples = []
    source_range = (0xC0, 0xDB, 0xFF) if quick else range(0xC0, 0x100)
    page_range = (0, 8, 24, 31, 63, 127, 255) if quick else range(256)
    for word in range(128):
        for paging in page_range:
            for source_high in source_range:
                result = runner.run(word, paging, source_high)
                if word in (0, 42, 85, 127) and paging == 24 and source_high == 0xC0:
                    examples.append(result)
        if word % 16 == 15:
            print(json.dumps(dict(progress_words=word+1, native_cases=runner.cases,
                                  elapsed_seconds=time.monotonic()-started)), flush=True)
    for word in range(128):
        runner.run(word, 0xFF, 0xDB, main_bc=0x10FE)
    # Only host-patched descriptor operands may differ from the assembled image.
    for word in range(128):
        at = labels[f"descriptor_{word}"] + 1
        runner.m.memory[at:at+2] = blob[at-0x8000:at-0x8000+2]
    expected_memory = bytearray(65536)
    expected_memory[0x8000:0x8000+len(blob)] = blob
    assert bytes(runner.m.memory) == bytes(expected_memory)
    source = Path(__file__).read_bytes()
    (folder / "producer.py.gz").write_bytes(gzip.compress(source, mtime=0))
    timing = dict(intervals_tstates=[28]*6, bridge_six_intervals_tstates=168,
        whole_fragment_including_first_OUT_and_exit_JP_tstates=190,
        actual_speaker_callback_tstates=[11, 39, 67, 95, 123, 151, 179],
        separate_page_callback_tstate=107,
        instruction_ledger=[
            dict(gap=0, body="EXX4; LD A,n7; INC BC6", body_tstates=17, next_speaker_OUT=11),
            dict(gap=1, body="LD BC,7FFD10; LD A,n7", body_tstates=17, next_speaker_OUT=11),
            dict(gap=2, body="LD DE,metadata10; LD A,n7", body_tstates=17, next_speaker_OUT=11),
            dict(gap=3, body="OUT(C),D12; EXX4", body_tstates=16, next_speaker_OUT=12),
            dict(gap=4, body="EXX4; LD D,E4; EXX4; NOP4", body_tstates=16, next_speaker_OUT=12),
            dict(gap=5, body="EXX4; XOR A4; LD E,A4; EXX4", body_tstates=16, next_speaker_OUT=12)],
        legacy_measured_bank_extra_tstates=243,
        legacy_cached_byte_bank_extra_tstates=229,
        additional_OUT_hold_tstates_in_this_component=0,
        comparison="The bridge redistributes real CPU work into six existing pulse slots;168T is its six-slot duration, not zero CPU cost. The243T/229T are previous whole-path bank additions; no integrated player speedup is proved.")
    report = dict(schema=1, date="2026-10-20", complete=True, quick_subset=quick,
        mechanism="Static isolated paging bridge with one ordinary source-high/page immediate word and arbitrary seven prescribed speaker bits",
        scope="Native uncontended CPU instruction and I/O sequence only; no hardware page-map callback, IMA decoder, table selector, complete banked player, disk or audio quality",
        elapsed_seconds=time.monotonic()-started, code_bytes=len(blob), code_sha256=sha(blob),
        producer_sha256=sha(source), labels=labels,
        native=dict(engine="z80.Z80Machine", cases=runner.cases,
            primary_cartesian_cases=128*len(page_range)*len(source_range),
            prescribed_pattern_words=128, pattern_bits=7,
            page_bytes=list(page_range), source_high_bytes=list(source_range),
            additional_main_BC_10FE_cases=128, speaker_writes=runner.cases*7,
            paging_writes=runner.cases, all_speaker_holds_tstates=28,
            no_ULA_paging_alias=True, page_port=0x7FFD,
            all_main_pairs_IX_IY_SP_altHL_altAF_I_preserved=True,
            alt_BC_after=0x7FFD, alt_DE_after="nextSourceHigh<<8", A_after=0, F_after=0x44,
            RAM_unchanged_after_removing_host_operand_patches=True,
            input_case_order_sha256=runner.digest.hexdigest()),
        timing=timing, examples=examples,
        preconditions=["Last packed source byte has been fetched and both required nibble values/decoder delta are no longer in ALT DE/BC",
                       "Main D=16, main C=FE, main A/F scratch; ALT HL and AF-prime remain live",
                       "Static metadata immediate is ready before this fragment; metadata lookup/pointer and EOF costs are outside the proof"],
        not_proved=["Complete 16-output sample or448T source period", "Ordinary/page/bank integration with full16 predictor and table lookup",
                    "Dynamic descriptor lookahead and occupied IY", "Cold/reload/EOF/progress UI",
                    "Physical Pentagon128/512/1024 paging or Spectrum/Scorpion contention",
                    "Whole-song source order, frequency/amplitude stability, listening quality or bootable TRD"],
        decision="The exact28T bank I/O bridge is feasible in isolation without extra speaker writes. Integrate only after its register and lookup work fits the full sample schedule.")
    save(folder / "report.json", report)
    artifacts = {str(p.relative_to(folder)).replace("\\", "/"):
                 dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
                 for p in sorted(folder.rglob("*")) if p.is_file()}
    save(folder / "manifest.json", dict(complete=True, artifact_files=artifacts))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    result = run(args.output, args.quick)
    print(json.dumps({k: result[k] for k in ("complete", "quick_subset", "elapsed_seconds", "native")}))
