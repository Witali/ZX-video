"""E04: one cap255 candidate, exact insertion model and complete raw gates.

The accepted cap228 fast layout is authenticated against frozen E01 native
regions and E00 counts. Target startup includes its 20T offset reset within
46T; no caller-visible initializer or uncounted target storage is introduced.
"""
import argparse
from collections import Counter
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT/"libraries/zx0/src", ROOT/"libraries/lzsa/src",
                  ROOT/"libraries/tests", ROOT, ROOT.parents[1]/".tmp/library-test-deps"):
    sys.path.insert(0, str(directory))

from emulator.cpu import execute_block, load_library
from measure_bit_phases import samples
from measure_mega_prefix import high_word_samples
from native_inplace_block import execute as inplace, host_trace
from next_s01_zx0_measure import PROTECTED, protected_source, dirty, layout, DLL_SHA
from next_e04_profiles import build, baseline, boundary_cases, transformed_sources
from profile_branch_mix import instructions
import z80


E01_SHA = "0641d507f137b95f03e4d4d4a6a9214fbfc10fd8ccd98a529bb1ec44107b9d55"
EXPECTED_REAL = 139546674


def sha(blob): return hashlib.sha256(blob).hexdigest()


def read(name):
    blob = (ROOT/"libraries/evidence"/name).read_bytes()
    return json.loads(gzip.decompress(blob) if name.endswith(".gz") else blob)


def regions(profile):
    return [dict(address=at, bytes=len(blob), sha256=sha(blob)) for at, blob in profile[0]]


def binding(profile):
    return dict(regions=regions(profile), labels=profile[1],
        labels_sha256=sha(json.dumps(profile[1], sort_keys=True).encode()), metadata=profile[2])


class CopyObserver:
    """Prove each word entry and positive residual at every actual LDIR.

    Descending suffix labels are fall-through aliases within one copy. Count
    only its first shared entry. At255 entry BC>=256; the first LDIR must
    observe exactly BC-entry minus255, hence at least one remaining byte.
    """
    def __init__(self, profile):
        self.active = None
        self.words = 0
        self.positive_ldir_iterations = 0
        self.long_entries = []
        self.word_residuals = []
        self.watch = {}
        entries = profile[2]["shared_prefix_audit"]["shared_suffix_entries"]
        for name, info in entries.items():
            def enter(machine, name=name, info=info):
                if self.active is not None: return
                count = info["prefix_bytes"]
                assert machine.bc > count, (name, machine.bc, count)
                self.active = dict(label=name, family=info["family"], phase=info["phase"],
                    prefix_bytes=count, incoming_bc=machine.bc)
                if machine.bc >= 254: self.long_entries.append(dict(self.active))
                if count > 127:
                    assert machine.bc >= 256
                    self.words += 1
            self.watch[profile[1][name]] = enter
        for origin, blob in profile[0]:
            for at, opcode in instructions(blob, origin):
                if opcode != b"\xed\xb0": continue
                def remainder(machine):
                    assert machine.bc > 0, (machine.pc, machine.bc)
                    self.positive_ldir_iterations += 1
                    if self.active is not None:
                        before = self.active
                        assert machine.bc == before["incoming_bc"]-before["prefix_bytes"], (before, machine.bc)
                        if before["prefix_bytes"] > 127:
                            self.word_residuals.append(dict(before, remaining_bc=machine.bc))
                        self.active = None
                assert at not in self.watch
                self.watch[at] = remainder

    def finish(self):
        assert self.active is None
        return dict(word_entries=self.words, positive_LDIR_iterations=self.positive_ldir_iterations,
            long_prefix_entries=self.long_entries, word_residuals=self.word_residuals)


def protected(profile, payload, raw, large, *, interrupts=False):
    allocation = layout(large); observer = CopyObserver(profile)
    got = PROTECTED(dirty(profile), payload, raw, source=allocation["source"],
        output=allocation["output"], caller_stack=allocation["caller_stack"],
        alternate_af=0x9797, interrupts=interrupts, watch=observer.watch)
    return dict(got, copies=observer.finish())


