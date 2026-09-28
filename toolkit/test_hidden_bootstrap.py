"""Check the hidden-screen fill, cost, restore contract and legacy layouts."""
import unittest

from fap3_disk_z80 import build_bootstrap
from test_fap3_disk import DiskCPU


class HiddenBootstrapTests(unittest.TestCase):
    def test_fill_changes_only_hidden_attributes_and_has_exact_cost(self):
        sections = [dict(bank=7, address=0xc000, decoded_bytes=6912,
                         buffer=0x4000, sectors=1, sector=21)]
        code, labels = build_bootstrap(sections, 22, 1, preload_sectors=0, runtime_entry=0xdb00)
        cpu = DiskCPU(code, b'')
        cpu.banks[5][:6912] = b'\x79'*6912
        cpu.banks[7][:6912] = b'\xa7'*6912
        cpu.pc = labels['hide_staging_screen']
        while cpu.pc != labels['staging_attributes_hidden']:
            cpu.step()
        self.assertEqual(cpu.tstates, 16171)
        self.assertEqual(cpu.port_7ffd, 0x17)
        self.assertEqual(bytes(cpu.banks[5][:6912]), b'\x79'*6912)
        self.assertEqual(bytes(cpu.banks[7][:6144]), b'\xa7'*6144)
        self.assertEqual(bytes(cpu.banks[7][6144:6912]), bytes(768))
        while cpu.pc != labels['boot_disk_call']:
            cpu.step()
        self.assertEqual(cpu.port_7ffd, 0x1f)

    def test_partial_shadow_restore_does_not_destroy_retained_attributes(self):
        for length in (0, 6144, 6911):
            sections = [dict(bank=7, address=0xc000, decoded_bytes=length,
                             buffer=0x4000, sectors=1, sector=21)]
            _, labels = build_bootstrap(sections, 22, 1)
            self.assertNotIn('hide_staging_screen', labels)

    def test_no_screen_staging_keeps_legacy_path(self):
        sections = [dict(bank=7, address=0xc000, decoded_bytes=6912,
                         buffer=0xa6a0, sectors=1, sector=21)]
        _, labels = build_bootstrap(sections, 22, 1)
        self.assertNotIn('hide_staging_screen', labels)


if __name__ == '__main__':
    unittest.main()
