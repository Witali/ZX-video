"""Native bitmap host and real full-flags Z80 mode, frontier and timing tests."""
import struct
import unittest
import numpy as np
from build_zxv_trd import spectrum_bitmap_offset
from probe_cell_codebook import mask
from verify_cell_codebook_z80 import Harness,independent
import native_lineart as line
import native_cell_codebook as codec
import cell_codebook_z80 as native


def blank():
    result = np.zeros(6912,np.uint8);result[6144:] = 7;result[6144:6240] = result[-96:] = 1
    return result


class NativeTests(unittest.TestCase):
    def test_native_raster_rows_banks_and_interrupts_have_exact_cost(self):
        rng=np.random.default_rng(71)
        payload=rng.integers(0,256,5184,np.uint8).tobytes()
        before={7:bytes([165])*6912,5:bytes([60])*6912}
        for inline in (False,True):
            for target in (5,7):
                expected={k:bytearray(v) for k,v in before.items()}
                array=np.frombuffer(expected[target],np.uint8)
                array[line.OFFSETS[24:168]]=np.frombuffer(payload[:4608],np.uint8).reshape(144,32)
                expected[target][6240:6816]=payload[4608:]
                expected={k:bytes(v) for k,v in expected.items()}
                h=Harness(bytes(2048),bytes(512),before[7]+before[5],True,
                    front_reuse=True,fast_masks=True,partial_rows=True,inline_cells=inline,native_bitmap=True)
                high=0xc0 if target==7 else 0x40
                measured=h.run('draw_raster',payload,0x6200,high)
                self.assertEqual(measured['tstates'],122020)
                self.assertTrue(all(bytes(h.c.banks[k][:6912])==v for k,v in expected.items()))
                independent(h,payload,0x6200,high,before,expected,measured['tstates'],
                    interrupts=True,entry_name='draw_raster')

    def test_narrow_original_strokes_have_no_parallel_added_contours(self):
        image=np.zeros((192,256,3),np.uint8);image[24:168]=205
        for width in (1,2):
            source=image.copy();source[55:105,80:80+width]=0
            actual=line.pixels(line.encode(source));black=np.all(actual[24:168]==0,-1)
            expected=np.zeros((144,256),bool);expected[31:81,80:80+width]=True
            np.testing.assert_array_equal(black,expected)
            source=image.copy();source[80:80+width,55:105]=0
            actual=line.pixels(line.encode(source));black=np.all(actual[24:168]==0,-1)
            expected=np.zeros((144,256),bool);expected[56:56+width,55:105]=True
            np.testing.assert_array_equal(black,expected)
        source=image.copy();source[55:105,80]=[205,0,0]
        np.testing.assert_array_equal(line.pixels(line.encode(source)),source)
        source=image.copy();source[48:128,64:144]=0;source[55:105,80]=205
        # The large rectangle still gets an object contour. Its interior
        # white stroke and neighbouring black pixels must remain exact.
        np.testing.assert_array_equal(line.pixels(line.encode(source))[60:100,76:85],source[60:100,76:85])
        source=image.copy();source[55:105,80]=source[55:105,83]=[90,90,90]
        actual=line.pixels(line.encode(source))
        self.assertTrue((actual[60:100,81:83] == 205).all())

    def test_native_one_pixel_is_not_a_two_by_two_sample(self):
        state = blank();state[spectrum_bitmap_offset(3,35)] = 0x20
        actual = line.pixels(state)
        self.assertEqual(np.count_nonzero(actual[32:40,24:32].max(-1)),1)
        self.assertTrue((actual[35,26] == 205).all())

    def test_native_colour_lines_and_source_black_are_actual_pixels(self):
        image = np.zeros((192,256,3),np.uint8);image[24:168] = [190,185,165]
        image[50:125,75:160] = [83,42,10];image[64:72,94:103] = 245
        image[96:99,105:145] = [45,25,15]
        state = line.encode(image);output = line.pixels(state);lines = line.source_lines(image)
        self.assertTrue(lines.any());self.assertFalse((output[lines] != 0).any())
        self.assertFalse(line.unpack(state)[0][:24].any());self.assertEqual(len(state),6912)
        old = line.pixels(line.encode(image,dark_fills=False))
        self.assertTrue((np.mean((output-image)**2,-1) <= np.mean((old-image)**2,-1)).all())

    def test_host_exact_history_book_front_literal_and_single_pixel_row(self):
        rng = np.random.default_rng(32);frames = np.array([blank() for _ in range(5)])
        frames[:,line.OFFSETS[24:168]] = rng.integers(0,256,(5,144,32),np.uint8)
        frames[1,:6144] = frames[0,:6144]
        frames[3,:6144] = frames[1,:6144]
        frames[3,spectrum_bitmap_offset(7,83)] ^= 1
        result = codec.representation(frames,0,5)
        self.assertTrue(result['dynamic_proof']['full_native_screens_exact'])
        self.assertGreater(sum(r['candidate_literal_cells'] for r in result['details']),0)
        self.assertTrue(any(r['raster_packet'] for r in result['details']))
        self.assertGreater(sum(r['front_cells'] for r in result['details']),0)
        self.assertGreater(sum(r['single_row_cells'] for r in result['details']),0)
        with self.assertRaises(ValueError):codec.decode_check(result['raw']+b'\0',frames,0,5)

    def test_all_native_rows_modes_inline_banks_and_exact_instruction_costs(self):
        table = bytes([255])*2048;row_table = bytes([165])*512
        for inline in (False,True):
            for row in range(8):
                for target in (5,7):
                    count = 9;modes=bytearray((count+3)//4);data=bytearray()
                    before={target:bytes([165])*6144+bytes(768),12-target:bytes([60])*6144+bytes(768)}
                    expected={k:bytearray(v) for k,v in before.items()}
                    for cell in range(count):
                        mode=cell%4;modes[cell//4] |= mode << ((cell%4)*2)
                        if mode==0:values=bytes([cell+1])*8;data += values
                        elif mode==1:values=bytes([255])*8;data += b'\0'
                        elif mode==2:values=bytes([60])*8
                        else:
                            values=bytearray([165])*8;values[row]=129;data += bytes([row,129])
                        for r,value in enumerate(values):expected[target][spectrum_bitmap_offset(cell,24+r)]=value
                    payload=mask(list(range(count)),576)+bytes(72)+modes+data
                    h=Harness(table,row_table,before[7]+before[5],True,front_reuse=True,
                        fast_masks=True,partial_rows=True,inline_cells=inline,native_bitmap=True)
                    high=0xc0 if target==7 else 0x40
                    measured=h.run('draw',payload,0x6441,high)
                    expected={k:bytes(v) for k,v in expected.items()}
                    self.assertTrue(all(bytes(h.c.banks[k][:6912]) == v for k,v in expected.items()))
                    independent(h,payload,0x6441,high,before,expected,measured['tstates'])
        baseline=native.build(dictionary=True,front_reuse=True,fast_masks=True,partial_rows=True)[2]
        current=native.build(dictionary=True,front_reuse=True,fast_masks=True,partial_rows=True,native_bitmap=True)[2]
        def cost(meta,stage):return sum(r['tstates'] for r in meta['instruction_listing'] if r['stage']==stage)
        self.assertEqual((cost(baseline,'literal'),cost(current,'literal')),(231,188))
        self.assertEqual((cost(baseline,'partial_row'),cost(current,'partial_row')),(93,53))

    def test_maximum_native_packet_and_interrupt_safe_complete_write(self):
        before={7:bytes(6912),5:bytes(6912)};table=bytes(2048);rows=bytes(512)
        values=bytes(range(1,9));payload=bytes([255])*144+bytes(144)+values*576+bytes([71])*576
        self.assertEqual(len(payload),codec.MAX_PACKET)
        expected={k:bytearray(v) for k,v in before.items()}
        for cell in range(576):
            y,x=divmod(cell,32)
            for row,value in enumerate(values):expected[7][spectrum_bitmap_offset(x,(y+3)*8+row)]=value
            expected[7][6240+cell]=71
        expected={k:bytes(v) for k,v in expected.items()}
        h=Harness(table,rows,before[7]+before[5],True,front_reuse=True,fast_masks=True,
            partial_rows=True,inline_cells=True,native_bitmap=True)
        measured=h.run('draw',payload,0x6200,0xc0)
        independent(h,payload,0x6200,0xc0,before,expected,measured['tstates'],interrupts=True)


if __name__ == '__main__':unittest.main()
