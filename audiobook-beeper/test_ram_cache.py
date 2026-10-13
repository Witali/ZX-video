"""Execute the real Z80 RAM detector/cache with coherent physical-bank aliases."""
import ast
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from z80 import Z80Machine

STATE=0x5b70


from ram_machine import MemoryMachine


class RamCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[1]/'.tmp';root.mkdir(exist_ok=True)
        cls.temporary=tempfile.TemporaryDirectory(dir=root,prefix='ram-cache-')
        out=Path(cls.temporary.name)
        (out/'ram-cache.asm').write_bytes(Path(__file__).with_name('ram-cache.asm').read_bytes())
        (out/'harness.asm').write_text('        ORG 0xB800\n        INCLUDE "ram-cache.asm"\n',encoding='ascii')
        r=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=cache.bin','-s','.*','harness.asm'],cwd=out,capture_output=True,text=True)
        if r.returncode:raise AssertionError(r.stdout+r.stderr)
        cls.labels=next(ast.literal_eval(x) for x in r.stdout.splitlines() if x.startswith('{'))
        cls.code=(out/'cache.bin').read_bytes()
        assert len(cls.code)<=2048

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def machine(self,kind,**options):return MemoryMachine(kind,self.code,self.labels,**options)

    def test_detects_every_model_without_lock_or_destructive_alias_probe(self):
        for kind,mode,pages in [('128',0,0),('scorpion',1,8),('pentagon512',2,24),('pentagon1024',3,56)]:
            with self.subTest(kind=kind):
                m=self.machine(kind);original=[b[0] for b in m.banks]
                m.call('cache_detect')
                self.assertEqual((m.read(STATE+2),m.read(STATE+3)),(mode,pages))
                self.assertEqual([b[0] for b in m.banks],original)
                self.assertFalse(m.locked)
                self.assertEqual(m.selected,0)
                self.assertEqual(set(m.page_writes),set(range(pages+8)) if pages else {0})

    def test_mirrored_expansion_cannot_inflate_capacity(self):
        m=self.machine('pentagon512',actual_pages=16)
        original=[b[0] for b in m.banks]
        m.call('cache_detect')
        self.assertEqual(m.read(STATE+3),8)
        self.assertEqual([b[0] for b in m.banks],original)
        self.assertFalse(m.locked)

    def test_fill_all_extended_pages_and_stop_at_disk_eof(self):
        for kind,pages in [('scorpion',8),('pentagon512',24),('pentagon1024',56)]:
            with self.subTest(kind=kind):
                m=self.machine(kind);m.call('cache_detect')
                count=min(pages*64,2560-27)
                m.call('cache_prefetch',hl=27,de=2560)
                self.assertEqual(m.word(STATE+4),27)
                self.assertEqual(m.word(STATE+6),count)
                self.assertEqual(m.physical_reads,list(range(27,27+count)))
                for slot in range(count):
                    page=8+slot//64;offset=slot%64*256
                    self.assertEqual(m.banks[page][offset:offset+256],m.sector(27+slot))
                self.assertFalse(m.locked)

    def test_cached_sector_copies_and_rom_misses_preserve_state(self):
        m=self.machine('pentagon1024');m.call('cache_detect')
        m.call('cache_prefetch',hl=100,de=175)
        before=bytes(m.read(STATE+i) for i in range(16))
        for sector,destination,page in [(100,0xc000,6),(163,0xf000,1),(164,0x5b00,0),(174,0x9000,0),(175,0xc000,4)]:
            with self.subTest(sector=sector):
                reads=len(m.physical_reads)
                m.call('cache_read_sector',a=24+page,hl=destination,de=(sector//16)*256+sector%16)
                expected=bytearray(m.sector(sector))
                if destination==0x5b00:expected[0x70:0x80]=before
                self.assertEqual(bytes(m.read(destination+i) for i in range(256)),expected)
                self.assertEqual(bytes(m.read(STATE+i) for i in range(16)),before)
                self.assertEqual(len(m.physical_reads)-reads,int(sector==175))
        self.assertFalse(m.locked)

    def test_progress_covers_loading_plus_full_prefetch(self):
        m=self.machine('pentagon1024');m.call('cache_detect')
        end=0x5b70+12
        m.write(self.labels['cache_disk_end'],0xdc)
        m.write(self.labels['cache_disk_end']+1,5) # disk EOF1500
        m.call('cache_begin_progress',hl=56,de=564)
        self.assertEqual(m.word(end),1444)
        for _ in range(508):m.call('cache_progress')
        self.assertEqual(m.read(STATE+8),11)
        m.call('cache_prefetch',hl=564,de=1500)
        self.assertEqual(m.read(STATE+8),32)
        self.assertEqual(bytes(m.banks[7][0x1ac0:0x1ae0]),bytes([0x24]*32))

    def test_consumed_cache_at_eof_is_invalidated_without_more_reads(self):
        m=self.machine('scorpion');m.call('cache_detect')
        m.call('cache_prefetch',hl=100,de=612)
        self.assertEqual(m.word(STATE+6),512)
        before=len(m.physical_reads)
        m.call('cache_prefetch',hl=612,de=612)
        self.assertEqual(m.word(STATE+6),0)
        self.assertEqual(len(m.physical_reads),before)


if __name__=='__main__':unittest.main()
