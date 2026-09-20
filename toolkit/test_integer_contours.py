import unittest
import struct
import numpy as np
import integer_contours as codec


class IntegerContoursTests(unittest.TestCase):
    def test_invalid_delta_cannot_escape_canvas(self):
        # One level-1 two-point contour: the second point would be (-1,-1).
        data=bytes([4,0])+struct.pack('<HH',1,2)+bytes([0,0,0x66])+bytes(6)
        with self.assertRaisesRegex(ValueError,'invalid vertex'):
            codec.decode_pixels(data,np.zeros((72,128),dtype=np.uint8))

    def test_grid_boundaries_holes_diagonal_contacts_and_thin_lines(self):
        masks=[]
        masks.append(np.zeros((72,128),dtype=bool)); masks.append(~masks[0])
        masks.append(np.indices((72,128)).sum(axis=0)%2==0)
        nested=masks[0].copy(); nested[1:71,1:127]=True; nested[9:63,9:119]=False
        nested[20:50,30:90]=True; nested[30:40,40:80]=False; masks.append(nested)
        line=masks[0].copy(); line[36,:]=True; line[:,64]=True; masks.append(line)
        rng=np.random.default_rng(44)
        masks.extend(rng.random((72,128))<p for p in (.05,.5,.95))
        for mask in masks: np.testing.assert_array_equal(codec.fill(codec.trace(mask))[0],mask)

    def test_integer_diagonal_edge_and_half_open_pixel_centres(self):
        triangle=np.array([[0,0],[8,0],[0,8]],dtype=np.int32)
        expected=np.zeros((72,128),dtype=bool)
        for y in range(7): expected[y,:7-y]=True
        np.testing.assert_array_equal(codec.fill([triangle])[0],expected)

    def test_modes_exact_after_simplification_and_parity_delta(self):
        rng=np.random.default_rng(84); previous=np.zeros((72,128),dtype=np.uint8)
        current=rng.integers(0,4,(72,128),dtype=np.uint8)
        current[5:60,10:80]=2
        paths={shade:codec.trace(current==shade) for shade in range(4)}
        packets=[codec.packed_packet(current),codec.rectangle_packet(current,previous)[0]]
        polygons=[codec.polygon_packet(current,paths,e)[0] for e in (0,.5,1)]
        packets.extend(polygons)
        packets.extend(codec.compact_contours(p,grid=(i==0)) for i,p in enumerate(polygons))
        for packet in packets: np.testing.assert_array_equal(codec.decode_pixels(packet,previous),current)
        attrs=rng.integers(0,128,576,dtype=np.uint8); old=np.ones(576,dtype=np.uint8)
        for value in (old,attrs):
            r=codec.Reader(codec.pack_attributes(value,old))
            np.testing.assert_array_equal(codec.read_attributes(r,old),value); r.end()


if __name__=='__main__': unittest.main()
