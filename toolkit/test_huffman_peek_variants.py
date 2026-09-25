"""Independent value/bit-position checks for both prefix-peek experiments."""
import unittest
from benchmark_prefix_huffman import Harness,INPUT
from probe_motion_entropy import codes_for
from test_prefix_huffman_z80 import candidate
import test_context_huffman_z80 as existing


class HuffmanPeekVariantsTests(unittest.TestCase):
    def test_every_code_at_all_offsets_and_nonzero_lookahead(self):
        tables,mapping=candidate()
        for options in (dict(single_byte=True),dict(carry_huffman=True)):
            h=Harness(tables,mapping,**options)
            for context,table in enumerate(tables):
                pair=(1,0) if context==len(tables)-1 else (0,mapping.index(context))
                for value,(code,length) in enumerate(codes_for(255,table)):
                    if not length:continue
                    for offset in range(8):
                        encoded=(code << ((-offset-length)%8)).to_bytes((offset+length+7)//8,'big')
                        h.begin(encoded);h.cpu.write8(INPUT+len(encoded),255)
                        h.cpu.write8(h.labels['bit_page'],h.bit_base+offset)
                        h.run([pair],bytes([value]))
                        self.assertEqual(h.position(),offset+length)

    def test_short_codes_all_lookahead_values_and_real_read_count(self):
        tables=[bytes([1,2,2]+[0]*253)]*2
        for options in (dict(single_byte=True),dict(carry_huffman=True)):
            h=Harness(tables,bytes(256),**options)
            base_read=h.cpu.read8;reads=[]
            def read(address):
                if h.cpu.guarding and INPUT<=address<INPUT+16384:reads.append(address)
                return base_read(address)
            h.cpu.read8=read
            for value,(code,length) in enumerate(codes_for(255,tables[0])[:3]):
                for offset in range(8):
                    encoded=(code << ((-offset-length)%8)).to_bytes((offset+length+7)//8,'big')
                    for lookahead in range(256):
                        h.begin(encoded);h.cpu.write8(INPUT+len(encoded),lookahead)
                        h.cpu.write8(h.labels['bit_page'],h.bit_base+offset);reads.clear()
                        h.run([(0,0)],bytes([value]))
                        self.assertEqual(len(reads),1 if options.get('single_byte') and offset+length<=7 else 2)

    def test_ay_irq_at_each_instruction(self):
        tables,mapping=candidate()
        for options in (dict(single_byte=True),dict(carry_huffman=True)):
            existing.ContextHuffmanZ80Tests().exercise_ay_irq(tables,mapping,
                lambda:Harness(tables,mapping,**options),'benchmark_prefix_huffman.PAIRS')

    def test_exclusive_variants(self):
        with self.assertRaises(ValueError):
            Harness([bytes([8]*256)]*2,bytes(256),single_byte=True,carry_huffman=True)


if __name__=='__main__':unittest.main()
