import unittest

import numpy as np

import five_level_dither as five
import spatial_dither as spatial


class SpatialDitherTests(unittest.TestCase):
    def test_metric_identical_edges_have_zero_error(self):
        from probe_spatial_dither import metrics
        image = np.zeros((96,128,3),dtype=np.uint8)
        image[:,::2] = 255
        measured, _ = metrics(image.repeat(2,0).repeat(2,1),image)
        for name in ('native_mse','logical_2x2_mse','aligned_4x4_mse','sliding_4x4_mse','gradient_error'):
            self.assertEqual(measured[name],0)

    def test_eight_uniform_coverages_and_static_phase(self):
        for count in spatial.DOT_COUNTS:
            projected = np.full((96, 128), count/16)
            bits = spatial.ordered(projected)
            self.assertTrue(np.all(bits.reshape(48, 4, 64, 4).sum(axis=(1, 3)) == count))
            np.testing.assert_array_equal(bits, spatial.ordered(projected))
        self.assertEqual(sorted(spatial.BAYER.flatten()), list(range(16)))

    def test_adaptive_output_retains_all_eight_uniform_bars(self):
        row = np.repeat(spatial.DOT_COUNTS.astype(np.float64)/16*255,16)
        image = np.broadcast_to(row[None,:,None],(96,128,3))
        old, new, selected = spatial.quantize(image,bytes(3072)+bytes([71])*768)
        average = spatial.pool(spatial.rgb(spatial.decode(new),new.attrs),4)
        np.testing.assert_allclose(average,spatial.pool(image,2))
        self.assertTrue(selected.any())
        self.assertNotEqual(old,new)

    def test_scalar_cell_decoder_matches_existing_five_expander(self):
        # Every possible four-sample row is represented, not just solid tiles.
        words = np.arange(96*32).reshape(96,32) % 625
        levels = ((words[..., None] // [125,25,5,1]) % 5).astype(np.uint8).reshape(96,128)
        attrs = bytes([71])*768
        frame = spatial.make_frame(levels, attrs, spatial.pattern(levels), np.zeros((48,64), bool))
        bitmap, _ = five.expand(five.pack_levels(levels)+attrs)
        expected = np.zeros((192,256), dtype=np.uint8)
        for y in range(192):
            at = spatial.video.base.spectrum_bitmap_offset(0,y)
            expected[y] = np.unpackbits(np.frombuffer(bitmap[at:at+32], dtype=np.uint8))
        np.testing.assert_array_equal(spatial.decode(frame), expected)

    def test_grid_edges_and_exact_five_tones_retained(self):
        y, x = np.indices((96,128))
        for values in (np.where((x+y) % 2, 255, 0), np.where(x == 63, 255, 0), np.full((96,128), 127.5)):
            image = np.repeat(values[...,None],3,2)
            old, new, selected = spatial.quantize(image, bytes(3072)+bytes([71])*768)
            self.assertFalse(selected.any())
            self.assertEqual(old, new)

    def test_orientation_and_bright_preserved(self):
        image = np.full((96,128,3),80)
        a = spatial.quantize(image, bytes(3072)+bytes([71])*768)
        b = spatial.quantize(image, bytes(3072)+bytes([120])*768)
        self.assertEqual(a[:2], b[:2])
        self.assertTrue(all(attr & 64 and not attr & 128 for attr in a[1].attrs))
        with self.assertRaises(ValueError): spatial.quantize(image, bytes(3072)+bytes([199])*768)

    def test_delta_modes_attributes_roundtrip_and_reject_damage(self):
        rng = np.random.default_rng(430)
        previous = None
        for step in range(4):
            levels = rng.integers(0,5,(96,128),dtype=np.uint8)
            bits = rng.integers(0,2,(192,256),dtype=np.uint8)
            attrs = bytes([7+64*(step % 2)])*768
            selected = rng.random((48,64)) < .05
            frame = spatial.make_frame(levels,attrs,bits,selected)
            wanted = np.where(selected.reshape(24,2,32,2).any(axis=(1,3)).repeat(8,0).repeat(8,1),bits,spatial.pattern(levels))
            np.testing.assert_array_equal(spatial.decode(frame),wanted)
            if previous is not None:
                packet = spatial.encode_delta(previous,frame,escapes=True)
                self.assertEqual(spatial.decode_delta(previous,packet,escapes=True),frame)
                for bad in (packet[:-1],packet+b'\0',packet[:191]):
                    with self.assertRaises(ValueError): spatial.decode_delta(previous,bad,escapes=True)
            previous = frame
        baseline = spatial.make_frame(levels,attrs,spatial.pattern(levels),np.zeros((48,64),bool))
        packet = spatial.encode_delta(baseline,baseline,escapes=False)
        self.assertEqual(len(packet),192)
        self.assertEqual(spatial.decode_delta(baseline,packet,escapes=False),baseline)


if __name__ == '__main__': unittest.main()
