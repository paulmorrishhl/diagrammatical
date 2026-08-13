#!/usr/bin/env python3
"""Run schema, safety, accessibility, SVG, and extraction checks for one deliverable."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    from .extract_svg import extract_svg_text
    from .validate import load_structured_file, validate_document
    from .validate_brand import validate_brand_document
    from .validate_svg import validate_html, validate_svg
except ImportError:  # Direct script execution.
    from extract_svg import extract_svg_text
    from validate import load_structured_file, validate_document
    from validate_brand import validate_brand_document
    from validate_svg import validate_html, validate_svg


@dataclass
class SelfCheckResult:
    directory: str
    diagram_id: str | None = None
    files: dict[str, str] = field(default_factory=dict)
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["valid"] = self.valid
        value["visualReview"] = {
            "status": "not-run",
            "findings": ["Mechanical self-check does not constitute visual review."],
        }
        return value


def _record(
    result: SelfCheckResult, name: str, check: Any, *, include_source: bool = True
) -> None:
    check_value = check.to_dict()
    if not include_source:
        check_value.pop("source", None)
    result.checks[name] = check_value
    result.errors.extend(f"{name}: {error}" for error in check.errors)
    result.warnings.extend(f"{name}: {warning}" for warning in check.warnings)


def run_self_check(directory: Path, *, require_validation: bool = True) -> SelfCheckResult:
    result = SelfCheckResult(directory=str(directory))
    source_path = directory / "diagram.yaml"
    if not source_path.is_file():
        result.errors.append("missing diagram.yaml")
        return result
    try:
        document = load_structured_file(source_path)
    except ValueError as exc:
        result.errors.append(str(exc))
        return result
    metadata = document.get("diagram", {})
    diagram_id = metadata.get("id") if isinstance(metadata, dict) else None
    if not isinstance(diagram_id, str):
        result.errors.append("diagram.yaml does not contain a usable diagram.id")
        return result
    result.diagram_id = diagram_id
    html_path = directory / f"{diagram_id}.html"
    svg_path = directory / f"{diagram_id}.svg"
    validation_path = directory / "validation.json"
    result.files = {
        "source": source_path.name,
        "html": html_path.name,
        "svg": svg_path.name,
        "validation": validation_path.name,
    }

    source_check = validate_document(document, "diagram", source=str(source_path))
    _record(result, "schema", source_check)
    if metadata.get("type") not in {
        "architecture", "flowchart", "sequence", "sitemap", "gantt"
    }:
        result.errors.append(
            "self-check accepts architecture, flowchart, sequence, sitemap, and Gantt diagrams"
        )

    if html_path.is_file():
        html_check = validate_html(html_path)
        _record(result, "htmlSafety", html_check)
    else:
        result.errors.append(f"missing {html_path.name}")
        html_check = None
    if svg_path.is_file():
        svg_check = validate_svg(svg_path, slug=diagram_id)
        _record(result, "svg", svg_check)
    else:
        result.errors.append(f"missing {svg_path.name}")
        svg_check = None

    if html_check and html_check.valid and svg_path.is_file():
        try:
            extracted = extract_svg_text(html_path.read_text(encoding="utf-8"))
            canonical = svg_path.read_text(encoding="utf-8")
            extraction_valid = extracted.strip() == canonical.strip()
            result.checks["extraction"] = {
                "valid": extraction_valid,
                "errors": [] if extraction_valid else ["standalone SVG differs from inline SVG"],
                "warnings": [],
            }
            if not extraction_valid:
                result.errors.append("extraction: standalone SVG differs from inline SVG")
        except (OSError, UnicodeError, ValueError) as exc:
            result.errors.append(f"extraction: {exc}")

    if require_validation:
        if not validation_path.is_file():
            result.errors.append("missing validation.json")
        else:
            try:
                saved = json.loads(validation_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                result.errors.append(f"invalid validation.json: {exc}")
            else:
                if saved.get("valid") is not True:
                    result.errors.append("validation.json does not record a valid result")
    png_files = sorted(path.name for path in directory.glob("*.png"))
    if png_files:
        result.errors.append(
            "PNG must not be generated by default; found " + ", ".join(png_files)
        )
    return result


def run_calibration_self_check(directory: Path) -> SelfCheckResult:
    """Run schema, contrast, HTML/SVG, extraction, receipt, and PNG checks for a brand."""

    result = SelfCheckResult(directory=str(directory))
    brand_path = directory / "brand.yaml"
    receipt_path = directory / "fidelity.json"
    html_path = directory / "calibration.html"
    svg_path = directory / "calibration.svg"
    for path in (brand_path, receipt_path, html_path, svg_path):
        if not path.is_file():
            result.errors.append(f"missing {path.name}")
    if result.errors:
        return result
    try:
        brand = load_structured_file(brand_path)
    except ValueError as exc:
        result.errors.append(str(exc))
        return result
    brand_id = brand.get("id")
    if not isinstance(brand_id, str):
        result.errors.append("brand.yaml does not contain a usable id")
        return result
    result.diagram_id = brand_id
    result.files = {
        "brand": brand_path.name,
        "fidelity": receipt_path.name,
        "html": html_path.name,
        "svg": svg_path.name,
    }
    brand_check = validate_brand_document(
        brand, source=str(brand_path), brand_directory=directory
    )
    result.checks["brand"] = brand_check.to_dict()
    result.errors.extend(f"brand: {error}" for error in brand_check.errors)
    result.warnings.extend(f"brand: {warning}" for warning in brand_check.warnings)
    html_check = validate_html(html_path)
    svg_check = validate_svg(svg_path, slug=brand_id)
    _record(result, "htmlSafety", html_check)
    _record(result, "svg", svg_check)
    if html_check.valid and svg_check.valid:
        try:
            inline = extract_svg_text(html_path.read_text(encoding="utf-8")).strip()
            standalone = svg_path.read_text(encoding="utf-8").strip()
            same = inline == standalone
        except (OSError, UnicodeError, ValueError) as exc:
            result.errors.append(f"extraction: {exc}")
        else:
            result.checks["extraction"] = {
                "valid": same,
                "errors": [] if same else ["standalone SVG differs from inline SVG"],
                "warnings": [],
            }
            if not same:
                result.errors.append("extraction: standalone SVG differs from inline SVG")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result.errors.append(f"invalid fidelity.json: {exc}")
    else:
        if receipt.get("brand") != brand_id:
            result.errors.append("fidelity.json brand does not match brand.yaml id")
        if "sources" not in receipt or "mappings" not in receipt or "contrast" not in receipt:
            result.errors.append("fidelity.json omits required source, mapping, or contrast data")
    png_files = sorted(path.name for path in directory.glob("*.png"))
    if png_files:
        result.errors.append("calibration must not generate PNG: " + ", ".join(png_files))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="diagram deliverable directory")
    parser.add_argument(
        "--calibration", action="store_true", help="self-check a project-owned brand calibration"
    )
    parser.add_argument(
        "--write-validation",
        action="store_true",
        help="write validation.json from current mechanical checks",
    )
    parser.add_argument("--json", action="store_true", help="also print structured JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = (
        run_calibration_self_check(args.directory)
        if args.calibration
        else run_self_check(args.directory, require_validation=not args.write_validation)
    )
    payload = result.to_dict()
    if args.write_validation:
        validation_path = args.directory / "validation.json"
        try:
            validation_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            result.errors.append(f"could not write validation.json: {exc}")
            payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"Self-check {'passed' if result.valid else 'failed'}: {args.directory} "
            f"({len(result.errors)} errors, {len(result.warnings)} warnings)"
        )
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
