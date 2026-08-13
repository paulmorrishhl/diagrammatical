#!/usr/bin/env python3
"""Validate brand schema, semantic roles, contrast, fonts, and local SVG assets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from defusedxml import ElementTree

try:
    from .contrast import contrast_ratio
    from .validate import load_structured_file, validate_document
except ImportError:
    from contrast import contrast_ratio
    from validate import load_structured_file, validate_document

UNSAFE_SVG_ELEMENTS = {"script", "iframe", "foreignobject", "object", "embed"}
REMOTE_URL = re.compile(r"(?:https?:)?//", re.IGNORECASE)
REQUIRED_ROLES = {
    "canvas",
    "surface",
    "surfaceSecondary",
    "ink",
    "inkMuted",
    "rule",
    "connector",
    "emphasisPrimary",
    "emphasisPrimaryTint",
    "emphasisSecondary",
    "external",
    "success",
    "warning",
    "danger",
    "deprecated",
}


@dataclass
class BrandValidationResult:
    source: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    contrast: list[dict[str, Any]] = field(default_factory=list)
    adjustments: list[dict[str, Any]] = field(default_factory=list)
    fontDisclosures: list[str] = field(default_factory=list)
    resolvedBrand: dict[str, Any] | None = None

    @property
    def valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["valid"] = self.valid
        return value


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1].lower()


def validate_svg_asset(path: Path) -> list[str]:
    """Check a reusable logo/icon SVG without requiring diagram accessibility metadata."""

    errors: list[str] = []
    if path.suffix.lower() != ".svg":
        return [f"asset must be an SVG file: {path}"]
    try:
        if path.stat().st_size > 1_000_000:
            return [f"SVG asset exceeds the 1,000,000-byte safety limit: {path}"]
        root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, Exception) as exc:
        return [f"could not safely parse SVG asset {path}: {exc}"]
    if _local_name(root.tag) != "svg":
        errors.append("SVG asset root must be <svg>")
    for element in root.iter():
        tag = _local_name(element.tag)
        if tag in UNSAFE_SVG_ELEMENTS:
            errors.append(f"unsafe SVG asset element <{tag}> is not permitted")
        for raw_name, value in element.attrib.items():
            name = _local_name(raw_name)
            if name.startswith("on"):
                errors.append(f"inline SVG asset event attribute '{name}' is not permitted")
            if name in {"href", "src"} and value and (
                REMOTE_URL.search(value) or not value.startswith("#")
            ):
                errors.append(f"unsafe external SVG asset reference is not permitted: {value}")
    return list(dict.fromkeys(errors))


def _best_foreground(background: str, candidates: Sequence[str]) -> tuple[str, float]:
    values = [(candidate, contrast_ratio(candidate, background)) for candidate in candidates]
    return max(values, key=lambda item: item[1])


def _adjust_toward_accessible(
    foreground: str, background: str, minimum: float
) -> tuple[str, float] | None:
    """Find the first 2% RGB mix toward black or white that meets the target."""

    source = [int(foreground[index : index + 2], 16) for index in (1, 3, 5)]
    for step in range(1, 51):
        amount = step / 50
        candidates: list[str] = []
        for target in (0, 255):
            values = [round(channel + (target - channel) * amount) for channel in source]
            candidates.append("#" + "".join(f"{value:02X}" for value in values))
        passing = [
            (candidate, contrast_ratio(candidate, background))
            for candidate in candidates
            if contrast_ratio(candidate, background) >= minimum
        ]
        if passing:
            return min(passing, key=lambda item: abs(item[1] - minimum))
    return None


def validate_brand_document(
    brand: Mapping[str, Any],
    *,
    source: str | None = None,
    brand_directory: Path | None = None,
    adjust: bool = False,
    available_fonts: set[str] | None = None,
) -> BrandValidationResult:
    result = BrandValidationResult(source=source, resolvedBrand=deepcopy(dict(brand)))
    schema = validate_document(brand, "brand", source=source)
    result.errors.extend(schema.errors)
    result.warnings.extend(schema.warnings)
    if not schema.valid:
        return result
    resolved = result.resolvedBrand
    assert resolved is not None
    policy = brand["accessibility"]
    normal_minimum = float(policy["normalTextContrast"])
    allow_adjustment = bool(policy["allowDerivedColours"])
    for variant_name, variant in resolved["variants"].items():
        roles = variant["roles"]
        missing = sorted(REQUIRED_ROLES - set(roles))
        if missing:
            result.errors.append(
                f"brand variant '{variant_name}' is missing semantic roles: {', '.join(missing)}"
            )
            continue
        text_pairs = (
            ("ink", "canvas", normal_minimum, "normal"),
            ("ink", "surface", normal_minimum, "normal"),
            ("inkMuted", "canvas", normal_minimum, "small"),
            ("inkMuted", "surface", normal_minimum, "small"),
        )
        for foreground_role, background_role, minimum, text_size in text_pairs:
            foreground = roles[foreground_role]
            background = roles[background_role]
            ratio = contrast_ratio(foreground, background)
            check = {
                "variant": variant_name,
                "foregroundRole": foreground_role,
                "backgroundRole": background_role,
                "foreground": foreground,
                "background": background,
                "textSize": text_size,
                "ratio": round(ratio, 3),
                "minimum": minimum,
                "passes": ratio >= minimum,
            }
            result.contrast.append(check)
            if ratio < minimum:
                proposed = _adjust_toward_accessible(foreground, background, minimum)
                if proposed and allow_adjustment:
                    adjustment = {
                        "variant": variant_name,
                        "role": foreground_role,
                        "sourceValue": foreground,
                        "proposedValue": proposed[0],
                        "ratio": round(proposed[1], 3),
                        "approved": bool(adjust),
                    }
                    result.adjustments.append(adjustment)
                    if adjust:
                        roles[foreground_role] = proposed[0]
                    else:
                        result.warnings.append(
                            f"{variant_name} {foreground_role} on {background_role} is "
                            f"{ratio:.2f}:1; "
                            f"proposed accessible value {proposed[0]} requires approval"
                        )
                else:
                    result.errors.append(
                        f"{variant_name} {foreground_role} on {background_role} is {ratio:.2f}:1, "
                        f"below {minimum:.2f}:1 and automatic adjustment is not permitted"
                    )
        foregrounds = variant.setdefault("foregrounds", {})
        for role in ("emphasisPrimary", "emphasisSecondary", "success", "warning", "danger"):
            foreground, ratio = _best_foreground(
                roles[role], (roles["ink"], roles["surface"], "#000000", "#FFFFFF")
            )
            foregrounds[role] = foreground
            passes = ratio >= normal_minimum
            result.contrast.append(
                {
                    "variant": variant_name,
                    "foregroundRole": f"textOn{role[0].upper()}{role[1:]}",
                    "backgroundRole": role,
                    "foreground": foreground,
                    "background": roles[role],
                    "textSize": "small",
                    "ratio": round(ratio, 3),
                    "minimum": normal_minimum,
                    "passes": passes,
                }
            )
            if not passes:
                result.errors.append(
                    f"{variant_name} cannot select accessible text for {role}; "
                    f"best contrast is {ratio:.2f}:1"
                )
    available = available_fonts or set()
    for role, font in brand["typography"].items():
        family = font["family"]
        if available and family not in available:
            result.fontDisclosures.append(
                f"{role} font '{family}' was not found locally; renderer fallbacks are "
                + ", ".join(font["fallbacks"])
            )
    logo = brand.get("logo", {})
    logo_source = logo.get("source") if isinstance(logo, Mapping) else None
    if logo_source and brand_directory:
        logo_path = (brand_directory / logo_source).resolve()
        try:
            logo_path.relative_to(brand_directory.resolve())
        except ValueError:
            result.errors.append("logo source must remain inside the project-owned brand directory")
        else:
            if not logo_path.is_file():
                result.errors.append(f"logo source does not exist: {logo_source}")
            else:
                result.errors.extend(validate_svg_asset(logo_path))
    icon_directory = brand.get("icons", {}).get("customDirectory")
    if icon_directory and brand_directory:
        icon_path = (brand_directory / icon_directory).resolve()
        try:
            icon_path.relative_to(brand_directory.resolve())
        except ValueError:
            result.errors.append(
                "custom icon directory must remain inside the project-owned brand directory"
            )
        else:
            if not icon_path.is_dir():
                result.errors.append(f"custom icon directory does not exist: {icon_directory}")
            else:
                for asset in sorted(icon_path.glob("*.svg")):
                    result.errors.extend(
                        f"icon {asset.name}: {error}" for error in validate_svg_asset(asset)
                    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brand", type=Path)
    parser.add_argument(
        "--adjust", action="store_true", help="apply permitted proposed adjustments"
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        brand = load_structured_file(args.brand)
        result = validate_brand_document(
            brand,
            source=str(args.brand),
            brand_directory=args.brand.parent,
            adjust=args.adjust,
        )
    except ValueError as exc:
        result = BrandValidationResult(source=str(args.brand), errors=[str(exc)])
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Brand validation {'passed' if result.valid else 'failed'}: {args.brand}")
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
