"""Numerical edge cases and matching regressions for task 23.

SciPy is an independent test oracle only; production metrics use NumPy.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from scipy import ndimage
import yaml

from src.eval.metric_utils import (
    ROOT, binary_dilation, erode_square, label, match_blobs,
    normalize_scale, scores, strict_config, validate_inputs,
)
from src.eval.benchmark_tier1 import continuous_metrics, expected_maps, run_tier1
from src.eval.bsds_threshold_grid import (
    STRUCT_2PX, BsdsItem, evaluate_percentile_grid, evaluate_prediction,
    hysteresis_percentile_fast,
)
from src.core.detectors import canny_nms, hysteresis_from_nms


class MetricTests(unittest.TestCase):
    def test_signed_mse_and_psnr_scope(self):
        a, b = np.array([-3., 1., 5.]), np.array([-1., 1., 1.])
        m = continuous_metrics(a, b)
        self.assertAlmostEqual(m["mse"], 20 / 3)
        self.assertAlmostEqual(m["rmse"] ** 2, m["mse"])
        self.assertEqual(m["psnr_db"], "")
        g = continuous_metrics(a, b, True)
        self.assertAlmostEqual(g["psnr_db"], 10 * np.log10(255 ** 2 / (20 / 3)))

    def test_perfect_gaussian_psnr_is_infinite(self):
        m = continuous_metrics([0., 1., 2.], [0., 1., 2.], True)
        self.assertTrue(np.isinf(m["psnr_db"]))
        self.assertEqual(m["status"], "PASS")

    def test_zero_reference_and_constant_correlation_not_pass(self):
        for a, b in [(np.zeros(4), np.zeros(4)), (np.ones(4), np.ones(4))]:
            m = continuous_metrics(a, b)
            self.assertIsNone(m["pearson_r"])
            self.assertEqual(m["status"], "UNDEFINED")

    def test_perfect_correlation_does_not_override_error(self):
        m = continuous_metrics(np.array([1., 2., 3.]) * 1.001, [1., 2., 3.])
        self.assertGreater(m["pearson_r"], .9999)
        self.assertEqual(m["status"], "FAIL")

    def test_invalid_continuous_inputs_rejected(self):
        for a, b in [([], []), ([np.nan], [1]), ([1, 2], [1])]:
            with self.assertRaises(ValueError):
                continuous_metrics(a, b)

    def test_missing_config_or_null_or_bool_normalization_rejected(self):
        cfg = strict_config()
        changes = [lambda c: c.pop("sigmas"), lambda c: c["kernel_k"].update(lx=None),
                   lambda c: c["featurej_normalized"].update(hessian="false")]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.yaml"
            for mutate in changes:
                c = copy.deepcopy(cfg)
                mutate(c)
                p.write_text(yaml.safe_dump(c), encoding="utf-8")
                with self.assertRaises(ValueError):
                    strict_config(p)

    def test_st_crop_sums_two_rounded_supports(self):
        cfg = strict_config()
        cfg["structure_pairs"] = [[1.1, 1.1]]
        cfg["kernel_k"]["lx"] = cfg["kernel_k"]["gauss"] = 1.1
        rows = [r for r in expected_maps(cfg) if r[1] == "st-l1"]
        self.assertEqual(rows[0][-1], 4)  # ceil(1.21)+ceil(1.21), not ceil(2.42).

    def test_missing_files_get_explicit_records(self):
        cfg = strict_config()
        gt = [{"image": name, "shape": [64, 64]} for name in cfg["tier1_images"]]
        with tempfile.TemporaryDirectory() as d:
            rows, borders, smoke = run_tier1(cfg, gt, Path(d), Path(d) / "py", Path(d) / "fj")
            self.assertEqual(len(rows), 220)
            self.assertEqual(len(smoke), 3)
            self.assertEqual({r["status"] for r in rows}, {"MISSING"})

    def test_normalization_avoids_double_scaling(self):
        cfg = strict_config()
        a = np.array([2.])
        self.assertEqual(normalize_scale(a, 3., 2, "fiji", "hessian", cfg)[0], 18.)
        cfg["featurej_normalized"]["hessian"] = True
        self.assertEqual(normalize_scale(a, 3., 2, "fiji", "hessian", cfg)[0], 2.)
        self.assertEqual(normalize_scale(a, 3., 2, "python", "hessian", cfg)[0], 18.)

    def test_numpy_morphology_against_independent_scipy(self):
        rng = np.random.default_rng(7)
        for shape in [(1, 1), (8, 11), (37, 51)]:
            a = rng.random(shape) > .15
            self.assertTrue(np.array_equal(binary_dilation(a, STRUCT_2PX), ndimage.binary_dilation(a, STRUCT_2PX)))
            for r in (0, 1, 3):
                self.assertTrue(np.array_equal(erode_square(a, r), ndimage.binary_erosion(a, np.ones((2*r+1, 2*r+1)))))

    def test_components_and_hysteresis_against_oracles(self):
        rng = np.random.default_rng(37)
        for prob in (0., .15, .6, 1.):
            a = rng.random((31, 43)) < prob
            mine, n = label(a)
            ref, nr = ndimage.label(a, np.ones((3, 3)))
            self.assertEqual(n, nr)
            # Verify actual partitions, independently of numeric label order.
            for k in range(1, nr+1):
                ids = np.unique(mine[ref == k])
                self.assertEqual(len(ids), 1)
                self.assertEqual(int((mine == ids[0]).sum()), int((ref == k).sum()))
        nms = canny_nms(rng.normal(size=(50, 61)), rng.normal(size=(50, 61)))
        for lo, hi in ((0, 100), (40, 80), (70, 95)):
            self.assertTrue(np.array_equal(hysteresis_percentile_fast(nms, lo, hi), hysteresis_from_nms(nms, lo, hi)))

    def test_euclidean_two_pixel_tolerance(self):
        truth = np.zeros((1, 9, 9), dtype=bool)
        truth[0, 4, 4] = True
        union = truth[0]
        item = BsdsItem("example", np.zeros((9, 9)), truth, union, binary_dilation(union, STRUCT_2PX), np.array([1]))
        pred = np.zeros((9, 9), dtype=bool)
        pred[6, 6] = True  # sqrt(8)>2, used to be accepted by square 5x5.
        self.assertEqual(evaluate_prediction(pred, item)["f1"], 0.)
        pred[:] = False
        pred[4, 6] = True
        self.assertAlmostEqual(evaluate_prediction(pred, item)["f1"], 1.)

    def test_empty_nms_still_counts_in_grid_mean(self):
        truth = np.zeros((1, 7, 7), dtype=bool)
        truth[0, 3, 3] = True
        def item(name):
            return BsdsItem(name, np.zeros((7, 7)), truth, truth[0], binary_dilation(truth[0], STRUCT_2PX), np.array([1]))
        nms = np.zeros((7, 7)); nms[3, 3] = 1.
        rows = evaluate_percentile_grid({"a": nms, "b": np.zeros_like(nms)}, [item("a"), item("b")], [40], [90])
        self.assertEqual(rows[0]["n_images"], 2)
        self.assertAlmostEqual(rows[0]["mean_f1"], .5)

    def test_one_prediction_cannot_match_two_gt(self):
        gt = [dict(x=0., y=0., radius=5.), dict(x=1., y=0., radius=5.)]
        pairs, gi, pi = match_blobs(gt, [(0., .5, 2., 5., 10.)])
        self.assertEqual(len(pairs), 1)
        self.assertEqual(scores(len(pairs), len(pi), len(gi)), (1., .5, 2/3))

    def test_matching_uses_augmenting_paths(self):
        gt = [dict(x=0., y=0., radius=5.), dict(x=2., y=0., radius=5.)]
        ds = [(0., 1., 2., 5., 10.), (0., -1., 2., 5., 10.)]
        pairs, _, _ = match_blobs(gt, ds)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(len({j for i,j in pairs}), 2)

    def test_ignore_region_and_radius_gate(self):
        gt = [dict(x=10., y=10., radius=5.)]
        ds = [(10., 10., 2., 7., 10.), (1., 1., 2., 5., 10.)]
        pairs, _, pi = match_blobs(gt, ds, [[0, 0, 2, 2]])
        self.assertEqual(len(pairs), 0)
        self.assertEqual(pi, [0])
        self.assertEqual(len(match_blobs(gt, [(10., 12., 2., 6., 10.)])[0]), 1)

    def test_live_dataset_checksums_and_ready(self):
        gt, evidence = validate_inputs()
        self.assertEqual(len(gt), 25)
        self.assertTrue(evidence)


if __name__ == "__main__":
    unittest.main()
