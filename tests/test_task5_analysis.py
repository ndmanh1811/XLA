"""Task-24 regressions: aggregation and truthful repeated timing evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.eval.analyze_task5 import edge_summary, tier1_summary, validate_runtime
from src.eval.metric_utils import ROOT, RESULTS, sha256, strict_config, write_csv
from src.eval.task5_runtime import build_cases, read_csv, timing_summary, runtime_fingerprint


class Task5Tests(unittest.TestCase):
    def test_accuracy_aggregation_uses_mean_f1_not_f1_of_means(self):
        rows, refs = [], []
        for i in range(10):
            p, r = (1., .1) if i < 5 else (.1, 1.)
            for source in ("python", "fiji"):
                rows.append(dict(source=source, task="edge_bsds", sigma="1.0", precision=p,
                                 recall=r, f1=2*p*r/(p+r)))
            refs.append(dict(sigma="1.0", f1=.4))
        result = edge_summary(rows, refs)[0]
        self.assertAlmostEqual(result["python_f1"], 2/11)
        self.assertAlmostEqual(result["python_precision"], .55)
        self.assertAlmostEqual(result["delta_f1_fiji_minus_python"], 0.)
        with self.assertRaises(ValueError):
            edge_summary(rows[:-1], refs)

    def test_fidelity_summary_counts_both_criteria_from_measured_status(self):
        # Immutable measured fixture: unit tests must not require regenerating
        # the current delivery directory before they can run on a fresh clone.
        rows = read_csv(ROOT / "outputs/metrics/duc_08_11/tier1_report.csv")
        summary = tier1_summary(rows)
        self.assertEqual(sum(r["maps"] for r in summary), 220)
        self.assertEqual(sum(r["passed"] for r in summary), sum(r["status"] == "PASS" for r in rows))
        for r in summary:
            self.assertEqual(r["maps"], r["passed"]+r["failed"])
        bad = copy.deepcopy(rows); bad[0]["status"] = "MISSING"
        with self.assertRaises(ValueError):
            tier1_summary(bad)

    def test_runtime_cases_cover_both_structure_pairs_and_no_legacy(self):
        cases = build_cases(strict_config())
        keys = {(r["image"],r["command"],r["sigma"]) for r in cases}
        self.assertEqual(len(cases), len(keys))
        self.assertEqual(len(cases), 357)
        self.assertNotIn(("blob_01", "edge", "1.0"), keys)
        self.assertIn(("bsds_01", "structure", "sd1.0_si3.0"), keys)
        self.assertIn(("bsds_01", "structure", "sd2.0_si6.0"), keys)
        self.assertIn(("blob_05", "laplacian", "5.7"), keys)

    def test_timing_summary_requires_positive_multiple_samples(self):
        self.assertEqual(timing_summary([1,2,3,4,100])["median_ms"], 3.)
        for bad in ([1], [0,1,2], [1,2,np.nan]):
            with self.assertRaises(ValueError):
                timing_summary(bad)

    def fixture_runtime(self, directory):
        case = dict(image="test", command="gauss", sigma="1.0")
        env = dict(config_sha256=sha256(ROOT / "config.yaml"), measured_repeats=5, warmup_discarded=1,
                   measurement_inputs_code_sha256=runtime_fingerprint())
        (directory / "runtime_environment.json").write_text(json.dumps(env), encoding="utf-8")
        summaries = []
        for source, factor, filename in (("python", 2., "python_samples.csv"), ("fiji_engine", 1., "fiji_engine_samples.csv")):
            samples = [dict(source=source, **case, iteration=i, warmup=(i==0), runtime_ms=(10000 if i==0 else i*factor)) for i in range(6)]
            write_csv(directory / filename, samples)
            summaries.append(dict(source=source, **case, measured_repeats=5, median_ms=3*factor))
        write_csv(directory / "runtime_case_summary.csv", summaries)
        write_csv(directory / "runtime_paired.csv", [dict(**case, ratio_python_over_engine=2.)])
        return case

    def test_warmup_is_excluded_and_missing_iteration_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp); case = self.fixture_runtime(d)
            with patch("src.eval.analyze_task5.build_cases", return_value=[case]):
                summary, paired, _ = validate_runtime(d, {})
                self.assertEqual(float(summary[0]["median_ms"]), 6.)
                self.assertEqual(float(paired[0]["ratio_python_over_engine"]), 2.)
                write_csv(d / "python_samples.csv", read_csv(d / "python_samples.csv")[:-1])
                with self.assertRaises(ValueError):
                    validate_runtime(d, {})

    def test_runtime_wrong_median_and_warmup_flag_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp); case = self.fixture_runtime(d)
            with patch("src.eval.analyze_task5.build_cases", return_value=[case]):
                samples = read_csv(d / "python_samples.csv")
                samples[0]["warmup"] = "False"
                write_csv(d / "python_samples.csv", samples)
                with self.assertRaises(ValueError):
                    validate_runtime(d, {})
                self.fixture_runtime(d)
                summary = read_csv(d / "runtime_case_summary.csv")
                summary[0]["median_ms"] = 999
                write_csv(d / "runtime_case_summary.csv", summary)
                with self.assertRaises(ValueError):
                    validate_runtime(d, {})


if __name__ == "__main__":
    unittest.main()
