#!/usr/bin/env python3
"""Create approval-gated project-owned Diagrammatical brand proposals and packs."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

try:
    from .calibration import write_calibration
    from .validate import load_structured_file, validate_document
    from .validate_brand import validate_brand_document, validate_svg_asset
except ImportError:
    from calibration import write_calibration
    from validate import load_structured_file, validate_document
    from validate_brand import validate_brand_document, validate_svg_asset

SKILL_ROOT = Path(__file__).resolve().parents[1]
USER_ROOT_NAME = ".diagrammatical"


def plugin_tree_digest(skill_root: Path = SKILL_ROOT) -> str:
    """Hash plugin-owned files so callers can prove onboarding did not mutate them."""

    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in skill_root.rglob("*") if candidate.is_file()):
        digest.update(path.relative_to(skill_root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _assert_project_target(project_root: Path) -> Path:
    target = (project_root / USER_ROOT_NAME).resolve()
    try:
        target.relative_to(SKILL_ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("user branding cannot be written inside the installed plugin")
    if project_root.name == "diagrammatical" and project_root.resolve() == SKILL_ROOT.resolve():
        raise ValueError("project root cannot be the installed shared-skill directory")
    return target


def _write_brand_files(
    directory: Path,
    brand: dict[str, Any],
    receipt: dict[str, Any],
    *,
    logo_source: Path | None = None,
    font_disclosures: list[str] | None = None,
) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    if logo_source:
        logo_errors = validate_svg_asset(logo_source)
        if logo_errors:
            raise ValueError("; ".join(logo_errors))
        shutil.copyfile(logo_source, directory / "logo.svg")
        brand["logo"]["source"] = "./logo.svg"
    else:
        brand["logo"]["source"] = None
        brand["logo"]["placements"] = []
    (directory / "brand.yaml").write_text(
        yaml.safe_dump(brand, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    (directory / "fidelity.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    calibration = write_calibration(
        brand, directory, font_disclosures=font_disclosures
    )
    if not calibration["valid"]:
        raise ValueError("calibration output failed safety or accessibility validation")
    return calibration


def _update_project_default(config_path: Path, brand_id: str) -> None:
    if config_path.is_file():
        config = load_structured_file(config_path)
    else:
        config = {"schemaVersion": 1}
    config.setdefault("defaults", {})["brand"] = brand_id
    validation = validate_document(config, "config", source=str(config_path))
    if not validation.valid:
        raise ValueError("project configuration is invalid: " + "; ".join(validation.errors))
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def material_differences(existing: Any, proposed: Any, prefix: str = "$") -> list[dict[str, Any]]:
    """Return version-control-friendly leaf differences without deleting unrelated data."""

    if isinstance(existing, dict) and isinstance(proposed, dict):
        differences: list[dict[str, Any]] = []
        for key in sorted(set(existing) | set(proposed)):
            child_prefix = f"{prefix}.{key}"
            if key not in existing:
                differences.append(
                    {"path": child_prefix, "existing": None, "proposed": proposed[key]}
                )
            elif key not in proposed:
                differences.append(
                    {"path": child_prefix, "existing": existing[key], "proposed": None}
                )
            else:
                differences.extend(
                    material_differences(existing[key], proposed[key], child_prefix)
                )
        return differences
    if existing != proposed:
        return [{"path": prefix, "existing": existing, "proposed": proposed}]
    return []


def prepare_brand(
    project_root: Path,
    brand: dict[str, Any],
    receipt: dict[str, Any],
    *,
    approved: bool = False,
    set_default: bool = False,
    replace: bool = False,
    logo_source: Path | None = None,
    available_fonts: set[str] | None = None,
) -> dict[str, Any]:
    """Validate/preview a proposal, then persist only with explicit approval."""

    user_root = _assert_project_target(project_root)
    validation = validate_brand_document(
        brand, available_fonts=available_fonts, adjust=approved
    )
    if not validation.valid:
        return {
            "valid": False,
            "approved": approved,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "contrast": validation.contrast,
            "adjustments": validation.adjustments,
        }
    resolved_brand = validation.resolvedBrand or deepcopy(brand)
    resolved_receipt = deepcopy(receipt)
    resolved_receipt["contrast"] = validation.contrast
    resolved_receipt["adjustments"] = validation.adjustments
    resolved_receipt["warnings"] = list(
        dict.fromkeys([*resolved_receipt.get("warnings", []), *validation.warnings])
    )
    resolved_receipt["fontDisclosures"] = validation.fontDisclosures
    resolved_receipt["approvedAt"] = (
        datetime.now(UTC).isoformat().replace("+00:00", "Z") if approved else None
    )
    if approved:
        target = user_root / "brands" / resolved_brand["id"]
        if target.exists() and not replace:
            existing_path = target / "brand.yaml"
            existing = load_structured_file(existing_path) if existing_path.is_file() else {}
            return {
                "valid": False,
                "approved": True,
                "errors": [
                    f"brand '{resolved_brand['id']}' already exists; compare material "
                    "differences and approve replacement"
                ],
                "differences": material_differences(existing, resolved_brand),
            }
        target.mkdir(parents=True, exist_ok=True)
    else:
        target = Path(tempfile.mkdtemp(prefix=f"diagrammatical-{resolved_brand['id']}-proposal-"))
    calibration = _write_brand_files(
        target,
        resolved_brand,
        resolved_receipt,
        logo_source=logo_source,
        font_disclosures=validation.fontDisclosures,
    )
    if approved and set_default:
        _update_project_default(user_root / "config.yaml", resolved_brand["id"])
    return {
        "valid": True,
        "approved": approved,
        "saved": approved,
        "defaultUpdated": bool(approved and set_default),
        "directory": str(target),
        "files": sorted(path.name for path in target.iterdir() if path.is_file()),
        "contrast": validation.contrast,
        "adjustments": validation.adjustments,
        "warnings": resolved_receipt["warnings"],
        "calibration": calibration,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("brand", type=Path)
    parser.add_argument("fidelity", type=Path)
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--set-default", action="store_true")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--logo", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    brand = load_structured_file(args.brand)
    receipt = json.loads(args.fidelity.read_text(encoding="utf-8"))
    result = prepare_brand(
        args.project,
        brand,
        receipt,
        approved=args.approve,
        set_default=args.set_default,
        replace=args.replace,
        logo_source=args.logo,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
