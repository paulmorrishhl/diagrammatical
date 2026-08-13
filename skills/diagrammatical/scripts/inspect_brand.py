#!/usr/bin/env python3
"""Inspect static, local brand sources without executing repository code."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    from .validate import load_structured_file, validate_document
except ImportError:
    from validate import load_structured_file, validate_document

MAX_FILE_BYTES = 1_000_000
IGNORED_DIRECTORIES = {
    ".git",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "vendor",
}
STYLE_SUFFIXES = {".css", ".scss", ".sass", ".less"}
TAILWIND_NAMES = {
    "tailwind.config.js",
    "tailwind.config.cjs",
    "tailwind.config.mjs",
    "tailwind.config.ts",
}
HEX_COLOUR = re.compile(r"#[0-9a-fA-F]{6}\b")
CSS_BLOCK = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
CSS_DECLARATION = re.compile(r"(--[\w-]+|[\w-]+)\s*:\s*([^;{}]+)")
TOKEN_REFERENCE = re.compile(r"^\{([A-Za-z0-9_.-]+)\}$")
TAILWIND_FONT_BLOCK = re.compile(r"fontFamily\s*:\s*\{(.*?)\}", re.DOTALL)
TAILWIND_FONT_ENTRY = re.compile(
    r"[\"']?([A-Za-z][\w.-]*)[\"']?\s*:\s*(?:\[\s*)?[\"']([^\"']+)[\"']"
)
STATIC_PAIR = re.compile(
    r"[\"']?([A-Za-z][\w.-]*)[\"']?\s*:\s*[\"'](#[0-9a-fA-F]{6}|[^\"']*font[^\"']*)[\"']"
)


class TokenReferenceError(ValueError):
    """Raised for invalid or circular local design-token references."""


@dataclass
class InspectionResult:
    root: str
    sources: list[dict[str, str]] = field(default_factory=list)
    colours: list[dict[str, Any]] = field(default_factory=list)
    fonts: list[dict[str, Any]] = field(default_factory=list)
    logos: list[dict[str, Any]] = field(default_factory=list)
    shape: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["valid"] = self.valid
        value["useful"] = bool(self.colours or self.fonts or self.logos or self.shape)
        return value


def _safe_text(path: Path) -> str:
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ValueError(f"file exceeds {MAX_FILE_BYTES:,}-byte inspection limit")
    return path.read_text(encoding="utf-8")


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _is_ignored(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(part in IGNORED_DIRECTORIES for part in parts)


def _append_colour(
    result: InspectionResult,
    *,
    name: str,
    value: str,
    source: str,
    context: str,
    variant: str = "light",
) -> None:
    normalised = value.upper()
    item = {
        "name": name.lstrip("-"),
        "value": normalised,
        "source": source,
        "context": context,
        "variant": variant,
    }
    if item not in result.colours:
        result.colours.append(item)


def inspect_css(path: Path, root: Path, result: InspectionResult) -> None:
    source = _relative(path, root)
    try:
        text = _safe_text(path)
    except (OSError, UnicodeError, ValueError) as exc:
        result.errors.append(f"could not inspect {source}: {exc}")
        return
    result.sources.append({"type": "css", "path": source})
    for selector, body in CSS_BLOCK.findall(text):
        selector_label = " ".join(selector.split()).strip()
        lowered = selector_label.lower()
        variant = (
            "dark"
            if "dark" in lowered or "prefers-color-scheme: dark" in lowered
            else "light"
        )
        context = (
            "theme"
            if ":root" in lowered or "@theme" in lowered or "theme" in lowered
            else "body"
            if re.search(r"(?:^|,)\s*(?:html\s+)?body(?:\s|,|$)", lowered)
            else "component"
        )
        for name, raw_value in CSS_DECLARATION.findall(body):
            colours = HEX_COLOUR.findall(raw_value)
            for colour in colours:
                _append_colour(
                    result,
                    name=name,
                    value=colour,
                    source=source,
                    context=f"{context}:{selector_label}",
                    variant=variant,
                )
            if name in {
                "font-family",
                "--font-heading",
                "--font-body",
                "--font-sans",
                "--font-display",
            }:
                family = raw_value.strip().strip("\"'")
                result.fonts.append(
                    {
                        "name": name.lstrip("-"),
                        "family": family,
                        "source": source,
                        "context": context,
                    }
                )
            if "radius" in name and re.fullmatch(r"\d+(?:\.\d+)?px", raw_value.strip()):
                result.shape.append(
                    {"name": name.lstrip("-"), "value": raw_value.strip(), "source": source}
                )


def inspect_tailwind(path: Path, root: Path, result: InspectionResult) -> None:
    source = _relative(path, root)
    try:
        text = _safe_text(path)
    except (OSError, UnicodeError, ValueError) as exc:
        result.errors.append(f"could not inspect {source}: {exc}")
        return
    result.sources.append({"type": "tailwind", "path": source})
    for name, value in STATIC_PAIR.findall(text):
        if HEX_COLOUR.fullmatch(value):
            _append_colour(
                result,
                name=name,
                value=value,
                source=source,
                context="static-tailwind-token",
            )
    for block in TAILWIND_FONT_BLOCK.findall(text):
        for name, family in TAILWIND_FONT_ENTRY.findall(block):
            result.fonts.append(
                {
                    "name": name,
                    "family": family,
                    "source": source,
                    "context": "tailwind",
                }
            )
    if "function" in text or "require(" in text or "process.env" in text:
        result.warnings.append(
            f"{source} contains dynamic JavaScript; only literal tokens were inspected "
            "and no code was executed"
        )


def _flatten_tokens(value: Any, path: tuple[str, ...] = ()) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    if isinstance(value, dict):
        if "$value" in value or ("value" in value and len(value) <= 4):
            flattened[".".join(path)] = value.get("$value", value.get("value"))
        else:
            for key, child in value.items():
                if not str(key).startswith("$"):
                    flattened.update(_flatten_tokens(child, (*path, str(key))))
    elif path:
        flattened[".".join(path)] = value
    return flattened


def resolve_token_references(tokens: dict[str, Any]) -> dict[str, Any]:
    """Resolve safe, exact local ``{token.path}`` references and reject cycles."""

    resolved: dict[str, Any] = {}

    def resolve(name: str, trail: tuple[str, ...]) -> Any:
        if name in resolved:
            return resolved[name]
        if name in trail:
            cycle = " -> ".join((*trail, name))
            raise TokenReferenceError(f"circular design-token reference: {cycle}")
        if name not in tokens:
            raise TokenReferenceError(f"unknown design-token reference '{{{name}}}'")
        value = tokens[name]
        if isinstance(value, str) and (match := TOKEN_REFERENCE.fullmatch(value.strip())):
            value = resolve(match.group(1), (*trail, name))
        resolved[name] = value
        return value

    for token_name in tokens:
        resolve(token_name, ())
    return resolved


def inspect_token_json(path: Path, root: Path, result: InspectionResult) -> None:
    source = _relative(path, root)
    try:
        text = _safe_text(path)
        document = json.loads(text)
        if not isinstance(document, dict):
            raise ValueError("top level must be an object")
        tokens = resolve_token_references(_flatten_tokens(document))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        result.errors.append(f"could not inspect {source}: {exc}")
        return
    result.sources.append({"type": "tokens", "path": source})
    for name, value in tokens.items():
        if isinstance(value, str) and HEX_COLOUR.fullmatch(value):
            _append_colour(
                result,
                name=name,
                value=value,
                source=source,
                context="design-token",
                variant="dark" if "dark" in name.lower().split(".") else "light",
            )
        elif isinstance(value, str) and any(
            term in name.lower() for term in ("font", "typeface", "typography")
        ):
            result.fonts.append(
                {"name": name, "family": value, "source": source, "context": "design-token"}
            )
        elif isinstance(value, (int, float, str)) and "radius" in name.lower():
            result.shape.append({"name": name, "value": value, "source": source})


def inspect_brand_pack(path: Path, root: Path, result: InspectionResult) -> None:
    brand_path = path / "brand.yaml" if path.is_dir() else path
    source = _relative(brand_path, root)
    try:
        brand = load_structured_file(brand_path)
        validation = validate_document(brand, "brand", source=source)
    except ValueError as exc:
        result.errors.append(str(exc))
        return
    if not validation.valid:
        result.errors.extend(f"{source}: {error}" for error in validation.errors)
        return
    result.sources.append({"type": "brand-pack", "path": source})
    for variant, values in brand["variants"].items():
        for name, colour in values["roles"].items():
            _append_colour(
                result,
                name=name,
                value=colour,
                source=source,
                context="existing-semantic-role",
                variant=variant,
            )
    for role, font in brand["typography"].items():
        result.fonts.append(
            {"name": role, "family": font["family"], "source": source, "context": "brand-pack"}
        )


def inspect_manual(values: dict[str, Any], result: InspectionResult) -> None:
    result.sources.append({"type": "manual", "path": "conversation"})
    for name, value in values.get("colours", {}).items():
        if not isinstance(value, str) or not HEX_COLOUR.fullmatch(value):
            result.errors.append(f"manual colour '{name}' must be a six-digit hex value")
            continue
        _append_colour(
            result, name=str(name), value=value, source="conversation", context="manual"
        )
    for name, family in values.get("fonts", {}).items():
        if isinstance(family, str) and family.strip():
            result.fonts.append(
                {
                    "name": str(name),
                    "family": family.strip(),
                    "source": "conversation",
                    "context": "manual",
                }
            )
    logo = values.get("logo")
    if isinstance(logo, str) and logo:
        result.logos.append({"path": logo, "source": "conversation"})


def inspect_repository(root: Path) -> InspectionResult:
    result = InspectionResult(root=str(root.resolve()))
    if not root.is_dir():
        result.errors.append(f"repository root is not a directory: {root}")
        return result
    files = [path for path in root.rglob("*") if path.is_file() and not _is_ignored(path, root)]
    for path in sorted(files):
        if path.name in TAILWIND_NAMES:
            inspect_tailwind(path, root, result)
        elif path.suffix.lower() in STYLE_SUFFIXES:
            inspect_css(path, root, result)
        elif path.suffix.lower() == ".json" and any(
            word in path.name.lower() for word in ("token", "theme", "design")
        ):
            inspect_token_json(path, root, result)
        elif path.suffix.lower() == ".svg" and any(
            word in path.name.lower() for word in ("logo", "mark", "brand")
        ):
            result.logos.append({"path": _relative(path, root), "source": _relative(path, root)})
    if not result.colours and not result.fonts and not result.logos and not result.errors:
        result.warnings.append("no useful supported brand tokens were found")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?", default=Path.cwd())
    parser.add_argument("--brand-pack", action="store_true")
    parser.add_argument("--manual-json", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.manual_json:
        result = InspectionResult(root=str(Path.cwd()))
        try:
            values = json.loads(args.manual_json.read_text(encoding="utf-8"))
            if not isinstance(values, dict):
                raise ValueError("manual JSON must contain an object")
            inspect_manual(values, result)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            result.errors.append(str(exc))
    elif args.brand_pack:
        result = InspectionResult(root=str(args.source.resolve()))
        root = args.source if args.source.is_dir() else args.source.parent
        inspect_brand_pack(args.source, root, result)
    else:
        result = inspect_repository(args.source)
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
