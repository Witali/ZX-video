"""Instruction cost and shared-sector boundaries of the real boot path."""
import unittest
from integrated_bootstrap import Builder,INSTALL,installer
from test_fap3_disk import DiskCPU
import fap3_disk_z80 as disk


class BootstrapTests(unittest.TestCase):
    def test_overlay_exact_and_cycles(self):
        c=DiskCPU(b'',b'');c.port_7ffd=0x17;c.pc=INSTALL
        for i,v in enumerate(installer()):c.write8(INSTALL+i,v)
        data=bytes((i*71+i//256)&255 for i in range(512))
        for i,v in enumerate(data):c.write8(0xa100+i,v)
        while c.pc!=disk.DRIVER:c.step()
        self.assertEqual(c.tstates,10812)
        self.assertEqual(bytes(c.read8(0x6000+i) for i in range(512)),data)

    def test_shared_sector_offsets(self):
        b=Builder.__new__(Builder)
        for sizes in ((1,255,256),(255,2,511),(257,4097,100)):
            with self.subTest(sizes=sizes):
                sections=[dict(data=bytes([i+1])*n,compressed_bytes=n,buffer=0x4000)
                          for i,n in enumerate(sizes)]
                files,end=b.place_sections(sections,21)
                self.assertEqual(end,21+(sum(sizes)+255)//256)
                payload=files[0].data
                for i,s in enumerate(sections):
                    offset=(s['sector']-21)*256+s['source_offset']
                    self.assertEqual(payload[offset:offset+sizes[i]],bytes([i+1])*sizes[i])
                    self.assertLessEqual(s['source_offset']+sizes[i],s['sectors']*256)


if __name__=='__main__':unittest.main()