def native_modes(profile, moved, payload, raw, large, expected, host, words):
    allocation = layout(large); result = {}
    for name, emitted, irq, overlap in (("plain", profile, False, False),
            ("irq", profile, True, False), ("relocated", moved, False, False),
            ("inplace_plain", profile, False, True), ("inplace_irq", profile, True, True),
            ("inplace_relocated", moved, False, True)):
        if overlap:
            observer = CopyObserver(emitted)
            got = inplace(emitted, payload, raw, codec="zx0", output=allocation["output"],
                caller_stack=allocation["caller_stack"], interrupts=irq, watch=observer.watch)
            got["copies"] = observer.finish()
            assert got["host_read_order_exact"] and got["code_protected"] and got["raw_abi_exact"]
            assert got["host_minimum_input_start"] == got["native_minimum_input_start"]
        else:
            got = protected(emitted, payload, raw, large, interrupts=irq)
        assert got["copies"]["word_entries"] == words
        assert got["write_input_cursors_sha256"] == host["write_input_cursors_sha256"]
        assert got["stack_bytes"] <= (10 if irq else 4)
        if not irq: assert got["tstates"] == expected, (name, got["tstates"], expected)
        result[name] = got
    return result


def source_hashes():
    names = ("libraries/tests/next_e04_profiles.py", "libraries/tests/next_e04_measure.py",
        "libraries/tests/next_s01_zx0_measure.py", "libraries/tests/next_s01_zx0_profiles.py",
        "libraries/tests/native_block.py", "libraries/tests/native_inplace_block.py",
        "libraries/tests/measure_bit_phases.py", "libraries/tests/measure_mega_prefix.py",
        "libraries/tests/profile_branch_mix.py", "libraries/zx0/src/zx0/maximum.py",
        "libraries/zx0/src/zx0/maximum_branches.py", "libraries/zx0/src/zx0/_shared_prefixes.py",
        "libraries/zx0/src/zx0/_z80.py", "libraries/zx0/src/zx0/asm/dzx0_mega.asm",
        "libraries/zx0/src/zx0/codec.py", "libraries/zx0/src/zx0/inplace.py",
        "libraries/zx0/src/zx0/tokens.py", "toolkit/zx0_speed.py", "emulator/cpu.py",
        "libraries/Z80_TIMINGS.md")
    return {name: sha((ROOT/name).read_bytes().replace(b"\r\n", b"\n")) for name in names}


def summarize(rows):
    slower = [dict(case=row["case"], real=row["real"], delta_tstates=row["delta_tstates"])
              for row in rows if row["delta_tstates"] > 0]
    return dict(cases=len(rows), real_cases=sum(row["real"] for row in rows),
        real_tstates=sum(row["c_guarded"]["tstates"] for row in rows if row["real"]),
        all_tstates=sum(row["c_guarded"]["tstates"] for row in rows),
        real_delta_tstates=sum(row["delta_tstates"] for row in rows if row["real"]),
        all_delta_tstates=sum(row["delta_tstates"] for row in rows),
        faster_cases=sum(row["delta_tstates"] < 0 for row in rows),
        equal_cases=sum(row["delta_tstates"] == 0 for row in rows), slower_cases=slower,
        maximum_regression_tstates=max([row["delta_tstates"] for row in slower] or [0]))


