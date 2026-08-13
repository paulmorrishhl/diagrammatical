#!/usr/bin/env python3
"""Extract one canonical inline SVG from a safe Diagrammatical HTML file."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from .validate_svg import validate_html_text, validate_svg_text
except ImportError:  # Direct script execution.
    from validate_svg import validate_html_text, validate_svg_text

MAX_HTML_BYTES = 2_000_000
SVG_PATTERN = re.compile(r"<svg\b[^>]*>.*?</svg\s*>", re.IGNORECASE | re.DOTALL)
ID_PATTERN = re.compile(r"\bid\s*=\s*(['\"])(.*?)\1", re.IGNORECASE | re.DOTALL)


def extract_svg_text(html: str, *, selector: str | None = None) -> str:
    safety = validate_html_text(html)
    unsafe_errors = [
        error for error in safety.errors if not error.startswith("expected exactly one inline")
    ]
    if unsafe_errors:
        raise ValueError("unsafe HTML cannot be extracted: " + "; ".join(unsafe_errors))
    matches = SVG_PATTERN.findall(html)
    if selector is not None:
        if not selector.startswith("#") or len(selector) == 1:
            raise ValueError("selector must be a simple SVG ID such as '#diagram-id'")
        selected_id = selector[1:]
        matches = [
            match
            for match in matches
            if (identifier := ID_PATTERN.search(match.split(">", 1)[0]))
            and identifier.group(2) == selected_id
        ]
    if len(matches) != 1:
        qualifier = f" for selector {selector!r}" if selector else ""
        raise ValueError(
            f"expected exactly one canonical inline SVG{qualifier}, found {len(matches)}"
        )
    svg = matches[0].strip() + "\n"
    validation = validate_svg_text(svg)
    if not validation.valid:
        raise ValueError("extracted SVG is invalid: " + "; ".join(validation.errors))
    return svg


def extract_svg_file(
    html_path: Path, output_path: Path, *, selector: str | None = None
) -> None:
    try:
        size = html_path.stat().st_size
    except OSError as exc:
        raise ValueError(f"cannot read {html_path}: {exc}") from exc
    if size > MAX_HTML_BYTES:
        raise ValueError(f"HTML exceeds the {MAX_HTML_BYTES:,}-byte extraction limit")
    try:
        html = html_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read UTF-8 HTML {html_path}: {exc}") from exc
    svg = extract_svg_text(html, selector=selector)
    try:
        output_path.write_text(svg, encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot write {output_path}: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path, help="self-contained HTML source")
    parser.add_argument("output", type=Path, help="standalone SVG destination")
    parser.add_argument("--selector", help="simple SVG ID selector when HTML has multiple SVGs")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        extract_svg_file(args.html, args.output, selector=args.selector)
    except ValueError as exc:
        print(f"SVG extraction failed: {exc}", file=sys.stderr)
        return 1
    print(f"Extracted canonical SVG: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
