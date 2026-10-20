"""Bind installed Hot emitters to complete, frozen private F00 native proof.

These checks reuse CPU/IRQ/overlap evidence only through exact emitted region
hashes and every native-origin label. All 256 alignment rows are authenticated
separately; no historical source hash is relabelled as a current source hash.
"""
import gzip
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT/"libraries/lzsa/src", ROOT/"libraries/tests"):
    sys.path.insert(0, str(directory))

from lzsa import hot
from lzsa.export import export
from lzsa import _wide_kernels
from next_f00_profiles import build as private_build


PROOF = ROOT/"libraries/evidence/next_f00_full.json.gz"
PROOF_SHA256 = "00b1facac131ba65f880989af84e0a013958bec9fe66a24733f7c09873c5ad66"
PROFILES = {"literals": ("hot_clone", 9529, 14913435),
            "nibble": ("hot_pair", 9515, 14918596),
            "combined": ("combined", 9545, 14905725)}


def region_rows(profile):
    return [dict(address=address, bytes=len(blob), sha256=sha256(blob).hexdigest())
            for address, blob in profile[0]]


def assembly_regions(path):
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("org "):
            result.append((int(line[5:], 16), bytearray()))
        elif line.startswith("db "):
            result[-1][1].extend(int(value[1:], 16) for value in line[3:].split(","))
    return [(address, bytes(blob)) for address, blob in result]


class HotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blob = PROOF.read_bytes()
        if sha256(blob).hexdigest() != PROOF_SHA256:
            raise AssertionError("Frozen F00 native proof hash differs")
        cls.proof = json.loads(gzip.decompress(blob))
        if not cls.proof["complete"] or not cls.proof["raw_qualification_complete"]:
            raise AssertionError("F00 native proof is incomplete")

    def test_native_proof_regions_and_every_label(self):
        for public, (private, size, ticks) in PROFILES.items():
            proof = self.proof["profiles"][private]
            self.assertTrue(proof["native_complete"] and proof["C_complete"])
            self.assertTrue(proof["qualification"]["complete"])
            self.assertEqual(proof["qualification"]["modes_per_case"], 6)
            self.assertEqual(proof["summary"]["real_tstates"], ticks)
            for core, binding in ((0x8000, proof), (0x9103, proof["relocated"])):
                with self.subTest(profile=public, core=core):
                    actual = hot.build(public, core=core)
                    self.assertEqual(region_rows(actual), binding["regions"])
                    self.assertEqual(actual[1], binding["labels"])
                    # Also exercise the historical private constructions on
                    # the hook-extended Wide/Hybrid sources, without rebinding
                    # their original executed-source manifests.
                    self.assertEqual(actual[:2], private_build(private, core=core)[:2])

    def test_all_256_alignments_match_saved_geometry(self):
        for public, (private, size, _) in PROFILES.items():
            rows = self.proof["profiles"][private]["alignments"]
            self.assertEqual(len(rows), 256)
            for low, row in enumerate(rows):
                with self.subTest(profile=public, low=low):
                    actual = hot.build(public, core=0x8000+low)
                    self.assertEqual(row["low_byte"], low)
                    self.assertEqual(region_rows(actual), row["regions"])
                    labels_hash = sha256(json.dumps(actual[1], sort_keys=True).encode()).hexdigest()
                    self.assertEqual(labels_hash, row["labels_sha256"])
                    memory = actual[2]["service_memory_bytes"]
                    self.assertEqual(memory, size+((-low)&255))
                    self.assertEqual(memory, row["service_bytes"])
                    self.assertEqual(memory+19, row["example_irq_inclusive_bytes"])
                    self.assertLessEqual(memory+19, 10000)

    def test_actual_inventory_raw_ABI_and_complete_call_metadata(self):
        for public, (_, size, ticks) in PROFILES.items():
            regions, labels, metadata = hot.build(public)
            self.assertEqual(sum(len(blob) for _, blob in regions)+6, size)
            self.assertEqual(sum(metadata["service_memory"].values()), size)
            self.assertEqual(metadata["service_memory_bytes"], size)
            self.assertEqual(metadata["total_storage_bytes"], size)
            self.assertEqual(metadata["nominal_aligned_service_bytes"], size)
            self.assertEqual(metadata["reference_real_tstates"], ticks)
            self.assertIn("complete entry setup through EOF", metadata["reference_real_tstates_scope"])
            self.assertEqual(metadata["caller_stack_bytes"], 6)
            self.assertEqual(metadata["decoder_stack_bytes"], 4)
            self.assertEqual(metadata["embedded_mutable_bytes"], 2)
            self.assertTrue(metadata["embedded_state_counted_once_in_code"])
            self.assertEqual(metadata["patched_addresses"], [labels["offset"], labels["offset"]+1])
            self.assertFalse(metadata["target_initializer_required"])
            self.assertEqual(metadata["runtime_generated_table_bytes"], 0)
            self.assertEqual(metadata["static_dispatch_table_bytes"], 512)
            self.assertTrue(metadata["one_shot"] and metadata["raw_only"])
            self.assertFalse(any(key.startswith("classic_reference_") for key in metadata))
            self.assertNotIn("test_only", metadata)
            self.assertNotIn("irq_qualified", metadata)
            self.assertNotIn("inplace_qualified", metadata)
            self.assertEqual("E02CloneStart" in labels, public != "nibble")
            self.assertEqual("e03_hot_first" in labels, public != "literals")

    def test_invalid_modes_reservations_and_wrapper_flags(self):
        for profile in ("unknown", "fast", "hot_clone", None, True, [], {}):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                hot.build(profile)
        for kwargs in (dict(core=-1), dict(core=65536), dict(core=True),
                       dict(core_limit=65537), dict(core_limit=0x8000),
                       dict(core_limit=True)):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                hot.build(**kwargs)
        for kwargs in (dict(_boundary=lambda a: None), dict(_literal_guards=True),
                       dict(_quota_hook=lambda a: None), dict(_assembler=lambda a: a),
                       dict(cold_match_extension=False), dict(short_lengths=(2,))):
            with self.subTest(kwargs=kwargs), self.assertRaises(TypeError):
                hot.build(**kwargs)
        for public, (_, size, _) in PROFILES.items():
            hot.build(public, core_limit=0x8000+size-6)
            with self.assertRaises(ValueError):
                hot.build(public, core_limit=0x8000+size-7)

    def test_drift_is_rejected_for_events_code_and_final_dispatch(self):
        assembler = hot._HotAssembler(0x8000, "nibble")
        assembler.label("body_167_0")
        with self.assertRaisesRegex(ValueError, "body emitter drift"):
            assembler.emit(0x00)
        original_kernel = _wide_kernels.emit_new_offset_short

        def corrupt_kernel(assembler, context, count):
            original_kernel(assembler, context, count)
            # Same size, altered opcode outside either replaced hot path.
            assembler.code[-4] ^= 1

        with patch.object(_wide_kernels, "emit_new_offset_short", corrupt_kernel):
            with self.assertRaisesRegex(ValueError, "canonical fingerprint drift"):
                hot.build()
        original_build = hot.hybrid.build

        def corrupt_dispatch(*args, **kwargs):
            regions, labels, metadata = original_build(*args, **kwargs)
            address, blob = regions[0]
            blob = bytearray(blob)
            blob[((address+255)&~255)-address] ^= 1
            return [(address, bytes(blob))], labels, metadata

        with patch.object(hot.hybrid, "build", corrupt_dispatch):
            with self.assertRaisesRegex(ValueError, "dispatch table drift"):
                hot.build()

    def test_ORG_DB_exports_preserve_exact_regions(self):
        with tempfile.TemporaryDirectory(dir=ROOT/".tmp", prefix="hot-export-") as temporary:
            for public in PROFILES:
                for core in (0x8000, 0x9103):
                    actual = hot.build(public, core=core)
                    directory = Path(temporary)/(public+"-"+str(core))
                    export(directory, *actual)
                    self.assertEqual(assembly_regions(directory/"decoder.asm"), actual[0])


if __name__ == "__main__":
    unittest.main()
