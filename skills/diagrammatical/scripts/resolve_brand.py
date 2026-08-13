#!/usr/bin/env python3
"""Map inspected values and resolve Diagrammatical brand configuration with provenance."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

try:
    from .contrast import contrast_ratio
    from .validate import validate_document
except ImportError:
    from contrast import contrast_ratio
    from validate import validate_document

COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")
ROLE_NAMES = (
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
)
LIGHT_DEFAULTS = {
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
DARK_DEFAULTS = {
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
STATUS_TERMS = {
    "success": ("success", "positive", "green"),
    "warning": ("warning", "warn", "amber", "orange"),
    "danger": ("danger", "error", "destructive", "red"),
}
ROLE_TERMS = {
    "canvas": ("canvas", "page-background", "body-background", "background"),
    "surface": ("surface", "card", "container", "panel"),
    "surfaceSecondary": ("surface-secondary", "muted-background", "subtle"),
    "ink": ("foreground", "text-primary", "text", "ink"),
    "inkMuted": ("muted-foreground", "text-secondary", "muted", "subtext"),
    "rule": ("border", "rule", "divider", "hairline"),
    "emphasisPrimary": ("primary", "brand", "accent", "cta"),
    "emphasisSecondary": ("secondary", "accent-secondary"),
    "external": ("link", "api", "information", "info"),
    **STATUS_TERMS,
}
IMMUTABLE_SAFETY_PATHS = {
    "accessibility.statusRequiresNonColourCue",
    "accessibility.neverUseColourAlone",
    "safety.scripts",
    "safety.remoteResources",
}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "custom-brand"


def _mix(first: str, second: str, amount: float) -> str:
    left = [int(first[index : index + 2], 16) for index in (1, 3, 5)]
    right = [int(second[index : index + 2], 16) for index in (1, 3, 5)]
    values = [round(a + (b - a) * amount) for a, b in zip(left, right, strict=True)]
    return "#" + "".join(f"{value:02X}" for value in values)


def _normalise_name(item: Mapping[str, Any]) -> str:
    return str(item.get("name", "")).lower().replace("_", "-").replace(".", "-")


def _candidate_score(item: Mapping[str, Any], terms: Sequence[str]) -> int:
    name = _normalise_name(item)
    context = str(item.get("context", "")).lower()
    score = max((10 - index for index, term in enumerate(terms) if term in name), default=0)
    if score == 0:
        return 0
    if item.get("context") == "manual":
        score += 20
    if context.startswith("theme") or "existing-semantic-role" in context:
        score += 8
    if ":root" in context:
        score += 4
    if context.startswith("component"):
        score -= 3
    return score


def _choose(
    colours: Sequence[Mapping[str, Any]], role: str, variant: str
) -> tuple[str | None, Mapping[str, Any] | None, list[Mapping[str, Any]]]:
    candidates = [item for item in colours if item.get("variant", "light") == variant]
    terms = ROLE_TERMS.get(role, (role.lower(),))
    ranked = sorted(
        ((item, _candidate_score(item, terms)) for item in candidates),
        key=lambda pair: pair[1],
        reverse=True,
    )
    positive = [pair for pair in ranked if pair[1] > 0]
    if not positive:
        return None, None, []
    winner, score = positive[0]
    ambiguous = [item for item, candidate_score in positive[1:] if candidate_score == score]
    return str(winner["value"]).upper(), winner, ambiguous


def _font_choice(fonts: Sequence[Mapping[str, Any]], role: str, fallback: str) -> str:
    terms = (role, "display" if role == "heading" else "sans")
    for item in fonts:
        if any(term in _normalise_name(item) for term in terms):
            return str(item["family"]).split(",")[0].strip().strip("\"'")
    return fallback


def _palette_from_roles(roles: Mapping[str, str]) -> dict[str, str]:
    return {role: colour for role, colour in roles.items()}


def _variant_from_candidates(
    colours: Sequence[Mapping[str, Any]],
    variant: str,
    receipt: dict[str, Any],
    *,
    generated: bool = False,
) -> dict[str, Any]:
    defaults = DARK_DEFAULTS if variant == "dark" else LIGHT_DEFAULTS
    roles: dict[str, str] = {}
    for role in ROLE_NAMES:
        value, source, ambiguous = _choose(colours, role, variant)
        if value is None:
            value = defaults[role]
            receipt["fallbacks"].append(
                {
                    "variant": variant,
                    "role": role,
                    "value": value,
                    "reason": "no unambiguous source value",
                }
            )
        else:
            receipt["mappings"].append(
                {
                    "variant": variant,
                    "role": role,
                    "sourceName": source.get("name") if source else None,
                    "sourceValue": source.get("value") if source else None,
                    "resolvedValue": value,
                    "source": source.get("source") if source else None,
                }
            )
        if ambiguous:
            receipt["ambiguities"].append(
                {
                    "variant": variant,
                    "role": role,
                    "selected": source.get("name") if source else None,
                    "alternatives": [item.get("name") for item in ambiguous],
                }
            )
        roles[role] = value
    # Normal connectors deliberately inherit a neutral role, never the brand accent.
    roles["connector"] = roles["inkMuted"]
    if not any(_choose(colours, role, variant)[0] for role in STATUS_TERMS):
        receipt["warnings"].append(
            f"{variant} source contained no semantic status colours; accessible "
            "Diagrammatical defaults were used"
        )
    tint_value, _, _ = _choose(colours, "emphasisPrimaryTint", variant)
    if tint_value is None or roles["emphasisPrimaryTint"] == roles["emphasisPrimary"]:
        roles["emphasisPrimaryTint"] = _mix(
            roles["emphasisPrimary"], roles["canvas"], 0.86 if variant == "light" else 0.72
        )
        for fallback in receipt["fallbacks"]:
            if fallback["variant"] == variant and fallback["role"] == "emphasisPrimaryTint":
                fallback["value"] = roles["emphasisPrimaryTint"]
                fallback["reason"] = "derived from primary accent and canvas"
    return {"palette": _palette_from_roles(roles), "roles": roles, "generated": generated}


def map_inspection_to_brand(
    inspection: Mapping[str, Any],
    *,
    name: str,
    brand_id: str | None = None,
    include_dark: bool | None = None,
    allow_adjustments: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Map an inspection digest into the existing Diagrammatical brand format."""

    brand_slug = brand_id or _slug(name)
    colours = [item for item in inspection.get("colours", []) if isinstance(item, Mapping)]
    fonts = [item for item in inspection.get("fonts", []) if isinstance(item, Mapping)]
    sources = [dict(item) for item in inspection.get("sources", []) if isinstance(item, Mapping)]
    receipt: dict[str, Any] = {
        "schemaVersion": 1,
        "brand": brand_slug,
        "sources": sources,
        "extracted": {
            "colours": [dict(item) for item in colours],
            "fonts": [dict(item) for item in fonts],
            "logos": list(inspection.get("logos", [])),
            "shape": list(inspection.get("shape", [])),
        },
        "mappings": [],
        "adjustments": [],
        "fallbacks": [],
        "ambiguities": [],
        "warnings": list(inspection.get("warnings", [])),
        "missingAssets": [],
        "contrast": [],
        "policies": {
            "maximumPrimaryFocalElements": 2,
            "normalConnectors": "neutral",
            "colourAlone": "prohibited",
        },
        "approvedAt": None,
    }
    variants = {"light": _variant_from_candidates(colours, "light", receipt)}
    has_dark = any(item.get("variant") == "dark" for item in colours)
    if include_dark is True and not has_dark:
        variants["dark"] = {
            "palette": dict(DARK_DEFAULTS),
            "roles": dict(DARK_DEFAULTS),
            "generated": True,
        }
        variants["dark"]["roles"]["emphasisPrimary"] = _mix(
            variants["light"]["roles"]["emphasisPrimary"], "#FFFFFF", 0.45
        )
        variants["dark"]["roles"]["emphasisSecondary"] = _mix(
            variants["light"]["roles"]["emphasisSecondary"], "#FFFFFF", 0.4
        )
        variants["dark"]["roles"]["connector"] = variants["dark"]["roles"]["inkMuted"]
        variants["dark"]["palette"] = dict(variants["dark"]["roles"])
        receipt["warnings"].append(
            "dark variant was derived from accessible dark defaults and brand accents; "
            "approval is required before reuse"
        )
    elif has_dark and include_dark is not False:
        variants["dark"] = _variant_from_candidates(colours, "dark", receipt)
    brand: dict[str, Any] = {
        "schemaVersion": 1,
        "id": brand_slug,
        "name": name,
        "description": f"Project-owned Diagrammatical identity for {name}.",
        "typography": {
            "heading": {
                "family": _font_choice(fonts, "heading", "Georgia"),
                "fallbacks": ["Arial", "sans-serif"],
                "weight": 600,
            },
            "body": {
                "family": _font_choice(fonts, "body", "Inter"),
                "fallbacks": ["Arial", "sans-serif"],
                "weight": 400,
            },
            "label": {
                "family": _font_choice(fonts, "label", "Inter"),
                "fallbacks": ["Arial", "sans-serif"],
                "weight": 600,
            },
            "technical": {
                "family": _font_choice(fonts, "technical", "IBM Plex Mono"),
                "fallbacks": ["monospace"],
                "weight": 400,
            },
        },
        "logo": {"source": None, "placements": [], "maximumWidth": 96},
        "shape": {"cornerCharacter": "small", "radius": 8, "nodePadding": 16, "maxNodeWidth": 280},
        "stroke": {"borderWidth": 1, "ruleWidth": 1},
        "connectors": {"weight": 2, "curvature": "orthogonal", "arrowhead": "line"},
        "icons": {"family": "geometric-line", "customDirectory": None},
        "density": "balanced",
        "accessibility": {
            "normalTextContrast": 4.5,
            "largeTextContrast": 3.0,
            "allowDerivedColours": allow_adjustments,
            "statusRequiresNonColourCue": True,
        },
        "variants": variants,
    }
    logo_candidates = receipt["extracted"]["logos"]
    if logo_candidates:
        brand["logo"]["source"] = "./logo.svg"
        brand["logo"]["placements"] = ["footer-right"]
    receipt["typography"] = {
        role: {
            "family": font["family"],
            "weight": font["weight"],
            "fallbacks": font["fallbacks"],
        }
        for role, font in brand["typography"].items()
    }
    return brand, receipt


