#!/usr/bin/env python3
"""Explicitly export a safe local Diagrammatical HTML or SVG input to PNG."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    from .extract_svg import extract_svg_text
    from .validate_svg import validate_html, validate_svg
except ImportError:
    from extract_svg import extract_svg_text
    from validate_svg import validate_html, validate_svg

INSTALL_MESSAGE = """PNG export requires Diagrammatical's optional export dependency:

pip install -e '.[export]'
playwright install chromium"""
VIEWBOX = re.compile(r'viewBox\s*=\s*["\']\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)')


@dataclass
class PNGExportResult:
    input: str
    output: str
    scale: int
    frame: str
    valid: bool = False
    width: int | None = None
    height: int | None = None
    networkRequestsBlocked: int = 0
    fontFallbackUsed: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _svg_dimensions(svg: str, scale: int) -> tuple[int, int]:
    match = VIEWBOX.search(svg)
    if not match:
        raise ValueError("SVG must provide a valid viewBox before PNG export")
    width, height = float(match.group(1)), float(match.group(2))
    if width <= 0 or height <= 0:
        raise ValueError("SVG viewBox dimensions must be positive")
    return round(width * scale), round(height * scale)


def export_png(
    input_path: Path,
    output_path: Path,
    *,
    scale: int = 2,
    full_frame: bool = False,
    force: bool = False,
    font_timeout_ms: int = 3000,
) -> PNGExportResult:
    result = PNGExportResult(
        input=str(input_path),
        output=str(output_path),
        scale=scale,
        frame="full-editorial" if full_frame else "diagram-only",
    )
    if scale not in {1, 2, 3, 4}:
        result.errors.append("scale must be an integer from 1 to 4")
        return result
    if output_path.exists() and not force:
        result.errors.append(f"output already exists: {output_path}; pass --force to replace it")
        return result
    if not input_path.is_file() or input_path.suffix.lower() not in {".html", ".svg"}:
        result.errors.append("PNG input must be an existing local .html or .svg file")
        return result
    is_html = input_path.suffix.lower() == ".html"
    safety = validate_html(input_path) if is_html else validate_svg(input_path)
    if not safety.valid:
        result.errors.extend(safety.errors)
        return result
    try:
        text = input_path.read_text(encoding="utf-8")
        svg = extract_svg_text(text) if is_html else text
        width, height = _svg_dimensions(svg, scale)
    except (OSError, UnicodeError, ValueError) as exc:
        result.errors.append(str(exc))
        return result
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError:
        result.errors.append(INSTALL_MESSAGE)
        return result
    browser = None
    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except PlaywrightError as exc:
                try:
                    browser = playwright.chromium.launch(channel="chrome", headless=True)
                    result.warnings.append(
                        "bundled Playwright Chromium was unavailable; used the local Chrome channel"
                    )
                except PlaywrightError as chrome_exc:
                    result.errors.append(
                        f"Chromium could not start.\n{INSTALL_MESSAGE}\n"
                        f"Details: {exc}\nChrome fallback: {chrome_exc}"
                    )
                    return result
            context = browser.new_context(
                viewport={
                    "width": max(1, round(width / scale)),
                    "height": max(1, round(height / scale)),
                },
                device_scale_factor=scale,
            )
            page = context.new_page()

            def block_network(route: Any) -> None:
                url = route.request.url
                if url.startswith(("file:", "data:", "about:")):
                    route.continue_()
                else:
                    result.networkRequestsBlocked += 1
                    route.abort()

            page.route("**/*", block_network)
            if is_html:
                page.goto(input_path.resolve().as_uri(), wait_until="domcontentloaded")
            else:
                page.set_content(
                    "<!doctype html><style>html,body{margin:0;background:transparent}"
                    "svg{display:block}</style>" + svg,
                    wait_until="domcontentloaded",
                )
            try:
                page.evaluate(
                    "timeout => Promise.race([document.fonts.ready, "
                    "new Promise((_, reject) => setTimeout(() => "
                    "reject(new Error('font timeout')), timeout))])",
                    font_timeout_ms,
                )
            except (PlaywrightTimeoutError, PlaywrightError):
                result.fontFallbackUsed = True
                result.warnings.append(
                    "font readiness timed out; documented local fallbacks were used"
                )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if full_frame and is_html:
                page.screenshot(path=str(output_path), full_page=True)
                image = page.locator("body").bounding_box()
                if image:
                    result.width = round(image["width"] * scale)
                    result.height = round(image["height"] * scale)
            else:
                locator = page.locator("svg").first
                locator.screenshot(path=str(output_path))
                result.width, result.height = width, height
            result.valid = True
            browser.close()
            browser = None
    except PlaywrightError as exc:
        result.errors.append(f"PNG export failed: {exc}")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--full-frame", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--font-timeout-ms", type=int, default=3000)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = export_png(
        args.input,
        args.output,
        scale=args.scale,
        full_frame=args.full_frame,
        force=args.force,
        font_timeout_ms=args.font_timeout_ms,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"PNG export {'passed' if result.valid else 'failed'}: {args.output}")
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
