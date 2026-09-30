"""All five levels, temporal mode switches and separate colour deltas."""
import unittest
import numpy as np

import five_level_dither as five
import hybrid_five_level as hybrid


def state(levels):
    return five.pack_levels(levels)+bytes([71])*768


class HybridFiveTests(unittest.TestCase):
    def test_all_five_levels_and_quartet_cells_roundtrip(self):
        rng = np.random.default_rng(625)
        levels = rng.integers(0, 5, (96, 128), dtype=np.uint8)
        levels[:4, :4] = np.resize([0, 1, 2, 4], (4, 4))
        levels[:4, 4:8] = np.resize([0, 2, 3, 4], (4, 4))
        source = state(levels)
        for adaptive in (False, True):
            frame = hybrid.from_five(source, adaptive=adaptive)
            restored, attrs = hybrid.decode(frame)
            np.testing.assert_array_equal(restored, levels)
            self.assertEqual(attrs, source[3840:])
            if adaptive:
                self.assertEqual(frame.modes[:2], b'\0\0')
                self.assertEqual(frame.attrs[:2], bytes([71, 120]))
                self.assertIn(1, frame.modes)

    def test_delta_keeps_attributes_independent_of_pixels(self):
        levels = np.zeros((96, 128), dtype=np.uint8)
        old = hybrid.from_five(state(levels))
        levels[12:16, :4] = np.arange(16).reshape(4, 4) % 5
        new = hybrid.from_five(state(levels), previous=old)
        packet = hybrid.encode_delta(old, new)
        self.assertEqual(packet[:96], bytes(96))
        self.assertEqual(len(packet), 192+1+5)
        self.assertEqual(hybrid.decode_delta(old, packet), new)
        for source, target in ((new, old), (old, old)):
            self.assertEqual(hybrid.decode_delta(source, hybrid.encode_delta(source, target)), target)
        bright = hybrid.Frame(bytes([7])+old.attrs[1:], old.modes, old.cells)
        packet = hybrid.encode_delta(old, bright)
        self.assertEqual(packet[96:192], bytes(96))
        self.assertEqual(len(packet), 193)
        self.assertEqual(hybrid.decode_delta(old, packet), bright)

    def test_canonical_three_modes_do_not_swap_colour_attributes(self):
        levels = np.zeros((96,128), dtype=np.uint8)
        old = hybrid.from_five(state(levels), canonical_quartets=True)
        levels[:4,:4] = 3
        levels[:4,4:8] = np.arange(16).reshape(4,4) % 5
        new = hybrid.from_five(state(levels), canonical_quartets=True, previous=old)
        self.assertEqual(new.modes[:3], bytes([2,1,0]))
        self.assertEqual(new.attrs, old.attrs)
        packet = hybrid.encode_delta(old, new, policy='canonical')
        self.assertEqual(packet[:96], bytes(96))
        self.assertEqual(hybrid.decode_delta(old, packet, policy='canonical'), new)
        np.testing.assert_array_equal(hybrid.decode(new)[0], levels)

    def test_all_radix_words_and_mode_switches(self):
        levels = np.resize(np.array([[(w//d) % 5 for d in (125, 25, 5, 1)]
                                    for w in range(625)], dtype=np.uint8), (96, 128))
        old = hybrid.from_five(state(np.zeros_like(levels)))
        new = hybrid.from_five(state(levels))
        self.assertEqual(hybrid.decode_delta(old, hybrid.encode_delta(old, new)), new)
        for policy, source, target in (
                ('four', old, old),
                ('five', hybrid.from_five(state(np.zeros_like(levels)), adaptive=False),
                 hybrid.from_five(state(levels), adaptive=False))):
            self.assertEqual(hybrid.decode_delta(source, hybrid.encode_delta(source, target, policy=policy), policy=policy), target)

    def test_invalid_packet_and_flash_rejected(self):
        base = hybrid.from_five(state(np.zeros((96, 128), dtype=np.uint8)))
        packet = hybrid.encode_delta(base, base)
        for damaged in (packet[:-1], packet+b'\0'):
            with self.assertRaises(ValueError): hybrid.decode_delta(base, damaged)
        damaged = hybrid.Frame(bytes([199])+base.attrs[1:], base.modes, base.cells)
        with self.assertRaises(ValueError): hybrid.decode(damaged)

    def test_refinement_changes_only_missing_shade_and_preserves_colours(self):
        compact = bytearray(3840)
        compact[3072:] = bytes([71])*768
        compact[384:512] = bytes([0x1b])*128
        image = np.zeros((96,128,3), dtype=np.uint8)
        image[12:16, :4] = np.array([0,64,128,191], dtype=np.uint8)[None,:,None]
        old, attrs = hybrid.decode(hybrid.from_compact(compact))
        refined = hybrid.refine_compact(compact, image)
        new = five.unpack_levels(refined[:3840])
        self.assertEqual(refined[3840:], attrs)
        self.assertTrue(np.all(new[new != old] == 3))
        np.testing.assert_array_equal(new[12, :4], [0,1,2,3])
        self.assertLessEqual(np.sum((new*63.75-image[:,:,0])**2),
                             np.sum((old*63.75-image[:,:,0])**2))


if __name__ == '__main__': unittest.main()
