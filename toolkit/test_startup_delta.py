"""Check actual Z80 table restoration, memory bounds and absolute T-states."""
import random
import unittest
from build_zxv_trd import MiniAssembler
from fap3_disk_z80 import emit_table_delta
from test_fap3_disk import DiskCPU,install
from probe_startup_tables import difference


class StartupDeltaTests(unittest.TestCase):
    def test_whole_bank_exact_and_constant_cost(self):
        rng=random.Random(67)
        for data in (bytes(16384),bytes(range(256))*64,rng.randbytes(16384)):
            a=MiniAssembler(0x6000);emit_table_delta(a)
            cpu=DiskCPU(b'',b'');cpu.port_7ffd=0x16;install(cpu,0x6000,a.resolve())
            cpu.banks[6][:]=difference(data);cpu.sp=0x5ff0;cpu.push(0x5e00)
            before=[bytes(b) for b in cpu.banks];cpu.pc=0x6000
            while cpu.pc!=0x5e00:cpu.step()
            self.assertEqual(bytes(cpu.banks[6]),data)
            self.assertEqual(cpu.tstates,541409)
            self.assertEqual(cpu.port_7ffd,0x16)
            self.assertTrue(all(bytes(cpu.banks[b])==before[b] for b in range(8) if b!=6))


if __name__=='__main__':unittest.main()
