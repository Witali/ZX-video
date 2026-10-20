"""Authenticate public Small bytes against the frozen complete S01 proof.

Native replay is reused through exact regions and every label at the four
executed origins, plus all 256 saved alignment images. Historical executed
source hashes remain separate from this new installed emitter's identity.
"""
import gzip
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT/"libraries/zx0/src", ROOT/"libraries/lzsa/src",
                  ROOT/"libraries/tests", ROOT.parents[1]/".tmp/library-test-deps"):
    sys.path.insert(0, str(directory))

from zx0.small import build
from zx0.export import export
from next_s01_zx0_profiles import binary_oracle
from test_libraries import profiles


PROOF = ROOT/"libraries/evidence/next_s01_zx0_full.json.gz"
PROOF_SHA256 = "2a202c04484bc67ce1d32e15e68d130b2a97bc17a21d32947561728ac6fc6223"
PROFILES = {"smc": (74, 4, 43, 189794309), "gamma-jp": (69, 6, 34, 199881370)}


def regions(profile):
    return [dict(address=address, bytes=len(blob), sha256=sha256(blob).hexdigest())
            for address, blob in profile[0]]


def restore_assembly(path):
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("org "):
            result.append((int(line[5:], 16), bytearray()))
        elif line.startswith("db "):
            result[-1][1].extend(int(value[1:], 16) for value in line[3:].split(","))
    return [(address, bytes(blob)) for address, blob in result]


