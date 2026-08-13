#!/usr/bin/env python3
"""Validate Diagrammatical HTML and SVG safety, accessibility, and basic geometry."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from defusedxml import ElementTree

MAX_OUTPUT_BYTES = 2_000_000
UNSAFE_ELEMENTS = {"script", "iframe", "foreignobject", "object", "embed"}
REMOTE_URL = re.compile(r"(?:https?:)?//", re.IGNORECASE)
CSS_IMPORT = re.compile(r"@import\b", re.IGNORECASE)
CSS_REMOTE_URL = re.compile(r"url\(\s*['\"]?(?:https?:)?//", re.IGNORECASE)
FONT_SIZE = re.compile(r"font-size\s*:\s*([0-9]+(?:\.[0-9]+)?)px", re.IGNORECASE)


@dataclass
class OutputValidationResult:
    kind: str
    source: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["valid"] = self.valid
        return value


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1].lower()


def _read_bounded(path: Path) -> str:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    if size > MAX_OUTPUT_BYTES:
        raise ValueError(f"output exceeds the {MAX_OUTPUT_BYTES:,}-byte limit: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read UTF-8 output {path}: {exc}") from exc


class _SafetyHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.errors: list[str] = []
        self.svg_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered_tag = tag.lower()
        if lowered_tag in UNSAFE_ELEMENTS:
            self.errors.append(f"unsafe HTML element <{tag}> is not permitted")
        if lowered_tag == "svg":
            self.svg_count += 1
        for name, value in attrs:
            lowered_name = name.lower()
            actual_value = value or ""
            if lowered_name.startswith("on"):
                self.errors.append(f"inline event attribute '{name}' is not permitted")
            if lowered_name == "srcdoc":
                self.errors.append("srcdoc is not permitted")
            if lowered_tag == "img" and lowered_name == "src":
                self.errors.append("HTML images are not permitted; use safe inline SVG geometry")
            if lowered_name in {"src", "href", "xlink:href"} and REMOTE_URL.search(
                actual_value
            ):
                self.errors.append(f"remote resource URL is not permitted: {actual_value}")
            if lowered_name == "style" and (
                CSS_IMPORT.search(actual_value) or CSS_REMOTE_URL.search(actual_value)
            ):
                self.errors.append("CSS imports and remote CSS URLs are not permitted")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        if CSS_IMPORT.search(data) or CSS_REMOTE_URL.search(data):
            self.errors.append("CSS imports and remote CSS URLs are not permitted")


def validate_html_text(text: str, *, source: str | None = None) -> OutputValidationResult:
    result = OutputValidationResult(kind="html", source=source)
    parser = _SafetyHTMLParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:
        result.errors.append(f"could not parse HTML: {exc}")
        return result
    result.errors.extend(dict.fromkeys(parser.errors))
    if parser.svg_count != 1:
        result.errors.append(
            f"expected exactly one inline diagram SVG, found {parser.svg_count}"
        )
    return result


def validate_html(path: Path) -> OutputValidationResult:
    try:
        text = _read_bounded(path)
    except ValueError as exc:
        return OutputValidationResult(kind="html", source=str(path), errors=[str(exc)])
    return validate_html_text(text, source=str(path))


def _parse_view_box(value: str | None) -> tuple[float, float, float, float] | None:
    if not value:
        return None
    try:
        numbers = tuple(float(part) for part in re.split(r"[\s,]+", value.strip()))
    except ValueError:
        return None
    if len(numbers) != 4:
        return None
    return numbers  # type: ignore[return-value]


def validate_svg_text(
    text: str, *, source: str | None = None, slug: str | None = None
) -> OutputValidationResult:
    result = OutputValidationResult(kind="svg", source=source)
    try:
        root = ElementTree.fromstring(text)
    except Exception as exc:
        result.errors.append(f"could not safely parse SVG XML: {exc}")
        return result
    if _local_name(root.tag) != "svg":
        result.errors.append("root element must be <svg>")
        return result

    view_box = _parse_view_box(root.attrib.get("viewBox"))
    if view_box is None:
        result.errors.append("SVG must declare a four-number viewBox")
    elif view_box[2] <= 0 or view_box[3] <= 0:
        result.errors.append("SVG viewBox width and height must be positive")

    if root.attrib.get("role") != "img":
        result.errors.append('SVG must carry role="img"')
    labelled_by = root.attrib.get("aria-labelledby", "").split()
    if len(labelled_by) < 2:
        result.errors.append("SVG aria-labelledby must reference title and description IDs")

    children = list(root)
    if not children or _local_name(children[0].tag) != "title":
        result.errors.append("SVG <title> must be the first child")
    ids: dict[str, str] = {}
    title_ids: set[str] = set()
    desc_ids: set[str] = set()
    focal_count = 0
    for element in root.iter():
        tag = _local_name(element.tag)
        if tag in UNSAFE_ELEMENTS:
            result.errors.append(f"unsafe SVG element <{tag}> is not permitted")
        element_id = element.attrib.get("id")
        if element_id:
            if element_id in ids:
                result.errors.append(f"duplicate SVG ID '{element_id}'")
            else:
                ids[element_id] = tag
            if slug and not element_id.startswith(f"{slug}-"):
                result.errors.append(
                    f"SVG ID '{element_id}' must be prefixed with diagram slug '{slug}-'"
                )
            if tag == "title":
                title_ids.add(element_id)
            elif tag == "desc":
                desc_ids.add(element_id)
        for name, value in element.attrib.items():
            attribute = _local_name(name)
            if attribute.startswith("on"):
                result.errors.append(f"inline SVG event attribute '{attribute}' is not permitted")
            if attribute == "href" and value and not value.startswith("#"):
                result.errors.append(f"unsafe external SVG reference is not permitted: {value}")
            if attribute == "style" and (
                CSS_IMPORT.search(value) or CSS_REMOTE_URL.search(value)
            ):
                result.errors.append("CSS imports and remote CSS URLs are not permitted")
        if tag == "style":
            css = element.text or ""
            if CSS_IMPORT.search(css) or CSS_REMOTE_URL.search(css):
                result.errors.append("CSS imports and remote CSS URLs are not permitted")
            for match in FONT_SIZE.finditer(css):
                if float(match.group(1)) < 12:
                    result.warnings.append(
                        f"declared font size {match.group(1)}px is below the 12px "
                        "document-wide review floor"
                    )
        if tag == "text" and view_box is not None and "transform" not in element.attrib:
            min_x, min_y, width, height = view_box
            for axis, lower, upper in (
                ("x", min_x, min_x + width),
                ("y", min_y, min_y + height),
            ):
                raw_coordinate = element.attrib.get(axis)
                if raw_coordinate is None:
                    continue
                try:
                    coordinate = float(re.split(r"[\s,]+", raw_coordinate.strip())[0])
                except (ValueError, IndexError):
                    continue
                if coordinate < lower or coordinate > upper:
                    result.errors.append(
                        f"text {axis} coordinate {coordinate:g} falls outside the SVG viewBox"
                    )
        font_size = element.attrib.get("font-size")
        if font_size:
            match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)(?:px)?", font_size.strip())
            if match and float(match.group(1)) < 12:
                result.warnings.append(
                    f"declared font size {match.group(1)}px is below the 12px "
                    "document-wide review floor"
                )
        if element.attrib.get("data-emphasis") == "primary":
            focal_count += 1
        status = element.attrib.get("data-status")
        if status and status != "default":
            if not (
                element.attrib.get("data-status-label")
                or element.attrib.get("data-status-cue")
            ):
                result.errors.append(
                    f"status '{status}' requires data-status-label or data-status-cue so "
                    "colour is not the only carrier of meaning"
                )
        path_role = element.attrib.get("data-path")
        if path_role in {"failure", "exception"} and not (
            element.attrib.get("data-path-label")
            and element.attrib.get("data-path-cue")
        ):
            result.errors.append(
                f"{path_role} path requires both data-path-label and data-path-cue so its "
                "meaning is explicit and does not rely on colour"
            )
        message_kind = element.attrib.get("data-message-kind")
        if message_kind in {"async", "return"} and not element.attrib.get(
            "data-message-cue"
        ):
            result.errors.append(
                f"sequence {message_kind} message requires data-message-cue so line or "
                "arrow treatment, not colour alone, carries meaning"
            )
        if element.attrib.get("data-link") == "cross" and not (
            element.attrib.get("data-link-label")
            and element.attrib.get("data-link-cue")
        ):
            result.errors.append(
                "site-map cross-link requires data-link-label and data-link-cue so it is "
                "distinguishable from hierarchy links"
            )

    if labelled_by:
        missing = [reference for reference in labelled_by if reference not in ids]
        if missing:
            result.errors.append(
                f"aria-labelledby references missing SVG IDs: {', '.join(missing)}"
            )
        if not title_ids.intersection(labelled_by):
            result.errors.append("aria-labelledby must reference the SVG title")
        if not desc_ids.intersection(labelled_by):
            result.errors.append("aria-labelledby must reference the SVG description")
    descriptions = [
        "".join(element.itertext()).strip()
        for element in root.iter()
        if _local_name(element.tag) == "desc"
    ]
    if not descriptions or max(map(len, descriptions), default=0) < 20:
        result.errors.append("SVG must contain a useful description of at least 20 characters")
    if focal_count > 2:
        result.errors.append(f"SVG contains {focal_count} primary focal elements; maximum is 2")
    result.errors = list(dict.fromkeys(result.errors))
    result.warnings = list(dict.fromkeys(result.warnings))
    return result


def validate_svg(path: Path, *, slug: str | None = None) -> OutputValidationResult:
    try:
        text = _read_bounded(path)
    except ValueError as exc:
        return OutputValidationResult(kind="svg", source=str(path), errors=[str(exc)])
    return validate_svg_text(text, source=str(path), slug=slug)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="HTML or SVG file to validate")
    parser.add_argument("--slug", help="require SVG IDs to use this prefix")
    parser.add_argument("--json", action="store_true", help="emit structured JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = (
        validate_svg(args.source, slug=args.slug)
        if args.source.suffix.lower() == ".svg"
        else validate_html(args.source)
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"{result.kind} validation {'passed' if result.valid else 'failed'}: {args.source}")
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