def validate_diagram_overrides(
    brand: Mapping[str, Any], mode: str, overrides: Mapping[str, Any]
) -> list[str]:
    errors: list[str] = []
    variant = brand.get("variants", {}).get(mode)
    if not isinstance(variant, Mapping):
        return [f"brand '{brand.get('id')}' has no {mode!r} variant"]
    allowed = set(ROLE_NAMES) | {"connectorWidth", "nodeRadius", "density"}
    for key, value in overrides.items():
        if key not in allowed:
            errors.append(f"unknown diagram override '{key}'")
        elif key in ROLE_NAMES and (not isinstance(value, str) or not COLOUR.fullmatch(value)):
            errors.append(f"diagram override '{key}' must be a six-digit hex colour")
    forbidden = set(overrides) & {path.rsplit(".", 1)[-1] for path in IMMUTABLE_SAFETY_PATHS}
    if forbidden:
        errors.append(
            "diagram overrides cannot disable required safety: "
            + ", ".join(sorted(forbidden))
        )
    roles = dict(variant.get("roles", {}))
    roles.update({key: value for key, value in overrides.items() if key in ROLE_NAMES})
    minimum = float(brand.get("accessibility", {}).get("normalTextContrast", 4.5))
    for foreground, background in (("ink", "canvas"), ("ink", "surface"), ("inkMuted", "canvas")):
        if foreground in roles and background in roles:
            ratio = contrast_ratio(roles[foreground], roles[background])
            if ratio < minimum:
                errors.append(
                    f"diagram override resolves {foreground} on {background} to "
                    f"{ratio:.2f}:1, below {minimum:.2f}:1"
                )
    return errors


