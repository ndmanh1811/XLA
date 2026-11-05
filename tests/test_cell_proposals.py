"""Check assisted annotation candidates, preserving independent human decisions."""

import copy
import unittest
import numpy as np

from src.eval.annotate_cells import object_from_box
from src.eval.cell_proposals import propose_boxes
from src.eval.prepare_ground_truth import pending_cell_truth, validate_cell_truth


class CellProposalTests(unittest.TestCase):
    def setUp(self):
        self.image = np.zeros((64,64), dtype=np.uint8)
        self.image[8:18,9:17] = 100
        self.image[36:48,39:50] = 140

    def test_distinct_objects_and_original_coordinates(self):
        boxes = propose_boxes(self.image, threshold=30)
        self.assertEqual(len(boxes),2)
        self.assertEqual(boxes[0]["bbox_xyxy"],[8.,7.,17.,18.])

    def test_existing_labels_and_ignores_not_duplicated_or_mutated(self):
        existing = [object_from_box([7,6,20,20],1)]
        original = copy.deepcopy(existing)
        self.assertEqual(len(propose_boxes(self.image,existing,threshold=30)),1)
        self.assertEqual(propose_boxes(self.image,existing,[[35,33,54,51]],threshold=30),[])
        self.assertEqual(existing,original)

    def test_border_objects_not_suggested_as_complete_cells(self):
        self.image[0:8,25:35] = 100
        self.assertEqual(len(propose_boxes(self.image,threshold=30)),2)

    def test_large_touching_component_flagged(self):
        image = np.zeros((64,64),dtype=np.uint8)
        image[10:25,10:35] = 100
        boxes = propose_boxes(image,threshold=30)
        self.assertIn("possible_touching_or_elongated_objects",boxes[0]["flags"])

    def test_constant_input_has_no_suggestions(self):
        self.assertEqual(propose_boxes(np.zeros((32,32),dtype=np.uint8)),[])

    def test_invalid_input_rejected(self):
        with self.assertRaises(ValueError):
            propose_boxes(self.image.astype(np.uint16))
        with self.assertRaises(ValueError):
            propose_boxes(self.image,threshold=-1)

    def test_unreviewed_suggestions_block_completion(self):
        truth = pending_cell_truth("blob_05",self.image,"fixture")
        truth.update(origin="manual_with_component_suggestions",status="READY",reviewed=True,reviewer="fixture")
        item = object_from_box([8.,7.,17.,18.],1)
        item.update(annotation_method="threshold_component_suggestion",proposal_reviewed=False)
        truth["objects"]=[item]
        with self.assertRaises(ValueError):
            validate_cell_truth(truth,"blob_05",self.image,"fixture")
        item["proposal_reviewed"]=True
        self.assertEqual(validate_cell_truth(truth,"blob_05",self.image,"fixture"),"READY")


if __name__ == "__main__":
    unittest.main()
