"""Batch cleaner for Nigeria's three independent regional surveys.

Usage:
    python -m processing.run_processing --north /path/north.csv \
        --south /path/south.csv --south-west /path/south_west.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from processing.clean import REGIONS, clean_region


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean Nigeria regional survey exports")
    for region in REGIONS:
        parser.add_argument(f"--{region.replace('_', '-')}", dest=region, required=True)
    parser.add_argument("--output-dir", default="processing_output")
    parser.add_argument(
        "--form-definition",
        default="2023+Northern+Nigeria_+Survey+Data+Collection.xlsx",
        help="Northern Nigeria XLSForm used to decode SurveyCTO choice codes.",
    )
    parser.add_argument("--duration-minutes", type=float, default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    manifests = []
    for region in REGIONS:
        output = output_dir / f"nigeria_{region}_cleaned.csv"
        manifests.append(clean_region(
            getattr(args, region), output, region,
            form_definition=args.form_definition,
            duration_minutes=args.duration_minutes,
        ))
        print(f"[{region}] {manifests[-1]['input_rows']} -> {manifests[-1]['output_rows']} rows")

    (output_dir / "manifest.json").write_text(json.dumps(manifests, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