def main(output):
    output = output.resolve()
    dll = ROOT/".tmp/codec-cpu-qualified/codec_cpu.dll"
    assert sha(dll.read_bytes()) == DLL_SHA
    e01_blob = (ROOT/"libraries/evidence/next_e01_zx0_branches.json.gz").read_bytes()
    assert sha(e01_blob) == E01_SHA
    e01 = read("next_e01_zx0_branches.json.gz")
    e00_blob = (ROOT/"libraries/evidence/next_e00_zx0_profile.json.gz").read_bytes()
    assert e01["e00_report_sha256"] == sha(e00_blob)
    e00 = json.loads(gzip.decompress(e00_blob))
    assert e01["complete"] and e00["complete"]
    previous = e01["profiles"]["228-all_profitable_reachable"]
    assert previous["complete"] and previous["real_candidate_tstates"] == 139552884
    public_auth = read("next_e01_zx0_public.json")
    assert public_auth["complete"]
    call = next(row for row in public_auth["current_public_calls"] if row["kwargs"] == dict(prefix_cap=228, policy="fast"))
    assert call["labels"] == baseline()[1] and call["regions"] == regions(baseline())
    cases = [(name, payload, raw, False) for name, payload, raw in samples()]
    cases += [(name, payload, raw, True) for name, payload, raw in high_word_samples()]
    assert len(cases) == 473
    extras = list(boundary_cases())
    assert len(extras) == 36
    library = load_library(dll); sources = source_hashes()
    assert all(not re.search(rb"[ \t]+\r?$", (ROOT/name).read_bytes(), re.MULTILINE)
               for name in ("libraries/tests/next_e04_profiles.py", "libraries/tests/next_e04_measure.py"))
    report = dict(date=date.today().isoformat(), stage="E04", observed_base_commit="ac8355e5",
        complete=False, C_complete=False, raw_qualification_complete=False, release=False,
        public_changes=False, launch_source_sha256_lf=sources,
        transformed_source_sha256=[sha(source.encode()) for source in transformed_sources()],
        fixed_branch_selection="all61 cap228 fast contractions retained; no new branch selection",
        inherited_E01_branch_lineage=dict(comparison="historical cap228 fast versus shared cap228 before61 contractions; not a new cap255 baseline",
            historical_slower_cases=previous["slower_cases"], historical_slower_real_cases=previous["slower_real_cases"],
            historical_maximum_delta_tstates=previous["maximum_delta_tstates"]),
        model="-135T per E00 word-prefix entry:27 LDIs replace27 repeating LDIR iterations",
        memory_scope="all code/embedded offset, caller return/live source stack; input/output/history excluded",
        initialization=dict(startup_tstates=46, offset_reset_tstates=20,
            target_initializer_required=False, all_setup_inside_start_through_EOF=True),
        native_C=dict(path=str(dll), sha256=DLL_SHA, build_sha256=sha(dll.with_name("build.json").read_bytes())),
        C_qualification_proofs={name: sha((ROOT/"emulator/evidence"/name).read_bytes()) for name in ("verification.json", "native_build.json")},
        native_kosarev_files={str(path): sha(path.read_bytes()) for path in
            [Path(z80.__file__)]+sorted(Path(z80.__file__).parent.glob("*.pyd"))},
        protected_source_sha256=sha(protected_source().encode()),
        archived_proofs={name: sha((ROOT/"libraries/evidence"/name).read_bytes()) for name in
            ("next_e00_zx0_profile.json.gz", "next_e01_zx0_branches.json.gz", "next_e01_zx0_public.json")},
        baseline=dict(**binding(baseline()), real_tstates=139552884, blocks=[]),
        candidate=dict(**binding(build()), relocated=binding(build(core=0x9103)),
            high_word=binding(build(core=0x0800)), high_word_relocated=binding(build(core=0x0703)),
            blocks=[], supplemental=[], alignments=[], C_complete=False, native_complete=False),
        attempts=[], unperformed=["public API/CLI/export/wheel integration", "coroutine/input guards", "physical ULA/ROM/disk/movie timing"])

    def save():
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(gzip.compress((json.dumps(report, sort_keys=True, separators=(",", ":"))+"\n").encode(), mtime=0))

    current = dict(stage="geometry")
    try:
        save()
        for core, key in ((0x8000, "regions"), (0x9103, "relocated_regions"),
                          (0x0800, "high_word_regions"), (0x0703, "high_word_relocated_regions")):
            assert regions(baseline(core=core)) == previous[key]
            assert build(core=core, prefix_cap=228)[:2] == baseline(core=core)[:2]
        for low in range(256):
            p = build(core=0x8000+low)
            assert build(core=0x8000+low, prefix_cap=228)[:2] == baseline(core=0x8000+low)[:2]
            report["candidate"]["alignments"].append(dict(origin=0x8000+low, regions=regions(p),
                labels_sha256=sha(json.dumps(p[1], sort_keys=True).encode()),
                service_bytes=p[2]["service_memory_bytes"], reference_IRQ_inclusive_bytes=p[2]["service_memory_bytes"]+19))
            assert p[2]["service_memory_bytes"] == 8165 and p[2]["service_memory_bytes"]+19 <= 10000
        golden = {row["case"]: row for row in previous["blocks"]}
        oracle = {row["case"]: row for row in e00["profiles"]["228"]["blocks"]}
        for index, (name, payload, raw, large) in enumerate(cases):
            current = dict(stage="C baseline+candidate", case=name, index=index)
            old, count = golden[name], oracle[name]
            assert sha(payload) == old["input_sha256"] == count["input_sha256"]
            assert sha(raw) == old["output_sha256"] == count["output_sha256"]
            allocation = layout(large)
            p, new = baseline(core=allocation["core"]), build(core=allocation["core"])
            options = dict(library=library, source=allocation["source"], output=allocation["output"], caller_stack=allocation["caller_stack"])
            before = execute_block(p, payload, raw, **options)
            after = execute_block(new, payload, raw, **options)
            assert before["tstates"] == old["candidate_tstates"]
            words = count["reused_saved_word_entries"]
            delta = -135*words
            assert after["tstates"] == before["tstates"]+delta and after["stack_bytes"] <= 4
            assert before["registers"]["af2"] == after["registers"]["af2"] == 0x9797
            host = host_trace("zx0", payload, raw)
            report["baseline"]["blocks"].append(dict(case=name, c_guarded=before, E01_native_exact=True, word_entries=words, host=host))
            report["candidate"]["blocks"].append(dict(case=name, real=name.startswith("real-"), large_layout=large,
                payload_sha256=sha(payload), raw_sha256=sha(raw), payload_bytes=len(payload), raw_bytes=len(raw),
                baseline_tstates=before["tstates"], delta_tstates=delta, word_entries=words, model_exact=True, c_guarded=after))
            if index%100 == 99: save(); print("C screen", index+1, flush=True)
        assert sum(row["word_entries"] for row in report["candidate"]["blocks"] if row["real"]) == 46
        assert sum(row["word_entries"] for row in report["candidate"]["blocks"]) == 186
        for name, payload, raw, request in extras:
            current = dict(stage="C boundary", case=name)
            before = execute_block(baseline(), payload, raw, library=library)
            observed = protected(baseline(), payload, raw, False)
            assert observed["tstates"] == before["tstates"]
            words = observed["copies"]["word_entries"]
            after = execute_block(build(), payload, raw, library=library)
            delta = -135*words
            assert after["tstates"] == before["tstates"]+delta
            report["candidate"]["supplemental"].append(dict(case=name, request=request,
                payload_sha256=sha(payload), raw_sha256=sha(raw), word_entries=words,
                baseline_tstates=before["tstates"], delta_tstates=delta, c_guarded=after,
                baseline_protected=observed, host=host_trace("zx0", payload, raw)))
        report["candidate"]["summary"] = summarize(report["candidate"]["blocks"])
        assert report["candidate"]["summary"]["real_tstates"] == EXPECTED_REAL
        report["candidate"]["C_complete"] = report["C_complete"] = True
        save(); print("C complete", report["candidate"]["summary"], flush=True)
        for index, ((name, payload, raw, large), row, old) in enumerate(zip(cases,
                report["candidate"]["blocks"], report["baseline"]["blocks"])):
            current = dict(stage="protected6mode", case=name, index=index)
            allocation = layout(large)
            row["native"] = native_modes(build(core=allocation["core"]), build(core=allocation["relocated"]),
                payload, raw, large, row["c_guarded"]["tstates"], old["host"], row["word_entries"])
            if index%50 == 49: save(); print("protected6mode", index+1, flush=True)
        coverage = set()
        for (name, payload, raw, request), row in zip(extras, report["candidate"]["supplemental"]):
            current = dict(stage="boundary6mode", case=name)
            row["native"] = native_modes(build(), build(core=0x9103), payload, raw, False,
                row["c_guarded"]["tstates"], row["host"], row["word_entries"])
            entries = [entry for entry in row["native"]["plain"]["copies"]["long_prefix_entries"] if entry["family"] == request["family"]]
            assert len(entries) == 1, (name, entries)
            coverage.add((request["family"], entries[0]["phase"], request["decoded_length"]))
        expected_coverage = {(family, phase, count) for family in ("length", "literals", "reuse")
                             for phase in (1, 3, 5, 7) for count in (255, 256, 257)}
        assert coverage == expected_coverage, (coverage, expected_coverage-coverage)
        report["candidate"]["boundary_coverage"] = [dict(family=f, phase=p, decoded_length=n) for f, p, n in sorted(coverage)]
        boundary = []
        for wanted in ("literal-1", "match-1", "high-word-offset-1-length-49151"):
            name, payload, raw, large = next(case for case in cases if case[0] == wanted)
            allocation = layout(large); results = {}
            expected = next(row["c_guarded"]["tstates"] for row in report["candidate"]["blocks"] if row["case"] == name)
            for mode, core, irq in (("plain", allocation["core"], False),
                    ("irq", allocation["core"], True), ("relocated", allocation["relocated"], False)):
                observer = CopyObserver(build(core=core))
                got = PROTECTED(dirty(build(core=core)), payload, raw, source=allocation["source"],
                    output=0xffff-len(raw), caller_stack=allocation["caller_stack"], alternate_af=0x9797,
                    interrupts=irq, watch=observer.watch)
                got["copies"] = observer.finish()
                if not irq: assert got["tstates"] == expected
                assert got["stack_bytes"] <= (10 if irq else 4)
                results[mode] = got
            boundary.append(dict(case=name, output_cursor=0xffff, modes=results))
        report["candidate"]["FFFF_output_cursor_probes"] = boundary
        rows = report["candidate"]["blocks"]+report["candidate"]["supplemental"]
        report["candidate"]["qualification"] = dict(complete=True, frozen_cases=473, supplemental_cases=36,
            modes_per_case=6, native_configs=len(rows)*6, FFFF_configs=9, BC_word_entry_and_positive_LDIR_exact=True,
            maximum_plain_stack_bytes=max(row["native"]["plain"]["stack_bytes"] for row in rows),
            maximum_irq_stack_bytes=max(row["native"]["irq"]["stack_bytes"] for row in rows),
            maximum_inplace_irq_stack_bytes=max(row["native"]["inplace_irq"]["stack_bytes"] for row in rows),
            actual_overlap_cases=sum(row["native"]["inplace_plain"]["actual_overlap_bytes"] > 0 for row in report["candidate"]["blocks"]),
            host_native_input_write_digests_exact=True, dirty_offset_reset_tested=True,
            intrinsic_service_bytes=8165, with_reference13B_IRQ_and6B_extra_stack=8184,
            injected_interrupts=sum(row["native"][mode]["injected_interrupts"] for row in rows for mode in ("irq", "inplace_irq")))
        assert source_hashes() == sources, "E04 executed source changed"
        report["candidate"]["native_complete"] = True
        report.update(complete=True, raw_qualification_complete=True, final_source_sha256_lf=source_hashes(),
            decision="Cap255 is648 service bytes larger and6210 realT faster than accepted cap228-fast; retains a nondominated maximum-speed point below10000. All finite measured cases are equal or faster. No global-optimality claim.")
        save(); print("FULL complete", report["candidate"]["qualification"], flush=True)
    except BaseException as error:
        report["attempts"].append(dict(**current, error=repr(error), complete=False))
        report["failure"] = dict(**current, error=repr(error))
        save(); raise
    overview = {key: value for key, value in report.items() if key not in ("baseline", "candidate")}
    overview["baseline"] = dict(service_bytes=7517, real_tstates=139552884, regions=report["baseline"]["regions"])
    overview["candidate"] = {key: value for key, value in report["candidate"].items() if key not in ("blocks", "supplemental", "alignments", "labels")}
    overview["full_evidence"] = dict(path=output.relative_to(ROOT).as_posix(), sha256=sha(output.read_bytes()))
    output.with_name("next_e04.json").write_text(json.dumps(overview, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"libraries/evidence/next_e04_full.json.gz")
    main(parser.parse_args().output)
