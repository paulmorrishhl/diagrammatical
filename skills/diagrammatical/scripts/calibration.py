#!/usr/bin/env python3
"""Generate a project-owned brand calibration using production semantic roles."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

try:
    from .extract_svg import extract_svg_text
    from .validate import load_structured_file
    from .validate_brand import validate_brand_document
    from .validate_svg import validate_html_text, validate_svg_text
except ImportError:
    from extract_svg import extract_svg_text
    from validate import load_structured_file
    from validate_brand import validate_brand_document
    from validate_svg import validate_html_text, validate_svg_text

SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_ROOT / "assets/templates/calibration-sheet.html"
DEFAULT_LIGHT = {
    "canvas": "#F7F5EF",
    "surface": "#FFFFFF",
    "surfaceSecondary": "#F0EEE8",
    "ink": "#20242C",
    "inkMuted": "#687083",
    "rule": "#D8D4CA",
    "connector": "#697386",
    "emphasisPrimary": "#315BE8",
    "emphasisPrimaryTint": "#E7ECFF",
    "emphasisSecondary": "#19735E",
    "external": "#2767B0",
    "success": "#19735E",
    "warning": "#B86514",
    "danger": "#B83A42",
    "deprecated": "#9A6427",
}
DEFAULT_DARK = {
    "canvas": "#171A21",
    "surface": "#20242C",
    "surfaceSecondary": "#292E38",
    "ink": "#F4F1E9",
    "inkMuted": "#BCC3D1",
    "rule": "#4D5564",
    "connector": "#AEB7C7",
    "emphasisPrimary": "#9CB2FF",
    "emphasisPrimaryTint": "#29355C",
    "emphasisSecondary": "#72D3B7",
    "external": "#8AC5FA",
    "success": "#72D3B7",
    "warning": "#F1B36C",
    "danger": "#FF9AA1",
    "deprecated": "#E4B06D",
}


def _replace_colours(source: str, original: dict[str, str], resolved: dict[str, str]) -> str:
    def css_name(role: str) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", "-", role).lower()

    for role, old_value in original.items():
        declaration = rf"(--{re.escape(css_name(role))}\s*:\s*){re.escape(old_value)}"
        source = re.sub(
            declaration,
            lambda match, value=resolved[role]: match.group(1) + value,
            source,
            flags=re.IGNORECASE,
        )

    raw_roles: dict[str, str] = {}
    for role, old_value in original.items():
        raw_roles[old_value.lower()] = role
    placeholders: dict[str, str] = {}
    for index, (old_value, role) in enumerate(raw_roles.items()):
        placeholder = f"__DIAGRAMMATICAL_COLOUR_{index}__"
        source = re.sub(re.escape(old_value), placeholder, source, flags=re.IGNORECASE)
        placeholders[placeholder] = resolved[role]
    for placeholder, value in placeholders.items():
        source = source.replace(placeholder, value)
    return source


def generate_calibration(
    brand: dict[str, Any],
    *,
    font_disclosures: list[str] | None = None,
) -> tuple[str, str]:
    """Return self-contained HTML and the exact canonical inline SVG."""

    brand_id = brand["id"]
    brand_name = html.escape(brand["name"])
    description = html.escape(brand["description"])
    source = TEMPLATE.read_text(encoding="utf-8")
    source = source.replace(
        "Editorial Blueprint calibration sheet", f"{brand_name} calibration sheet"
    )
    source = source.replace("Editorial Blueprint semantic role", f"{brand_name} semantic role")
    source = source.replace(">Editorial Blueprint<", f">{brand_name}<")
    source = source.replace(
        "Warm editorial restraint for purposeful technical communication.", description
    )
    source = source.replace(
        "Cobalt marks focus; shape, labels, and stroke carry meaning alongside colour.",
        "Primary accent marks focus; shape, labels, and stroke carry meaning alongside colour.",
    )
    source = re.sub(r"(?<!data-)calibration-", f"{brand_id}-calibration-", source)
    source = source.replace(
        "Instrument Serif", html.escape(brand["typography"]["heading"]["family"])
    )
    source = source.replace(
        "IBM Plex Mono", html.escape(brand["typography"]["technical"]["family"])
    )
    source = re.sub(
        r"font-family: Inter, Arial, sans-serif",
        "font-family: "
        + html.escape(brand["typography"]["body"]["family"])
        + ", Arial, sans-serif",
        source,
    )
    source = _replace_colours(source, DEFAULT_LIGHT, brand["variants"]["light"]["roles"])
    dark = brand["variants"].get("dark")
    if dark:
        source = _replace_colours(source, DEFAULT_DARK, dark["roles"])
        source = source.replace("Editorial Blueprint after dark", f"{brand_name} after dark")
    else:
        source = re.sub(
            r'<text x="80" y="1610" class="section">Dark-mode preview</text>\s*'
            r'<g transform="translate\(80 1640\)" data-calibration-role="dark-preview">.*?</g>',
            '<text x="80" y="1610" class="section">Dark-mode status</text>\n'
            '<g transform="translate(80 1640)" data-calibration-role="dark-disclosure">'
            '<rect width="1280" height="196" rx="6" fill="var(--surface-secondary)"/>'
            '<text x="28" y="60" class="label">No reusable dark variant is configured.</text>'
            '<text x="28" y="94" class="small">Diagrammatical will not invert or save '
            "derived colours without approval.</text>"
            "</g>",
            source,
            flags=re.DOTALL,
        )
    disclosures = font_disclosures or [
        "Font availability was not verified; declared fallbacks remain active."
    ]
    disclosure = html.escape(" · ".join(disclosures))
    source = source.replace(
        "EDITORIAL BLUEPRINT · LIGHT + DARK · NO DROP SHADOWS · SEMANTIC ROLES ONLY",
        f"{brand_name.upper()} · {disclosure}",
    )
    svg = extract_svg_text(source)
    return source, svg


def write_calibration(
    brand: dict[str, Any], directory: Path, *, font_disclosures: list[str] | None = None
) -> dict[str, Any]:
    html_text, svg_text = generate_calibration(brand, font_disclosures=font_disclosures)
    html_check = validate_html_text(html_text, source=str(directory / "calibration.html"))
    svg_check = validate_svg_text(
        svg_text, source=str(directory / "calibration.svg"), slug=brand["id"]
    )
    result = {
        "valid": html_check.valid and svg_check.valid,
        "html": html_check.to_dict(),
        "svg": svg_check.to_dict(),
    }
    if result["valid"]:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "calibration.html").write_text(html_text, encoding="utf-8")
        (directory / "calibration.svg").write_text(svg_text, encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brand", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    brand = load_structured_file(args.brand)
    validation = validate_brand_document(brand, source=str(args.brand))
    if not validation.valid:
        print(json.dumps(validation.to_dict(), indent=2))
        return 1
    result = write_calibration(
        validation.resolvedBrand or brand,
        args.output,
        font_disclosures=validation.fontDisclosures,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
