"""Compatibility CLI for the single canonical metric pipeline.

Use python -m src.eval.run_metrics. The former independent evaluator is
preserved in outputs/archives/maintenance_10_11/truoc_khi_sua_pipeline_10_11.zip.
It is no longer used for matching, FOV, normalization or threshold selection.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["both"], default="both", help="A delivery always evaluates both sources")
    parser.add_argument("--blob-sigmas", choices=["config"], default="config", help="Both sources use the configured seven scales")
    parser.add_argument("--skip-generate", action="store_true")
    args = parser.parse_args()
    from src.eval.run_metrics import main as run
    sys.argv = [sys.argv[0]] + (["--skip-generate"] if args.skip_generate else [])
    run()


if __name__ == "__main__":
    main()
