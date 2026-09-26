"""Successful direct reads preserve IM2; full/error paths still restore it."""
import unittest
from benchmark_fap3_disk import run
from benchmark_context_huffman import word
from test_fap3_disk import DiskCPU,install
import fap3_disk_z80 as disk
from fast_return_irq import install as patch


class FastReturnTests(unittest.TestCase):
    def test_direct_full_and_short_read_paths(self):
        options=dict(fast_disk=True,cached_seek=True,interleaved=True,irq_safe_paging=True,poison_irq=True)
        for case in ({},{'cached':255},{'cached':2},{'sector':15},
                     {'region':3,'high':255},{'short':True},{'cached':2,'short':True}):
            with self.subTest(case=case):
                old=run(**options,**case);new=run(**options,**case,fast_return_irq=True)
                delta=-58 if new['direct_calls'] and not new['fallback_calls'] else 0
                self.assertEqual(new['tstates']-old['tstates'],delta)
                self.assertEqual(new['restore_calls'],new['full_calls'])
                for key in ('code_bytes','full_calls','direct_calls','fallback_calls'):
                    self.assertEqual(new[key],old[key])

    def test_success_path_never_masks_irq(self):
        code,labels,rows=disk.build_disk(49,7,fast_disk=True,cached_seek=True,interleaved=True)
        c=DiskCPU(b'',b'');install(c,disk.DISK,code)
        m=dict(fast_disk=True,required_trdos_sha256=disk.TRDOS_503_SHA256,
               disk_labels=labels,slot_queue_instruction_listing=rows)
        report=patch(c.read8,lambda a,b:install(c,a,b),m)
        c.pc=labels['fast_disk_return'];c.set_hl(0xc100);word(c,0x5d00,0xc000)
        c.i=0xbe;c.im=2;c.iff1=True;word(c,0xbdbe,0xbd80)
        while c.pc!=report['accepted_sector']:
            c.step();self.assertTrue(c.iff1)
            self.assertEqual((c.i,c.im,word(c,0xbdbe)),(0xbe,2,0xbd80))
        self.assertEqual(c.tstates,57)
        self.assertEqual(report['previous_success_to_cursor_tstates'],115)

    def test_refuses_unknown_rom_and_changed_code(self):
        code,l,rows=disk.build_disk(49,7,fast_disk=True,cached_seek=True,interleaved=True)
        c=DiskCPU(b'',b'');install(c,disk.DISK,code)
        m=dict(fast_disk=True,required_trdos_sha256='unknown',disk_labels=l,slot_queue_instruction_listing=rows)
        put=lambda a,b:install(c,a,b)
        with self.assertRaises(ValueError):patch(c.read8,put,m)
        m['required_trdos_sha256']=disk.TRDOS_503_SHA256;c.write8(l['disk_finish'],0)
        with self.assertRaises(ValueError):patch(c.read8,put,m)


if __name__=='__main__':unittest.main()
