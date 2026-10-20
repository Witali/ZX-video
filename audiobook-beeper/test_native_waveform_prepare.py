"""Meaningful float-bit/row-order controls for native waveform preparation."""
import unittest

import numpy as np

from ima_waveform_encoder import WaveformModel
from native_waveform_prepare import reference,unique_holds


class NativePreparationTests(unittest.TestCase):
    def test_reference_full_u8_range_and_padded_queries(self):
        source=np.r_[np.arange(256,dtype='u1'),np.arange(255,-1,-1,dtype='u1')]
        # Every phase cell at input zero, random subsequent times and beyond
        # EOF exercise the exact zero padding and six-term reduction order.
        generator=np.random.default_rng(8012)
        units=np.r_[np.arange(35469,dtype=np.int64),
            generator.integers(0,(len(source)+19)*35469,size=50000)]
        queries=units/80
        model=WaveformModel()
        expected=model.reference(source,queries);actual=reference(model,source,queries)
        self.assertEqual(expected.tobytes(),actual.tobytes())

    def test_reference_2d_shape_and_noncontiguous_source(self):
        source=np.arange(256,dtype='u1')[::2]
        queries=np.arange(2048,dtype=np.int64).reshape(128,16)*17/80
        model=WaveformModel()
        expected=model.reference(source,queries);actual=reference(model,source,queries)
        self.assertEqual(expected.shape,actual.shape)
        self.assertEqual(expected.tobytes(),actual.tobytes())

    def test_unique_exact_lexicographic_order_ties_and_hash_growth(self):
        generator=np.random.default_rng(12816)
        distinct=generator.integers(1,100,size=(700,16)).astype(np.float64)
        # Consecutive float64s must remain distinct; physically equal-looking
        # uniform rows may never be rounded to a common nominal interval.
        distinct[0]=28.;distinct[1]=28.;distinct[1,-1]=np.nextafter(28.,np.inf)
        rows=distinct[generator.integers(0,len(distinct),size=9000)]
        rows=np.r_[rows,distinct,rows[:100][::-1]]
        expected,expected_ids=np.unique(rows,axis=0,return_inverse=True)
        actual,actual_ids=unique_holds(rows)
        self.assertEqual(expected.tobytes(),actual.tobytes())
        self.assertEqual(expected_ids.tobytes(),actual_ids.tobytes())
        self.assertEqual(rows.tobytes(),actual[actual_ids].tobytes())

    def test_unique_noncontiguous_input(self):
        rows=np.arange(16*12,dtype=np.float64).reshape(12,16)+1
        rows=rows[::2,::-1]
        expected,ids=np.unique(rows,axis=0,return_inverse=True)
        actual,actual_ids=unique_holds(rows)
        self.assertEqual(expected.tobytes(),actual.tobytes())
        self.assertEqual(ids.tobytes(),actual_ids.tobytes())

    def test_unique_rejects_nonphysical_or_unsupported_intervals(self):
        for value in (0.,-0.,-1.,np.nan,np.inf,-np.inf):
            rows=np.full((2,16),28.);rows[0,3]=value
            with self.subTest(value=value),self.assertRaises(ValueError):unique_holds(rows)
        for rows in (np.empty((0,16)),np.ones((2,15)),np.ones((2,16),dtype='f4'),np.ones(16)):
            with self.subTest(shape=rows.shape),self.assertRaises(ValueError):unique_holds(rows)

    def test_reference_rejects_unsupported_grid_or_input(self):
        model=WaveformModel();source=np.full(128,128,'u1')
        for queries in (np.array([-.1]),np.array([.001]),np.array([])):
            with self.subTest(queries=queries),self.assertRaises(ValueError):reference(model,source,queries)
        with self.assertRaises(ValueError):reference(model,source.astype('f8'),np.array([0.]))


if __name__=='__main__':unittest.main()
