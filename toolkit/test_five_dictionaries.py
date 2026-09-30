import unittest

import numpy as np

import five_level_dither as five
import hybrid_five_level as hybrid
import probe_five_cell_dictionary as cell
import probe_five_row_dictionary as row


class DictionaryTests(unittest.TestCase):
    def test_native_reference_uses_byte_columns(self):
        from audit_five_row_tables import expected_screen, base
        state = bytearray(3840); state[12*32+31] = 1
        tables = bytearray(512); tables[1] = 128
        bitmap, _ = expected_screen(state,tables)
        self.assertEqual(bitmap[base.spectrum_bitmap_offset(31,24)],128)
        self.assertEqual(sum(bitmap),128)

    def test_all_625_rows_keep_phase_and_inverse(self):
        for word in range(625):
            data = sum(word << shift for shift in (30,20,10,0)).to_bytes(5,'big')
            native = bytes([five.TOP[word],five.BOTTOM[word]])*4
            self.assertEqual(cell.unpack_cell(data),native)
            self.assertEqual(cell.pack_cell(native),data)
            self.assertEqual(row.rows(data),(word,)*4)
        with self.assertRaises(ValueError): cell.pack_cell(bytes([1,0])*4)

    def test_mixed_hits_escapes_and_attribute_xors(self):
        levels = np.zeros((96,128),dtype=np.uint8)
        before = hybrid.from_five(five.pack_levels(levels)+bytes([71])*768,adaptive=False)
        rng = np.random.default_rng(725)
        levels[:] = rng.integers(0,5,levels.shape,dtype=np.uint8)
        after = hybrid.from_five(five.pack_levels(levels)+bytes([7])*768,adaptive=False)
        packet = hybrid.encode_delta(before,after,policy='five')
        cells = cell.parts(packet)[1]
        choices = list(dict.fromkeys(cells))[:128]
        dictionary = [cell.unpack_cell(c) for c in choices]
        packed = cell.encode_packet(packet,{c:i for i,c in enumerate(choices)})
        self.assertEqual(cell.decode_packet(packed,dictionary),packet)
        words = list(dict.fromkeys(w for c in cells for w in row.rows(c)))[:256]
        dictionary2 = [bytes([five.TOP[w],five.BOTTOM[w]]) for w in words]
        packed2 = row.encode_packet(packet,{w:i for i,w in enumerate(words)})
        self.assertEqual(row.decode_packet(packed2,dictionary2),packet)
        for decoder,encoded,table in ((cell.decode_packet,packed,dictionary),(row.decode_packet,packed2,dictionary2)):
            for damaged in (encoded[:-1],encoded+b'\0',encoded[:191]):
                with self.assertRaises(ValueError): decoder(damaged,table)

    def test_no_change_and_index_bounds(self):
        for codec in (cell,row):
            self.assertEqual(codec.decode_packet(codec.encode_packet(bytes(192),{}),[]),bytes(192))
            prefix = bytes(96)+bytes([128])+bytes(95)
            bad = prefix+bytes([128,255])*(1 if codec is cell else 3)
            with self.assertRaises(ValueError): codec.decode_packet(bad,[])


if __name__ == '__main__': unittest.main()
