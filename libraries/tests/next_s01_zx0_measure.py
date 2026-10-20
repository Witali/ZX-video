"""S01: bounded Standard-size audit and complete useful raw qualification.

Screen the reset-complete SMC and one count-selected JP intermediate on473
cases. Use the independent protected CPU for counts, plain/IRQ/relocation,
actual minimum-safe compressed overlap, preserved registers and EOF cursors.
"""
import argparse
from collections import Counter
from datetime import date
import gzip
import hashlib
import inspect
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT/"libraries/lzsa/src", ROOT/"libraries/zx0/src",
                  ROOT/"libraries/tests", ROOT, ROOT.parents[1]/".tmp/library-test-deps"):
    sys.path.insert(0, str(directory))

from emulator.cpu import execute_block, load_library
import native_block
from native_inplace_block import execute as inplace, host_trace
from measure_bit_phases import samples
from measure_mega_prefix import high_word_samples
from next_s01_zx0_profiles import build, host_counts, predicted_delta
from zx0.block import build as public_block
import z80


DLL_SHA = "21e89129d040c6c29112c8977b5cb28573ae09f75632f5b993308204a76b2db8"
SELECTED_JUMP = "gamma-jp"
KINDS = ("smc", SELECTED_JUMP)


def sha(blob): return hashlib.sha256(blob).hexdigest()


def binding(profile):
    regions, labels, metadata = profile
    return dict(regions=[dict(address=at, bytes=len(blob), sha256=sha(blob)) for at, blob in regions],
        labels=labels, labels_sha256=sha(json.dumps(labels, sort_keys=True).encode()), metadata=metadata)


def protected_source():
    source = inspect.getsource(native_block.execute)
    old = "preserved=dict(ix=0x1357,alt_bc=0x2468,alt_de=0x369a,alt_hl=0xace1)"
    assert source.count(old) == 1
    source = source.replace(old, "preserved=dict(ix=0x1357,iy=0x57b9,alt_af=alternate_af,alt_bc=0x2468,alt_de=0x369a,alt_hl=0xace1)")
    source = source.replace("m.alt_af=alternate_af", "m.alt_af=alternate_af;m.af=0x5a93;m.bc=0xb7d9")
    assert source.count("high=output;cursor=source;lowest=stack-2") == 1
    source = source.replace("high=output;cursor=source;lowest=stack-2",
        "high=output;cursor=source;lowest=stack-2;digest=hashlib.sha256()")
    assert source.count("            high+=1") == 1
    source = source.replace("            high+=1", "            digest.update((cursor-source).to_bytes(4,'little'));high+=1")
    source = source.replace("return dict(tstates=budget-m.ticks_to_stop,exact=True,", 
        "return dict(write_input_cursors_sha256=digest.hexdigest(),tstates=budget-m.ticks_to_stop,exact=True,")
    return source


_namespace = dict(vars(native_block), hashlib=hashlib)
exec(compile(protected_source(), "<S01 protected runner: IY/AF-alt/digest only>", "exec"), _namespace)
PROTECTED = _namespace["execute"]


def dirty(profile):
    regions, labels, metadata = profile
    patches = set(metadata["patched_addresses"])
    return [(at, bytes(0xa5 if at+i in patches else value for i, value in enumerate(blob)))
            for at, blob in regions], labels, metadata


def layout(large):
    return dict(core=0x0800, relocated=0x0703, source=0x0400, output=0x3000,
                caller_stack=0x2ff0) if large else dict(core=0x8000, relocated=0x9103,
                source=0x2000, output=0xc000, caller_stack=0xbff0)


def run_protected(profile, payload, raw, large, **kwargs):
    allocation = layout(large)
    return PROTECTED(dirty(profile), payload, raw, source=allocation["source"],
        output=allocation["output"], caller_stack=allocation["caller_stack"],
        alternate_af=0x9797, **kwargs)


