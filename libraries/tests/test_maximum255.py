"""The public cap255 opt-in remains one fixed resident branch layout.

These are generator/API tests. The separate public authenticator binds all
alignments and native placements to the protected E04 execution archive.
"""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'libraries/zx0/src'))
from zx0.maximum import build as maximum
from zx0.maximum_branches import build
from zx0.maximum_coroutine import build as coroutine


class Maximum255Tests(unittest.TestCase):
    def test_fixed_image_and_complete_service_inventory(self):
        regions, labels, meta = build(prefix_cap=255, policy='fast')
        self.assertEqual(hashlib.sha256(regions[0][1]).hexdigest(),
                         '6f59e27d67ac567fc2a6b30c76f8520403c3fd00e3e415d396023d8a99394553')
        self.assertEqual(hashlib.sha256(json.dumps(labels, sort_keys=True).encode()).hexdigest(),
                         '6c860d0542f6493e24eb60478a3c4ace032ae0a2bead462420cee0f9e2cabb8e')
        self.assertEqual(meta['code_bytes'], 8161)
        self.assertEqual(meta['service_memory_bytes'], 8165)
        self.assertEqual(sum(meta['service_memory'].values()), 8165)
        self.assertEqual(meta['workspace_bytes'], 8165)
        self.assertEqual(meta['max_decoder_stack_bytes'], 4)
        self.assertFalse(meta['coroutine_supported'])
        self.assertFalse(meta['globally_optimal'])
        self.assertTrue(meta['input_output_history_counted_separately'])
        self.assertEqual(meta['patched_addresses'],
                         [labels['dzx0m_last_offset+1'] + i for i in (0, 1)])
        for family in ('length', 'literals', 'reuse'):
            for phase in (1, 3, 5, 7):
                at = labels[f'shared_zero_{family}_{phase}_255'] - regions[0][0]
                self.assertEqual(regions[0][1][at:at + 54], b'\xed\xa0' * 27)

    def test_only_fast_policy_and_strict_argument_types(self):
        self.assertEqual(build(prefix_cap=255)[:2], build(prefix_cap=255, policy='fast')[:2])
        for kwargs in (dict(prefix_cap=255, policy='real'), dict(prefix_cap=255, policy='corpus'),
                       dict(prefix_cap=255.0), dict(prefix_cap=True), dict(prefix_cap=254),
                       dict(prefix_cap=256), dict(prefix_cap=255, policy=True),
                       dict(prefix_cap=255, _quota_hook=lambda *_: None)):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                build(**kwargs)

    def test_other_maximum_entrypoints_still_reject_255(self):
        for shared in (False, True):
            with self.subTest(shared=shared), self.assertRaises(ValueError):
                maximum(prefix_cap=255, shared_prefixes=shared)
        with self.assertRaises(ValueError):
            coroutine(prefix_cap=255)

    def test_service_and_code_limits_count_irq_reservations(self):
        self.assertEqual(build(prefix_cap=255, service_limit=8165)[2]['service_memory_bytes'], 8165)
        self.assertEqual(build(prefix_cap=255, irq_code_bytes=13, irq_stack_bytes=6)[2]['service_memory_bytes'], 8184)
        self.assertEqual(build(prefix_cap=255, irq_code_bytes=1835)[2]['service_memory_bytes'], 10000)
        self.assertEqual(build(prefix_cap=255, core_limit=0x8000 + 8161)[2]['code_bytes'], 8161)
        for kwargs in (dict(service_limit=8164), dict(irq_code_bytes=1836),
                       dict(core_limit=0x8000 + 8160), dict(service_limit=10001),
                       dict(irq_stack_bytes=-1), dict(irq_code_bytes=True), dict(core=True)):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                build(prefix_cap=255, **kwargs)

    def test_all_original_61_branches_relocate_with_valid_jr_operands(self):
        for origin in (0x8000, 0x9103, 0x0800, 0x0703):
            regions, labels, meta = build(prefix_cap=255, core=origin)
            self.assertEqual(meta['conditional_branch_site_count'], 61)
            self.assertEqual(len(meta['conditional_branch_sites']), 61)
            for row in meta['conditional_branch_sites']:
                with self.subTest(origin=origin, site=row['baseline_offset']):
                    at = row['address'] - origin
                    operand = regions[0][1][at + 1]
                    displacement = operand - 256 if operand >= 128 else operand
                    self.assertEqual(regions[0][1][at], {0xc2: 0x20, 0xca: 0x28, 0xd2: 0x30, 0xda: 0x38}[row['opcode']])
                    self.assertEqual(row['address'] + 2 + displacement, labels[row['target']])
                    self.assertEqual(displacement, row['final_displacement'])

    def test_cli_selects_only_qualified_path_and_exports_exact_bytes(self):
        from zx0.__main__ import main
        def run(arguments):
            output = io.StringIO()
            with patch.object(sys, 'argv', ['zx0', 'build'] + arguments), \
                    contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                try:
                    main()
                except SystemExit as error:
                    return error.code, output.getvalue()
            return 0, output.getvalue()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            for policy in ([], ['--branch-policy', 'fast']):
                code, message = run(['--variant', 'maximum-branches', '--prefix-cap', '255',
                                     '--output', temporary] + policy)
                self.assertEqual(code, 0, message)
                rebuilt = []
                text = (destination / 'decoder.asm').read_text()
                for line in text.splitlines():
                    if line.startswith('org '):
                        rebuilt.append((int(line[5:], 16), bytearray()))
                    elif line.startswith('db '):
                        rebuilt[-1][1].extend(int(value[1:], 16) for value in line[3:].split(','))
                self.assertEqual([(at, bytes(blob)) for at, blob in rebuilt], build(prefix_cap=255)[0])
                self.assertIn('initializ', text.lower())
            for flags in (['--variant', 'maximum'], ['--variant', 'maximum', '--shared-prefixes'],
                          ['--variant', 'maximum-coroutine'],
                          ['--variant', 'maximum-branches', '--branch-policy', 'real'],
                          ['--variant', 'maximum-branches', '--branch-policy', 'corpus'],
                          ['--variant', 'maximum-branches', '--shared-prefixes'],
                          ['--variant', 'maximum-branches', '--prefix', '0x7000'],
                          ['--variant', 'maximum-branches', '--service-limit', '8164']):
                code, message = run(['--prefix-cap', '255', '--output', temporary] + flags)
                self.assertEqual(code, 2, (flags, message))


if __name__ == '__main__':
    unittest.main()
