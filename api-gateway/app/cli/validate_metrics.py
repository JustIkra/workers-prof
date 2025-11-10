#!/usr/bin/env python3
"""
CLI tool for interactive validation of extracted metrics.

Features:
1. Load extraction results from JSON
2. Display images alongside extracted metrics
3. Allow user to correct/confirm each metric
4. Export validated results to JSON/CSV
"""

import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image

# Paths
OUTPUT_DIR = Path("/Users/maksim/git_projects/workers-prof/.memory-base/outputs/metrics")
TMP_DIR = Path("/Users/maksim/git_projects/workers-prof/tmp_images")


class MetricValidator:
    """Interactive CLI validator for extracted metrics."""

    def __init__(self, extraction_results_path: Path):
        self.extraction_results_path = extraction_results_path
        self.results = self._load_results()
        self.validated_metrics = []
        self.corrections = []

    def _load_results(self) -> list[dict]:
        """Load extraction results from JSON."""
        with open(self.extraction_results_path, encoding="utf-8") as f:
            return json.load(f)

    def run(self):
        """Run interactive validation."""
        print("=" * 80)
        print("METRIC VALIDATION TOOL")
        print("=" * 80)
        print()
        print("Instructions:")
        print("  - Review each extracted metric")
        print("  - Press ENTER to accept")
        print("  - Type new value to correct")
        print("  - Type 'skip' to skip this metric")
        print("  - Type 'quit' to exit and save")
        print()

        total_metrics = sum(len(result["metrics"]) for result in self.results)
        current = 0

        for result in self.results:
            docx_name = result["docx"]
            print(f"\n{'=' * 80}")
            print(f"Document: {docx_name}")
            print(f"{'=' * 80}\n")

            for metric in result["metrics"]:
                current += 1
                label = metric["label"]
                value = metric["value"]
                source = metric["source"]
                confidence = metric.get("confidence", 1.0)

                # Find image path
                image_path = self._find_image_path(docx_name, source)

                # Display metric info
                print(f"\n[{current}/{total_metrics}] Metric from {source}")
                print(f"Label:      {label}")
                print(f"Value:      {value}")
                print(f"Confidence: {confidence:.2f}")

                if image_path and image_path.exists():
                    print(f"Image:      {image_path.name}")
                    self._show_image_info(image_path)
                else:
                    print(f"Image:      NOT FOUND")

                # Get user input
                user_input = input("\nAction [ENTER=accept, VALUE=correct, skip, quit]: ").strip().lower()

                if user_input == "quit":
                    print("\nSaving and exiting...")
                    self._save_results()
                    return

                elif user_input == "skip":
                    print("  → Skipped")
                    continue

                elif user_input == "":
                    # Accept as-is
                    self.validated_metrics.append({
                        "label": label,
                        "value": value,
                        "source": source,
                        "validated": True,
                        "corrected": False
                    })
                    print("  ✓ Accepted")

                else:
                    # Correct value
                    new_value = user_input
                    self.validated_metrics.append({
                        "label": label,
                        "value": new_value,
                        "source": source,
                        "validated": True,
                        "corrected": True,
                        "original_value": value
                    })
                    self.corrections.append({
                        "label": label,
                        "original": value,
                        "corrected": new_value,
                        "source": source
                    })
                    print(f"  ✓ Corrected: {value} → {new_value}")

        # Save at the end
        print("\n" + "=" * 80)
        print("VALIDATION COMPLETE")
        print("=" * 80)
        self._save_results()

    def _find_image_path(self, docx_name: str, source: str) -> Path | None:
        """Find image path in tmp directory."""
        # Extract stem from docx name
        docx_stem = Path(docx_name).stem

        # Try to find processed image
        processed = TMP_DIR / f"{docx_stem}_{source}_improved_processed.png"
        if processed.exists():
            return processed

        processed_hybrid = TMP_DIR / f"{docx_stem}_{source}_hybrid_processed.png"
        if processed_hybrid.exists():
            return processed_hybrid

        # Fall back to original
        original = TMP_DIR / f"{docx_stem}_{source}"
        if original.exists():
            return original

        return None

    def _show_image_info(self, image_path: Path):
        """Show image information (size, format)."""
        try:
            with Image.open(image_path) as img:
                print(f"            {img.size[0]}x{img.size[1]} px, {img.format}")
        except Exception:
            pass

    def _save_results(self):
        """Save validated results to JSON/CSV."""
        # Count stats
        total = len(self.validated_metrics)
        corrected = len(self.corrections)
        accepted = total - corrected

        print(f"\nValidation summary:")
        print(f"  Total metrics validated: {total}")
        print(f"  Accepted as-is:          {accepted}")
        print(f"  Corrected:               {corrected}")

        if total == 0:
            print("\nNo metrics validated. Exiting without saving.")
            return

        # Save validated metrics
        validated_output = OUTPUT_DIR / "batura_validated_metrics.json"
        with open(validated_output, "w", encoding="utf-8") as f:
            json.dump(self.validated_metrics, f, ensure_ascii=False, indent=2)
        print(f"\nSaved validated metrics to {validated_output}")

        # Save corrections log
        if self.corrections:
            corrections_output = OUTPUT_DIR / "batura_corrections_log.json"
            with open(corrections_output, "w", encoding="utf-8") as f:
                json.dump(self.corrections, f, ensure_ascii=False, indent=2)
            print(f"Saved corrections log to {corrections_output}")

        # Export to CSV
        import csv
        csv_output = OUTPUT_DIR / "batura_validated_metrics.csv"
        with open(csv_output, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["label", "value", "source", "validated", "corrected"])
            writer.writeheader()
            for metric in self.validated_metrics:
                writer.writerow({
                    "label": metric["label"],
                    "value": metric["value"],
                    "source": metric["source"],
                    "validated": metric["validated"],
                    "corrected": metric.get("corrected", False)
                })
        print(f"Saved validated metrics to {csv_output}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate extracted metrics interactively",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate improved prompt results
  python -m app.cli.validate_metrics --input batura_improved_extraction_results.json

  # Validate hybrid OCR results
  python -m app.cli.validate_metrics --input batura_hybrid_extraction_results.json

  # Validate original results
  python -m app.cli.validate_metrics --input batura_extraction_results.json
        """
    )

    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Input JSON file with extraction results (filename only, will look in OUTPUT_DIR)"
    )

    args = parser.parse_args()

    # Resolve input path
    input_path = OUTPUT_DIR / args.input
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Run validator
    validator = MetricValidator(input_path)
    try:
        validator.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        validator._save_results()
        sys.exit(0)


if __name__ == "__main__":
    main()