def native_modes(profile, moved, payload, raw, large, expected, host):
    allocation = layout(large); results = {}
    for mode, emitted, irq, overlap in (("plain", profile, False, False),
            ("irq", profile, True, False), ("relocated", moved, False, False),
            ("inplace_plain", profile, False, True), ("inplace_irq", profile, True, True),
            ("inplace_relocated", moved, False, True)):
        if overlap:
            result = inplace(emitted, payload, raw, codec="zx0", output=allocation["output"],
                caller_stack=allocation["caller_stack"], interrupts=irq)
            assert result["host_read_order_exact"] and result["code_protected"] and result["raw_abi_exact"]
            assert result["native_minimum_input_start"] == result["host_minimum_input_start"]
        else:
            result = run_protected(emitted, payload, raw, large, interrupts=irq)
        assert result["write_input_cursors_sha256"] == host["write_input_cursors_sha256"]
        if not irq: assert result["tstates"] == expected, (mode, result["tstates"], expected)
        assert result["stack_bytes"] <= profile[2]["caller_stack_bytes"]+(6 if irq else 0)
        results[mode] = result
    return results


def source_hashes():
    names = ("libraries/tests/next_s01_zx0_profiles.py", "libraries/tests/next_s01_zx0_measure.py",
        "libraries/tests/native_block.py", "libraries/tests/native_inplace_block.py",
        "libraries/tests/measure_bit_phases.py", "libraries/tests/measure_mega_prefix.py",
        "libraries/tests/profile_branch_mix.py", "libraries/zx0/src/zx0/asm/dzx0_standard.asm",
        "libraries/zx0/src/zx0/block.py", "libraries/zx0/src/zx0/_z80.py",
        "libraries/zx0/src/zx0/codec.py", "libraries/zx0/src/zx0/inplace.py",
        "libraries/zx0/src/zx0/tokens.py", "toolkit/zx0_speed.py", "emulator/cpu.py")
    return {name: sha((ROOT/name).read_bytes().replace(b"\r\n", b"\n")) for name in names}


def summary(rows, field="c_guarded"):
    real = [row for row in rows if row["real"]]
    slower = [dict(case=row["case"], real=row["real"], delta_tstates=row["delta_tstates"])
              for row in rows if row["delta_tstates"] > 0]
    return dict(cases=len(rows), real_cases=len(real),
        real_tstates=sum(row[field]["tstates"] for row in real),
        all_tstates=sum(row[field]["tstates"] for row in rows),
        real_delta_tstates=sum(row["delta_tstates"] for row in real),
        all_delta_tstates=sum(row["delta_tstates"] for row in rows),
        faster_cases=sum(row["delta_tstates"] < 0 for row in rows),
        equal_cases=sum(row["delta_tstates"] == 0 for row in rows),
        slower_cases=slower, maximum_regression_tstates=max([row["delta_tstates"] for row in slower] or [0]))


