"""Same-cylinder read geometry, sentinels, exact RAM cycles and ROM identity."""
import gzip
import hashlib
import json
from pathlib import Path
import unittest

from benchmark_fap3_disk import run
import fap3_disk_z80 as disk
from z80 import Z80Machine


def timings():
    rows={}
    for name,options in (
        ('same_track',{}),('side_one',dict(cached=2)),
        ('side_zero',dict(track=2,cached=3)),('cylinder',dict(track=4,cached=3)),
        ('head_reload',dict(cached=254)),('cold',dict(cached=255)),
        ('side_short_retry',dict(cached=2,short=True))):
        before=run(fast_disk=True,cached_seek=True,**options)
        after=run(fast_disk=True,cached_seek=True,side_only_seek=True,**options)
        rows[name]=dict(before=before,after=after,delta_tstates=after['tstates']-before['tstates'])
    return rows


class SideOnlySeekTests(unittest.TestCase):
    def test_default_bytes(self):
        path=Path(__file__).with_name('direct_lzsa2_header_evidence')/'window-ZX-video-front_part07.json.gz'
        m=json.loads(gzip.decompress(path.read_bytes()))
        code,labels,_=disk.build_cached_seek(m['disk_labels'])
        self.assertEqual(code.hex(),'e57a32f55c32ea602100bd22bebd3ae260e60111eb1fcaac9a11f61f21bb9ae5d53ebeed47ed5efbc32f3dfb3af65c5f160021fa5c197ee603473ae260cb3f21db9ae521443ee5fbc32f3dfb2180bd22bebd3e8432fe5ce1c9')
        self.assertEqual(labels,m['seek_labels'])
        self.assertEqual(labels['end'],0x9ae9)

    def test_geometry_and_retry(self):
        for track in range(160):
            for drive in range(4):
                for region in range(4):
                    run(fast_disk=True,cached_seek=True,side_only_seek=True,
                        track=track,cached=track^1,drive=drive,region=region,high=255,
                        sector=15,interleaved=True,irq_safe_paging=True,fast_return_irq=True)
        for cached in (2,4,254,255):
            run(fast_disk=True,cached_seek=True,side_only_seek=True,cached=cached,
                short=True,poison_irq=True,fast_return_irq=True)

    def test_absolute_cpu_counts(self):
        r=timings()
        self.assertEqual((r['same_track']['before']['tstates'],r['same_track']['after']['tstates']),(896,896))
        self.assertEqual((r['side_one']['before']['tstates'],r['side_one']['after']['tstates']),(1351,1959))
        self.assertEqual(r['side_zero']['delta_tstates'],608)
        self.assertEqual(r['cylinder']['delta_tstates'],65)
        self.assertEqual(r['head_reload']['delta_tstates'],65)
        self.assertEqual(r['cold']['delta_tstates'],0)
        self.assertEqual(r['side_short_retry']['delta_tstates'],608)

    def test_full_flags_and_minimum_delay(self):
        _,d,_=disk.build_disk(49,7,fast_disk=True,cached_seek=True)
        code,z,_=disk.build_cached_seek(d,side_only=True)
        self.assertEqual(len(code),107)
        # Execute the complete helper on an independent core. The trampoline
        # and ROM services are RET stubs; every AF value is poisoned on return.
        for cached in (2,4,254,255):
            for flags in range(256):
                m=Z80Machine();m.set_memory_block(disk.CACHED_SEEK,code)
                for at in (0x3d2f,0x1ff6,0x3e44):m.memory[at]=0xc9
                m.memory[d['cached_track']]=cached;m.memory[d['disk_position']+1]=3
                m.memory[0x5cfe]=0x80;m.memory[0x5cf6]=2;m.memory[0x5cfc]=0x82
                m.hl=0xc300;m.de=0x0301;m.sp=0x9bfe;m.memory[0x9bfe:0x9c00]=b'\x00\x5f'
                m.pc=disk.CACHED_SEEK;m.ticks_to_stop=10000
                for pc in (z['seek_side_return'],z['side_settle'],z['restore_irq'],0x3e44,0x5f00):m.set_breakpoint(pc)
                seen=[];delay=None
                while m.pc!=0x5f00:
                    self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
                    seen.append(m.pc)
                    if m.pc==z['seek_side_return']:
                        m.af=0x8100|flags;m.bc=0xc33c;m.de=0xdead;m.hl=0xa55a
                    if m.pc==z['side_settle']:delay=m.ticks_to_stop
                    if m.pc==z['restore_irq'] and delay is not None:self.assertEqual(delay-m.ticks_to_stop,717)
                    if m.pc==0x3e44:self.assertEqual((m.a,m.b),(1,2))
                    m.clear_breakpoint(m.pc)
                self.assertEqual(m.hl,0xc300);self.assertEqual(m.sp,0x9c00)
                self.assertEqual(m.memory[0x5cf5],3);self.assertEqual(m.memory[d['cached_track']],3)
                self.assertEqual(m.memory[0xbdbe:0xbdc0],b'\x80\xbd')
                self.assertEqual(0x3e44 in seen,cached!=2)
                self.assertEqual(m.memory[0x5cfe],0x80 if cached==2 else 0x84)

    def test_pinned_rom_entries(self):
        rom=Path('tools/fuse-1.9.0-sdl/roms/trdos.rom').read_bytes()
        self.assertEqual(hashlib.sha256(rom).hexdigest(),disk.TRDOS_503_SHA256)
        self.assertEqual(rom[0x1feb:0x2000],bytes.fromhex('3a165df63c32165dd3ffc93a165de66f18f3f33ef4'))
        self.assertEqual(rom[0x3e44:0x3e4c],bytes.fromhex('d37f78f618c39a3d'))


if __name__=='__main__':unittest.main()
