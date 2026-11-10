"""Regression tests at the canonical evaluator boundary."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from src.eval import metrics_tier2 as pipeline
from src.eval.metric_utils import match_blobs, strict_config
from src import config


class DeliveryPipelineTests(unittest.TestCase):
    def test_blob_evaluator_uses_one_to_one_and_ignore_for_both_sources(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            annotations = root / "data/gt/blob"
            annotations.mkdir(parents=True)
            for i in range(1, 6):
                (annotations / f"blob_{i:02d}.json").write_text(json.dumps(dict(
                    shape=[32, 32], polarity="bright",
                    objects=[dict(x=9, y=10, radius=3), dict(x=11, y=10, radius=3)],
                    ignore_regions=[[18, 18, 22, 22]])), encoding="utf-8")
            cfg = strict_config()
            detections = [(10, 10, 2, 3, 10), (20, 20, 2, 3, 10)]
            with patch.object(pipeline, "ROOT", root), \
                 patch.object(pipeline, "get_map", return_value=np.zeros((32, 32))), \
                 patch.object(pipeline, "detect_blob", return_value=detections):
                rows = pipeline.blobs(cfg, {"blob_thresholds": [1, 5]}, root)
            self.assertEqual(len(rows), 10)
            for r in rows:
                self.assertEqual((r["tp"], r["predicted_count"], r["gt_count"]), (1, 1, 2))
                self.assertEqual(r["ignored_predictions"], 1)
                self.assertEqual(r["precision"], 1)
                self.assertAlmostEqual(r["f1"], 2/3)

    def test_matching_finds_assignment_when_greedy_order_would_lose_a_match(self):
        gt = [dict(x=0, y=0, radius=3), dict(x=2, y=0, radius=3)]
        det = [(0, 1, 2, 3, 10), (0, -1, 2, 3, 10)]
        pairs, _, _ = match_blobs(gt, det)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(len({j for _, j in pairs}), 2)

    def test_drive_evaluation_support_follows_config_not_sigma2(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            folder = root / "data/gt/drive"
            folder.mkdir(parents=True)
            for i in range(1, 11):
                for suffix in ("vessels", "fov"):
                    Image.fromarray(np.full((32,32),255,np.uint8)).save(folder/f"drive_{i:02d}_{suffix}.png")
            cfg = strict_config()
            cfg.update(sigmas=[1., 3.], kernel_k=dict(gauss=2., lx=2., lxx=2.))
            with patch.object(pipeline, "ROOT", root), \
                 patch.object(pipeline, "get_map", return_value=np.ones((32,32))), \
                 patch.object(pipeline, "detect_ridge", side_effect=lambda *a, **k: np.ones((32,32))):
                rows = pipeline.ridges(cfg, {"ridge_thresholds": [.5]}, root)
            self.assertEqual(len(rows), 20)
            for row in rows:
                self.assertEqual(row["fov_erosion_px"], 6)
                self.assertEqual(row["valid_pixels"], 400)

    def test_fiji_normalization_flag_is_honored_at_map_loader(self):
        cfg = strict_config()
        cfg["featurej_normalized"]["laplacian"] = True
        with patch.object(pipeline, "read_map", return_value=np.ones((3,3))):
            fj = pipeline.get_map("fiji", "blob_01", "lap", 2., (3,3), cfg, True)
            py = pipeline.get_map("python", "blob_01", "lap", 2., (3,3), cfg, True)
        np.testing.assert_array_equal(fj, np.ones((3,3)))
        np.testing.assert_array_equal(py, np.full((3,3),4.))

    def test_required_scale_lists_do_not_fall_back(self):
        with patch.object(config, "load_config", return_value={}):
            for getter in (config.get_sigmas, config.get_blob_sigmas, config.get_structure_pairs, config.get_tier1_images):
                with self.subTest(getter=getter.__name__), self.assertRaises(ValueError):
                    getter()


if __name__ == "__main__":
    unittest.main()
