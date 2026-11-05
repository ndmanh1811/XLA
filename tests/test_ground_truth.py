"""Check annotation integrity and readiness, without running detectors or metrics."""

import copy
import io
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import savemat

from src.eval.annotate_cells import object_from_box
from src.eval.prepare_data import synthetic_blob
from src.eval.prepare_ground_truth import (binary_mask, bsds_annotations, pending_cell_truth,
                                          synthetic_truth, validate_cell_truth, write_json)


class GroundTruthTests(unittest.TestCase):
    def setUp(self):
        self.raw = np.zeros((64, 64), dtype=np.uint8)
        self.truth = pending_cell_truth("blob_05", self.raw, "fixture-hash")

    def validate(self, truth):
        return validate_cell_truth(truth, "blob_05", self.raw, "fixture-hash")

    def test_all_matlab_annotators_preserved(self):
        boundary = np.zeros((6, 8), dtype=np.uint8)
        boundary[:, 3] = 1
        segmentation = np.ones((6, 8), dtype=np.uint16)
        segmentation[:, 4:] = 2
        people = np.empty((1, 2), dtype=object)
        people[0, 0] = {"Boundaries": boundary, "Segmentation": segmentation}
        people[0, 1] = {"Boundaries": boundary[::-1, ::-1], "Segmentation": segmentation[:, ::-1]}
        stream = io.BytesIO()
        savemat(stream, {"groundTruth": people})
        result = bsds_annotations(stream.getvalue(), boundary.shape)
        self.assertEqual(len(result), 2)
        np.testing.assert_array_equal(result[0][0], boundary*255)
        np.testing.assert_array_equal(result[1][1], segmentation[:, ::-1])
        with self.assertRaises(ValueError):
            bsds_annotations(stream.getvalue(), boundary.T.shape)

    def test_masks_reject_nonbinary_or_wrong_shape(self):
        with self.assertRaises(ValueError):
            binary_mask(np.full((6, 8), 42), (6, 8))
        with self.assertRaises(ValueError):
            binary_mask(np.zeros((6, 8)), (8, 6))

    def test_analytic_disk_and_gaussian_labels(self):
        for model in ("disk", "gaussian"):
            entry = {"name": "blob_fixture", "model": model, "polarity": "bright"}
            actual = synthetic_blob(entry)
            truth = synthetic_truth(entry, actual)
            self.assertEqual(len(truth["objects"]), 4)
            self.assertEqual((truth["objects"][0]["x"], truth["objects"][0]["y"]), (52, 64))
            radius = 3 if model == "disk" else np.sqrt(2)*2
            self.assertAlmostEqual(truth["objects"][0]["radius"], radius)
            actual[0, 0] ^= 1
            with self.assertRaises(ValueError):
                synthetic_truth(entry, actual)

    def test_empty_cell_template_is_pending(self):
        self.assertEqual(self.validate(self.truth), "PENDING_ANNOTATION")

    def test_unreviewed_labels_cannot_be_ready(self):
        self.truth["status"] = "READY"
        with self.assertRaises(ValueError):
            self.validate(self.truth)

    def test_review_requires_objects_and_reviewer(self):
        self.truth.update(status="READY", reviewed=True)
        with self.assertRaises(ValueError):
            self.validate(self.truth)
        self.truth["objects"] = [object_from_box([10, 12, 20, 30], 1)]
        with self.assertRaises(ValueError):
            self.validate(self.truth)
        self.truth["reviewer"] = "fixture reviewer"
        self.assertEqual(self.validate(self.truth), "READY")

    def test_coordinate_and_radius_consistency(self):
        self.truth["objects"] = [object_from_box([10, 12, 20, 30], 1)]
        self.truth["objects"][0]["x"] = 16
        with self.assertRaises(ValueError):
            self.validate(self.truth)

    def test_ignore_overlap_and_duplicates_are_rejected(self):
        self.truth["objects"] = [object_from_box([10, 12, 20, 30], 1)]
        self.truth["ignore_regions"] = [[12, 12, 18, 30]]
        with self.assertRaises(ValueError):
            self.validate(self.truth)
        self.truth["ignore_regions"] = []
        self.truth["objects"].append(copy.deepcopy(self.truth["objects"][0]))
        with self.assertRaises(ValueError):
            self.validate(self.truth)

    def test_annotation_for_another_image_is_rejected(self):
        self.truth["image_sha256"] = "different-input"
        with self.assertRaises(ValueError):
            self.validate(self.truth)

    def test_user_annotations_not_overwritten_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"labels.json"
            write_json(path, self.truth)
            changed = dict(self.truth, reviewer="another person")
            with self.assertRaises(FileExistsError):
                write_json(path, changed)


if __name__ == "__main__":
    unittest.main()
