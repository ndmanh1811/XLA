"""Kiểm thử công cụ quét lưới ngưỡng BSDS theo sigma.

Trọng tâm là bảo đảm ``hysteresis_absolute``/``hysteresis_percentile_fast``
(dùng SciPy label) cho kết quả giống tuyệt đối với BFS 8-láng giềng trong
``src.core.detectors``. Nhờ đó lưới có thể chạy nhanh mà không đổi ngữ nghĩa
của ``detect_canny``.
"""

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.detectors import canny_nms, hysteresis_from_nms
from src.eval.bsds_threshold_grid import (
    BsdsItem,
    STRUCT_2PX,
    evaluate_absolute_grid,
    evaluate_percentile_grid,
    evaluate_prediction,
    hysteresis_absolute,
    hysteresis_percentile_fast,
    select_best_row,
)
from scipy.ndimage import binary_dilation


def _make_item(stem="synthetic", shape=(48, 64)):
  h, w = shape
  gt = np.zeros((2, h, w), dtype=bool)
  gt[0, h // 2, :] = True
  gt[1, h // 2 + 1, :] = True
  union = np.any(gt, axis=0)
  return BsdsItem(
      stem=stem,
      image=np.zeros(shape, dtype=np.float64),
      gt_boundaries=gt,
      union_gt=union,
      dilated_union_gt=binary_dilation(union, structure=STRUCT_2PX),
      annotator_positives=np.sum(gt, axis=(1, 2)),
  )


class TestBsdsGrid(unittest.TestCase):
  def test_fast_hysteresis_matches_core_bfs(self):
    rng = np.random.default_rng(42)
    lx = rng.normal(size=(64, 80))
    ly = rng.normal(size=(64, 80))
    nms = canny_nms(lx, ly)
    for p_low, p_high in [(10, 50), (30, 70), (60, 85), (80, 95)]:
      ref = hysteresis_from_nms(
          nms, p_low=p_low, p_high=p_high, return_binary=False
      )
      fast = hysteresis_percentile_fast(nms, p_low, p_high)
      self.assertTrue(
          np.array_equal(ref, fast),
          msg=f"Lệch tại p_low={p_low}, p_high={p_high}",
      )

  def test_absolute_hysteresis_matches_core_when_thresholds_match(self):
    rng = np.random.default_rng(7)
    lx = rng.normal(size=(40, 40))
    ly = rng.normal(size=(40, 40))
    nms = canny_nms(lx, ly)
    nonzero = nms[nms > 0]
    p_low, p_high = 35.0, 80.0
    t_low = float(np.percentile(nonzero, p_low))
    t_high = float(np.percentile(nonzero, p_high))
    ref = hysteresis_from_nms(
        nms, p_low=p_low, p_high=p_high, return_binary=False
    )
    fast = hysteresis_absolute(nms, t_low=t_low, t_high=t_high)
    self.assertTrue(np.array_equal(ref, fast))

  def test_evaluate_prediction_matches_manual_formula(self):
    item = _make_item()
    pred = np.zeros((48, 64), dtype=bool)
    pred[24, 10:50] = True
    metrics = evaluate_prediction(pred, item)
    self.assertAlmostEqual(metrics["precision"], 1.0)
    # Euclidean <=2px: 44 covered pixels on row 24, 42 on row 25.
    expected_recall = (44 / 64 + 42 / 64) / 2
    self.assertAlmostEqual(metrics["recall"], expected_recall)
    expected_f1 = 2 * expected_recall / (1.0 + expected_recall)
    self.assertAlmostEqual(metrics["f1"], expected_f1)
    self.assertEqual(int(metrics["predicted_count"]), 40)

  def test_percentile_grid_returns_valid_rows(self):
    item = _make_item()
    rng = np.random.default_rng(3)
    nms = np.zeros((48, 64), dtype=np.float64)
    nms[20:28, 10:54] = rng.random((8, 44))
    rows = evaluate_percentile_grid(
        {item.stem: nms},
        [item],
        grid_low=[10, 30, 60],
        grid_high=[50, 80, 95],
    )
    self.assertTrue(rows)
    for row in rows:
      self.assertLess(row["p_low"], row["p_high"])
      self.assertGreaterEqual(row["mean_f1"], 0.0)
      self.assertLessEqual(row["mean_f1"], 1.0)
    best = select_best_row(rows)
    self.assertIsNotNone(best)
    self.assertIn("mean_f1", best)

  def test_absolute_grid_returns_valid_rows(self):
    item = _make_item()
    rng = np.random.default_rng(4)
    edge = np.zeros((48, 64), dtype=np.float64)
    edge[20:28, 10:54] = rng.random((8, 44)) * 10.0
    rows = evaluate_absolute_grid(
        {item.stem: edge},
        [item],
        grid_low=[0.5, 2.0, 5.0],
        grid_high=[3.0, 6.0, 9.0],
    )
    self.assertTrue(rows)
    for row in rows:
      self.assertLess(row["t_low"], row["t_high"])
      self.assertGreaterEqual(row["mean_f1"], 0.0)
      self.assertLessEqual(row["mean_f1"], 1.0)


if __name__ == "__main__":
  unittest.main()