def main(output, screen_only=False, resume=False):
    output = output.resolve()
    dll = ROOT/".tmp/codec-cpu-qualified/codec_cpu.dll"
    assert sha(dll.read_bytes()) == DLL_SHA
    library = load_library(dll)
    cases = [(name, payload, raw, False) for name, payload, raw in samples()]
    cases += [(name, payload, raw, True) for name, payload, raw in high_word_samples()]
    assert len(cases) == 473 and sum(name.startswith("real-") for name, *_ in cases) == 364
    sources = source_hashes()
    historical = json.loads((ROOT/"libraries/evidence/trick_23.json").read_text())
    jumps = json.loads((ROOT/"libraries/evidence/fast_jumps.json").read_text())["profiles"]["zx0-standard"]
    if resume:
        report = json.loads(gzip.decompress(output.read_bytes()))
        assert report["C_complete"] and report["launch_source_sha256_lf"] == sources
    else:
        report = dict(date=date.today().isoformat(), stage="S01-ZX0", complete=False,
            C_complete=False, raw_qualification_complete=False, release=False, public_changes=False,
            observed_base_commit="2d998229", minimum_baseline="Standard68code+6callerstack=74service",
            benchmark_scope="complete start, all per-call setup, EOF and RET; no omitted target initializer",
            metric_scope="service includes all code/state/tables/padding/scratch/required stacks; input/output/history excluded",
            launch_source_sha256_lf=sources, protected_source_sha256=sha(protected_source().encode()),
            protected_changes="IY and alternateAF sentinels, arbitrary AF/BC entry, output-write input-cursor digest; no guest timing changes",
            native_C=dict(path=str(dll), sha256=DLL_SHA, build_sha256=sha(dll.with_name("build.json").read_bytes())),
            native_kosarev_files={str(path): sha(path.read_bytes()) for path in
                [Path(z80.__file__)]+sorted(Path(z80.__file__).parent.glob("*.pyd"))},
            historical_proofs={name: sha((ROOT/"libraries/evidence"/name).read_bytes())
                for name in ("trick_23.json", "fast_jumps.json")},
            bounded_designs=dict(
                rst=dict(status="rejected before CPU execution", main_code_bytes=49, helper_bytes=15,
                    caller_stack_bytes=6, theoretical_service_bytes=70, helper_address=0x28,
                    reason="RST28 helper0028..0036 requires replacing Spectrum ROM; not an arbitrarily relocatable RAM decoder"),
                smc=dict(code_bytes=74, caller_stack_bytes=4, service_bytes=78,
                    startup_delta_bytes=3, copy_delta_bytes=1, new_offset_delta_bytes=2,
                    full_entry_reset_tstates=20, startup_delta_tstates=9,
                    model="9-28*match_copies-10*new_offset_entries+9*(new_offset_entries-1)"),
                selective_jump=dict(code_bytes=69, caller_stack_bytes=6, service_bytes=75,
                    selected=SELECTED_JUMP, selection="greatest real aggregate execution count at equal service",
                    static_only_unselected_layout_emitted=True, model="-2 per selected unconditional jump")),
            baseline=dict(**binding(build("standard")), blocks=[]), profiles={}, attempts=[],
            unperformed=["Spectrum contention/ROM/disk/movie timing", "public API/wheel integration", "unbounded minimum-size search"])

    def save():
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(gzip.compress((json.dumps(report, sort_keys=True, separators=(",", ":"))+"\n").encode(), mtime=0))

    current = dict(stage="start")
    try:
        save()
        if not resume:
            counts = [host_counts(payload, raw) for _, payload, raw, _ in cases]
            real = [count for (name, *_), count in zip(cases, counts) if name.startswith("real-")]
            gamma = sum(count["gamma_backtracks"] for count in real)
            copy = sum(count["copy_back_jumps"] for count in real)
            assert gamma == 804367 and copy == 238027 and gamma > copy
            report["bounded_designs"]["selective_jump"].update(real_gamma_back_jumps=gamma,
                real_copy_back_jumps=copy, predicted_gamma_delta=-2*gamma, predicted_copy_delta=-2*copy,
                scope="selection optimizes aggregate real CPU; other valid inputs can favor the unselected jump")
            golden = {row["case"]: row for row in historical["blocks"]}
            for index, ((name, payload, raw, large), dynamic) in enumerate(zip(cases, counts)):
                current = dict(stage="baseline C+protected counters", case=name, index=index)
                allocation = layout(large); profile = build("standard", core=allocation["core"])
                c = execute_block(profile, payload, raw, library=library, source=allocation["source"],
                    output=allocation["output"], caller_stack=allocation["caller_stack"])
                assert c["registers"]["af2"] == 0x9797
                if not large:
                    old = golden[name]
                    assert c["tstates"] == old["profiles"]["standard"]["tstates"]
                    assert sha(payload) == old["payload_sha256"] and sha(raw) == old["raw_sha256"]
                hits = Counter(); watch = {}
                addresses = {"gamma_backtracks": profile[1]["dzx0s_elias_backtrack"]+5,
                    "copy_back_jumps": profile[1]["dzx0s_elias"]-2,
                    "match_copies": profile[1]["dzx0s_copy"],
                    "new_offset_entries": profile[1]["dzx0s_new_offset"]}
                for key, address in addresses.items():
                    def observe(machine, key=key): hits[key] += 1
                    watch[address] = observe
                observed = run_protected(profile, payload, raw, large, watch=watch)
                assert observed["tstates"] == c["tstates"] and all(hits[key] == value for key, value in dynamic.items()), (name, hits, dynamic)
                host = host_trace("zx0", payload, raw)
                assert observed["write_input_cursors_sha256"] == host["write_input_cursors_sha256"]
                report["baseline"]["blocks"].append(dict(case=name, large_layout=large,
                    real=name.startswith("real-"), payload_sha256=sha(payload), raw_sha256=sha(raw),
                    payload_bytes=len(payload), raw_bytes=len(raw), counts=dynamic, c_guarded=c,
                    protected=observed, host=host, historical_main_exact=not large))
                if index%50 == 49: save(); print("baseline", index+1, flush=True)
            assert sum(row["c_guarded"]["tstates"] for row in report["baseline"]["blocks"] if row["real"]) == 201490104
            for kind in KINDS:
                p = build(kind); entry = dict(**binding(p), relocated=binding(build(kind, core=0x9103)),
                    high_word=binding(build(kind, core=0x0800)), high_word_relocated=binding(build(kind, core=0x0703)),
                    blocks=[], alignments=[], C_complete=False, native_complete=False)
                report["profiles"][kind] = entry
                for low in range(256):
                    aligned = build(kind, core=0x8000+low)
                    entry["alignments"].append(dict(low_byte=low, **binding(aligned)))
                    assert aligned[2]["service_memory_bytes"] == p[2]["service_memory_bytes"]
                for index, ((name, payload, raw, large), baseline) in enumerate(zip(cases, report["baseline"]["blocks"])):
                    current = dict(stage="C candidate", profile=kind, case=name, index=index)
                    allocation = layout(large)
                    got = execute_block(build(kind, core=allocation["core"]), payload, raw, library=library,
                        source=allocation["source"], output=allocation["output"], caller_stack=allocation["caller_stack"])
                    delta = predicted_delta(kind, baseline["counts"])
                    assert got["tstates"] == baseline["c_guarded"]["tstates"]+delta, (kind, name, got, delta)
                    assert got["registers"]["af2"] == 0x9797
                    assert got["stack_bytes"] <= p[2]["caller_stack_bytes"]
                    entry["blocks"].append(dict(case=name, real=name.startswith("real-"), large_layout=large,
                        payload_sha256=sha(payload), raw_sha256=sha(raw), baseline_tstates=baseline["c_guarded"]["tstates"],
                        delta_tstates=delta, model_exact=True, c_guarded=got))
                    if index%100 == 99: print("C candidate", kind, index+1, flush=True)
                entry.update(C_complete=True, summary=summary(entry["blocks"]))
                save(); print("C complete", kind, entry["summary"], flush=True)
            for baseline, old in zip(report["baseline"]["blocks"], jumps["blocks"]):
                assert not baseline["large_layout"] and baseline["case"] == old["case"]
                assert baseline["c_guarded"]["tstates"]-2*(baseline["counts"]["gamma_backtracks"]+baseline["counts"]["copy_back_jumps"]) == old["candidate_tstates"]
            report["existing_both_jumps"] = dict(code_bytes=70, caller_stack_bytes=6,
                service_bytes=76, historical_complete_main_cases=417,
                real_tstates=jumps["summary"]["real_candidate_tstates"], byte_regions=binding(public_block("standard", fast_jumps=True))["regions"],
                scope="existing public profile; archived417-case CPU independently agrees with counted -2T at both sites")
            report["C_complete"] = True
            save()
        if screen_only: return report
        for kind in KINDS:
            entry = report["profiles"][kind]
            for index, ((name, payload, raw, large), row, baseline) in enumerate(zip(cases, entry["blocks"], report["baseline"]["blocks"])):
                current = dict(stage="protected6mode", profile=kind, case=name, index=index)
                allocation = layout(large)
                row["native"] = native_modes(build(kind, core=allocation["core"]),
                    build(kind, core=allocation["relocated"]), payload, raw, large,
                    row["c_guarded"]["tstates"], baseline["host"])
                if index%50 == 49: save(); print("protected6mode", kind, index+1, flush=True)
            boundary = []
            probes = (next(case for case in cases if case[0] == "literal-1"),
                      next(case for case in cases if case[0] == "match-1"),
                      next(case for case in cases if case[0] == "high-word-offset-1-length-49151"))
            for name, payload, raw, large in probes:
                allocation = layout(large); result = {}
                expected = next(row["c_guarded"]["tstates"] for row in entry["blocks"] if row["case"] == name)
                for mode, core, irq in (("plain", allocation["core"], False),
                        ("irq", allocation["core"], True), ("relocated", allocation["relocated"], False)):
                    got = PROTECTED(dirty(build(kind, core=core)), payload, raw,
                        source=allocation["source"], output=0xffff-len(raw),
                        caller_stack=allocation["caller_stack"], alternate_af=0x9797, interrupts=irq)
                    if not irq: assert got["tstates"] == expected
                    assert got["stack_bytes"] <= build(kind)[2]["caller_stack_bytes"]+(6 if irq else 0)
                    result[mode] = got
                boundary.append(dict(case=name, output_cursor=0xffff, modes=result))
            entry["FFFF_output_cursor_probes"] = boundary
            rows = entry["blocks"]
            entry.update(native_complete=True, qualification=dict(complete=True, cases=473,
                high_word_cases=56, modes_per_case=6, native_configs=473*6, FFFF_configs=9,
                maximum_plain_stack_bytes=max(row["native"]["plain"]["stack_bytes"] for row in rows),
                maximum_irq_stack_bytes=max(row["native"]["irq"]["stack_bytes"] for row in rows),
                maximum_inplace_irq_stack_bytes=max(row["native"]["inplace_irq"]["stack_bytes"] for row in rows),
                actual_overlap_cases=sum(row["native"]["inplace_plain"]["actual_overlap_bytes"] > 0 for row in rows),
                host_native_input_write_digests_exact=True, dirty_offset_reset_tested=kind == "smc",
                all_required_initialization_inside_measured_call=True,
                maximum_intrinsic_service_bytes=entry["metadata"]["service_memory_bytes"],
                with_reference13B_IRQ_and6B_extra_stack=entry["metadata"]["service_memory_bytes"]+19,
                injected_interrupts=sum(row["native"][mode]["injected_interrupts"] for row in rows for mode in ("irq", "inplace_irq"))))
            save(); print("FULL complete", kind, entry["qualification"], flush=True)
        assert source_hashes() == sources, "S01 executed sources changed"
        report.update(complete=True, raw_qualification_complete=True, final_source_sha256_lf=source_hashes(),
            decision="No smaller Spectrum-valid service layout found in these three bounded designs; two useful faster/larger raw intermediates completely qualified. Fixed-ROM RST proposal rejected, not a public minimum or a global impossibility proof.")
        save()
    except BaseException as error:
        report["attempts"].append(dict(**current, error=repr(error), complete=False))
        report["failure"] = dict(**current, error=repr(error))
        save(); raise
    overview = {key: value for key, value in report.items() if key not in ("baseline", "profiles")}
    overview["baseline"] = dict(service_bytes=74, real_tstates=201490104,
        all_tstates=sum(row["c_guarded"]["tstates"] for row in report["baseline"]["blocks"]), cases=473)
    overview["profiles"] = {kind: {key: value for key, value in entry.items() if key not in ("blocks", "alignments", "labels")}
                            for kind, entry in report["profiles"].items()}
    overview["full_evidence"] = dict(path=output.relative_to(ROOT).as_posix(), sha256=sha(output.read_bytes()))
    output.with_name("next_s01_zx0.json").write_text(json.dumps(overview, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"libraries/evidence/next_s01_zx0_full.json.gz")
    parser.add_argument("--screen-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    main(arguments.output, arguments.screen_only, arguments.resume)