def resolve_diagram_brand(
    brand: Mapping[str, Any], mode: str, overrides: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Resolve one diagram's isolated brand tokens and report override provenance."""

    selected = brand.get("variants", {}).get(mode)
    if not isinstance(selected, Mapping):
        return {
            "valid": False,
            "errors": [f"brand '{brand.get('id')}' has no {mode!r} variant"],
        }
    requested = dict(overrides or {})
    errors = validate_diagram_overrides(brand, mode, requested)
    if errors:
        return {"valid": False, "errors": errors}
    roles = dict(selected["roles"])
    provenance = {role: f"brand:{brand.get('id')}:{mode}" for role in roles}
    applied: dict[str, Any] = {}
    presentation: dict[str, Any] = {}
    for key, value in requested.items():
        if key in ROLE_NAMES:
            roles[key] = value
            provenance[key] = "diagram-override"
        else:
            presentation[key] = value
        applied[key] = value
    return {
        "valid": True,
        "brand": brand.get("id"),
        "mode": mode,
        "roles": roles,
        "presentation": presentation,
        "appliedOverrides": applied,
        "provenance": provenance,
    }


def write_mapping(brand: Mapping[str, Any], receipt: Mapping[str, Any], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "brand.yaml").write_text(
        yaml.safe_dump(dict(brand), sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    (directory / "fidelity.json").write_text(
        json.dumps(dict(receipt), indent=2) + "\n", encoding="utf-8"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inspection", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--id")
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    inspection = json.loads(args.inspection.read_text(encoding="utf-8"))
    brand, receipt = map_inspection_to_brand(
        inspection, name=args.name, brand_id=args.id, include_dark=args.dark
    )
    validation = validate_document(brand, "brand")
    payload = {
        "valid": validation.valid,
        "brand": brand,
        "fidelity": receipt,
        "errors": validation.errors,
    }
    if args.output and validation.valid:
        write_mapping(brand, receipt, args.output)
    print(json.dumps(payload, indent=2))
    return 0 if validation.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
