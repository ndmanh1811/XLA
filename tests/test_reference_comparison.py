"""Regression checks for measured library-comparison evidence."""
import unittest
import numpy as np
from benchmarks.reference_comparison.report_metrics import (
    continuous_metrics,measured_summary_text,component_summary,mask_agreement,
)


class ReferenceComparisonTests(unittest.TestCase):
    def test_constant_map_does_not_get_perfect_pearson(self):
        a=np.full((16,16),.1)
        m=continuous_metrics(a,a)
        self.assertIsNone(m['pearson_r'])
        self.assertFalse(m['pearson_defined'])
        self.assertEqual(m['max_error'],0.)

    def test_perfect_correlation_does_not_hide_amplitude_error(self):
        a=np.arange(9,dtype=float).reshape(3,3)
        m=continuous_metrics(a,3*a+2)
        self.assertAlmostEqual(m['pearson_r'],1.)
        self.assertGreater(m['max_error'],1.)
        self.assertNotIn('status',m)

    def test_image_summary_reflects_actual_negative_correlation(self):
        a=np.arange(9,dtype=float).reshape(3,3)
        text=measured_summary_text({'probe':(a,-a)},a>3,a>5)
        self.assertIn('probe: r=-1.00000000',text)
        self.assertNotIn('100% PASS',text)

    def test_mask_overlap_is_computed_from_both_masks(self):
        a=np.array([[1,1],[0,0]],bool);b=np.array([[1,0],[1,0]],bool)
        m=mask_agreement(a,b)
        self.assertAlmostEqual(m['iou'],1/3)
        self.assertEqual(m['dice'],.5)
        self.assertEqual(m['overlap_pixels'],1)

    def test_components_exclude_background_even_for_empty_mask(self):
        a=np.zeros((4,4),bool)
        self.assertEqual(component_summary(a)['components'],0)
        a[0,0]=True;a[3,3]=True
        m=component_summary(a)
        self.assertEqual(m['components'],2)
        self.assertEqual(m['mean_pixels_per_component'],1.)

    def test_invalid_arrays_are_rejected(self):
        with self.assertRaises(ValueError):continuous_metrics([1,np.nan],[1,2])
        with self.assertRaises(ValueError):continuous_metrics([1,2],[1])


if __name__=='__main__':unittest.main()
