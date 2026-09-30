"""Execute every COPY/FILL suffix length across Spectrum address boundaries."""
import unittest
from collections import Counter
import numpy as np
from benchmark_compact_screen import NativeCPU, STACK, STOP
from build_zxv_trd import spectrum_bitmap_offset
from probe_compiled_row_output import routines, COMPACT, TABLE, select_row


class CompiledRowTests(unittest.TestCase):
    def test_all_suffixes_both_screens_and_row_boundaries(self):
        stub, labels, listing = routines()
        checked = Counter()
        for target in (5,7):
            for y in (12,31,32,63,64,83):
                for kind in ('copy','pattern','solid'):
                    for n in range(1,33):
                        c=NativeCPU(b'',b'');c.guarding=False;c.port_7ffd=0x17
                        def install(at,blob):
                            for i,v in enumerate(blob):c.write8(at+i,v)
                        install(0x9000,stub)
                        tables=bytes(range(256))+bytes(255-i for i in range(256))
                        install(TABLE,tables);install(COMPACT,bytes(range(32)))
                        x=32-n;phase=n&1;base=0x4000 if target==5 else 0xc000
                        c.set_de(base+spectrum_bitmap_offset(x,y*2)+256*phase)
                        c.set_hl(COMPACT+x)
                        if kind=='copy':c.b=(TABLE>>8)+phase
                        elif kind=='pattern':c.b=0xa6;c.c=0x59;c.a=c.c if phase else c.b
                        else:c.a=0x37
                        c.pc=labels[kind,n];c.sp=STACK;c.push(STOP);start=c.tstates
                        while c.pc!=STOP:
                            pc=c.pc;before=c.tstates;c.step()
                            self.assertEqual(c.tstates-before,listing[pc]['tstates'])
                        self.assertEqual(c.tstates-start,{'copy':51,'pattern':26,'solid':22}[kind]*n+10)
                        expected=bytearray(6144)
                        for column in range(x,32):
                            top,bottom=((column,255-column) if kind=='copy' else
                                        (0xa6,0x59) if kind=='pattern' else (0x37,0x37))
                            expected[spectrum_bitmap_offset(column,y*2)]=top
                            expected[spectrum_bitmap_offset(column,y*2+1)]=bottom
                        self.assertEqual(c.banks[target][:6144],expected)
                        self.assertEqual(c.banks[12-target][:6144],bytes(6144))
                        self.assertEqual(c.sp,STACK)
                        checked[kind]+=1
        self.assertEqual(sum(checked.values()),1152)

    def test_unchanged_row_emits_no_commands(self):
        self.assertEqual(select_row(np.arange(32,dtype=np.uint8),np.zeros(32,dtype=bool),bytes(512)),[])


if __name__=='__main__':unittest.main()