class SmallZX0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blob = PROOF.read_bytes()
        if sha256(blob).hexdigest() != PROOF_SHA256:
            raise AssertionError("Frozen S01 native proof hash differs")
        cls.proof = json.loads(gzip.decompress(blob))
        if not cls.proof["complete"] or not cls.proof["raw_qualification_complete"]:
            raise AssertionError("S01 native proof is incomplete")
        if cls.proof["launch_source_sha256_lf"] != cls.proof["final_source_sha256_lf"]:
            raise AssertionError("S01 executed-source identity differs")
        for name in ("libraries/tests/next_s01_zx0_profiles.py",
                     "libraries/tests/next_s01_zx0_measure.py"):
            actual = sha256((ROOT/name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            if actual != cls.proof["launch_source_sha256_lf"][name]:
                raise AssertionError("Frozen S01 private emitter/runner changed")

    def test_every_native_origin_region_and_label_exact(self):
        for profile in PROFILES:
            saved = self.proof["profiles"][profile]
            self.assertTrue(saved["native_complete"] and saved["C_complete"])
            self.assertTrue(saved["qualification"]["complete"])
            self.assertEqual(saved["qualification"]["cases"], 473)
            self.assertEqual(saved["qualification"]["modes_per_case"], 6)
            self.assertEqual(saved["qualification"]["FFFF_configs"], 9)
            self.assertEqual(saved["qualification"]["actual_overlap_cases"], 473)
            for core, binding in ((0x8000, saved), (0x9103, saved["relocated"]),
                                  (0x0800, saved["high_word"]),
                                  (0x0703, saved["high_word_relocated"])):
                with self.subTest(profile=profile, core=core):
                    actual = build(profile, core=core, core_limit=core+256)
                    self.assertEqual(regions(actual), binding["regions"])
                    self.assertEqual(actual[1], binding["labels"])
                    self.assertEqual(actual[:2], binary_oracle(profile, core))

    def test_all_256_alignments_match_saved_images_and_inventory(self):
        for profile, (code, stack, _, _) in PROFILES.items():
            rows = self.proof["profiles"][profile]["alignments"]
            self.assertEqual(len(rows), 256)
            for low, saved in enumerate(rows):
                with self.subTest(profile=profile, low=low):
                    actual = build(profile, core=0x8000+low)
                    self.assertEqual(saved["low_byte"], low)
                    self.assertEqual(regions(actual), saved["regions"])
                    self.assertEqual(actual[1], saved["labels"])
                    self.assertEqual(actual[:2], binary_oracle(profile, 0x8000+low))
                    self.assertEqual(sum(actual[2]["service_memory"].values()), code+stack)
                    self.assertEqual(actual[2]["service_memory_bytes"], code+stack)

    def test_raw_ABI_complete_initialization_and_embedded_state(self):
        for profile, (code, stack, startup, ticks) in PROFILES.items():
            emitted, labels, metadata = build(profile)
            self.assertEqual(len(emitted[0][1]), code)
            self.assertEqual(metadata["code_bytes"], code)
            self.assertEqual(metadata["core_end"], 0x8000+code)
            self.assertEqual(metadata["caller_stack_bytes"], stack)
            self.assertEqual(metadata["decoder_stack_bytes"], stack-2)
            self.assertEqual(metadata["service_memory_bytes"], code+stack)
            self.assertEqual(metadata["total_storage_bytes"], code+stack)
            self.assertEqual(metadata["startup_tstates"], startup)
            self.assertEqual(metadata["reference_real_tstates"], ticks)
            self.assertIn("364 real raw blocks", metadata["reference_real_tstates_scope"])
            self.assertFalse(metadata["target_initializer_required"])
            self.assertFalse(metadata["coroutine_supported"])
            self.assertEqual(metadata["runtime_generated_table_bytes"], 0)
            self.assertTrue(metadata["one_shot"] and metadata["raw_only"])
            self.assertEqual(metadata["preserved_registers"], ["IX", "IY", "AF'", "BC'", "DE'", "HL'"])
            self.assertNotIn("test_only", metadata)
            self.assertNotIn("irq_qualified", metadata)
            self.assertNotIn("inplace_qualified", metadata)
            self.assertEqual(metadata["embedded_mutable_bytes"], 2 if profile == "smc" else 0)
            self.assertTrue(metadata["embedded_state_counted_once_in_code"])
            if profile == "smc":
                self.assertEqual(metadata["patched_addresses"], [labels["s01_offset"], labels["s01_offset"]+1])
                self.assertEqual(metadata["offset_reset_tstates"], 20)
                self.assertTrue(metadata["requires_writable_code"] and metadata["nonreentrant"])
                self.assertFalse(metadata["rom_compatible"])
            else:
                self.assertEqual(metadata["patched_addresses"], [])
                self.assertEqual(metadata["offset_reset_tstates"], 0)
                self.assertFalse(metadata["requires_writable_code"] or metadata["nonreentrant"])
                self.assertTrue(metadata["rom_compatible"])

    def test_existing_defaults_remain_byte_exact(self):
        baseline = json.loads((ROOT/"libraries/tests/decoder_baseline.json").read_text())["profiles"]
        self.assertEqual(profiles(), baseline)

    def test_reject_unqualified_modes_flags_and_invalid_reservations(self):
        for profile in ("standard", "copy-jp", "unknown", None, True, [], {}):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                build(profile)
        for kwargs in (dict(core=-1), dict(core=65536), dict(core=True), dict(core=0.0),
                       dict(core_limit=65537), dict(core_limit=0x8000),
                       dict(core_limit=True), dict(core_limit=33792.0)):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                build(**kwargs)
        for kwargs in (dict(_quota_hook=lambda *args: None), dict(_boundary=lambda a: None),
                       dict(_assembler=lambda a: a), dict(fast_jumps=True),
                       dict(branch_tuned=True), dict(output_base=0xc000)):
            with self.subTest(kwargs=kwargs), self.assertRaises(TypeError):
                build(**kwargs)
        for profile, (code, _, _, _) in PROFILES.items():
            build(profile, core_limit=0x8000+code)
            build(profile, core=65536-code, core_limit=65536)
            with self.assertRaises(ValueError):
                build(profile, core_limit=0x8000+code-1)

    def test_exact_ORG_DB_exports(self):
        with tempfile.TemporaryDirectory(dir=ROOT/".tmp", prefix="small-zx0-export-") as temporary:
            for profile in PROFILES:
                for core in (0x8000, 0x9103):
                    actual = build(profile, core=core, core_limit=core+256)
                    directory = Path(temporary)/(profile+"-"+str(core))
                    export(directory, *actual)
                    self.assertEqual(restore_assembly(directory/"decoder.asm"), actual[0])

    def test_installed_source_builder_needs_no_repository_helpers(self):
        program = """import sys
sys.path.insert(0, sys.argv[1])
import zx0
before = set(sys.modules)
from zx0.small import build
assert build()[2]['service_memory_bytes'] == 78
assert build('gamma-jp')[2]['service_memory_bytes'] == 75
added = set(sys.modules)-before
assert not {'ast','inspect'} & added
assert not any(name.startswith(('next_', 'test_')) for name in added)
"""
        with tempfile.TemporaryDirectory(dir=ROOT/".tmp", prefix="small-zx0-isolated-") as temporary:
            result = subprocess.run([sys.executable, "-I", "-B", "-c", program,
                str(ROOT/"libraries/zx0/src")], cwd=temporary, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
