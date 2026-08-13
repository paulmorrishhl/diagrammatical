#!/usr/bin/env python3
"""Verify the plugin package and milestone-local resources using the standard library."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_COMMANDS = (
    "create",
    "brand",
    "variants",
    "restyle",
    "import-mermaid",
    "validate",
    "export",
)
SHARED_SKILL = Path("skills/diagrammatical/SKILL.md")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
MILESTONE_2_RESOURCES = (
    "skills/diagrammatical/schemas/diagram.schema.json",
    "skills/diagrammatical/schemas/brand.schema.json",
    "skills/diagrammatical/schemas/config.schema.json",
    "skills/diagrammatical/scripts/validate.py",
    "skills/diagrammatical/scripts/contrast.py",
    "skills/diagrammatical/assets/brands/editorial-blueprint.yaml",
    "skills/diagrammatical/assets/styles/editorial.yaml",
    "skills/diagrammatical/assets/styles/technical.yaml",
    "skills/diagrammatical/assets/styles/executive.yaml",
    "skills/diagrammatical/assets/styles/clinical.yaml",
    "skills/diagrammatical/assets/styles/neutral.yaml",
    "skills/diagrammatical/assets/templates/minimal-light.html",
    "skills/diagrammatical/assets/templates/minimal-dark.html",
    "skills/diagrammatical/assets/templates/calibration-sheet.html",
)
ARCHITECTURE_EXAMPLES = (
    "event-ingestion-pipeline",
    "commerce-control-plane",
    "care-coordination-domains",
)
FLOWCHART_EXAMPLES = (
    "partner-onboarding",
    "document-validation-retry",
    "policy-transition-comparison",
)
MILESTONE_3_RESOURCES = (
    "skills/diagrammatical/references/types/architecture.md",
    "skills/diagrammatical/scripts/validate_svg.py",
    "skills/diagrammatical/scripts/extract_svg.py",
    "skills/diagrammatical/scripts/self_check.py",
)
MILESTONE_4_RESOURCES = ("skills/diagrammatical/references/types/flowchart.md",)
SEQUENCE_EXAMPLES = ("catalogue-request", "token-refresh", "order-event")
SITEMAP_EXAMPLES = ("marketing-site", "product-areas", "support-hub")
GANTT_EXAMPLES = ("mobile-launch", "platform-workstreams", "release-gates")
MILESTONE_5_RESOURCES = (
    "skills/diagrammatical/references/types/sequence.md",
    "skills/diagrammatical/references/types/sitemap.md",
    "skills/diagrammatical/references/types/gantt.md",
    "skills/diagrammatical/scripts/gantt_dates.py",
)


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing required JSON file: {path.relative_to(ROOT)}")
        return {}
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"expected an object in {path.relative_to(ROOT)}")
        return {}
    return value


def verify_repository(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    plugin_path = root / ".claude-plugin/plugin.json"
    marketplace_path = root / ".claude-plugin/marketplace.json"
    agents_marketplace_path = root / ".agents/plugins/marketplace.json"

    plugin = load_json(plugin_path, errors)
    marketplace = load_json(marketplace_path, errors)
    agents_marketplace = load_json(agents_marketplace_path, errors)

    if plugin.get("name") != "diagrammatical":
        errors.append("plugin manifest name must be 'diagrammatical'")
    version = plugin.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        errors.append("plugin manifest version must be strict semantic versioning")
    if plugin.get("commands") != "./commands/":
        errors.append("plugin manifest must discover the root commands directory")
    if plugin.get("skills") != "./skills/":
        errors.append("plugin manifest must discover the shared skills directory")

    entries = marketplace.get("plugins")
    if marketplace.get("name") != "diagrammatical":
        errors.append("Claude marketplace name must be 'diagrammatical'")
    if not isinstance(entries, list) or len(entries) != 1:
        errors.append("Claude marketplace must contain exactly one plugin entry")
    else:
        entry = entries[0]
        if not isinstance(entry, dict):
            errors.append("Claude marketplace plugin entry must be an object")
        else:
            if entry.get("name") != plugin.get("name"):
                errors.append("Claude marketplace and plugin manifest names must match")
            if entry.get("version") != plugin.get("version"):
                errors.append("Claude marketplace and plugin manifest versions must match")
            if entry.get("source") != "./":
                errors.append("Claude marketplace plugin source must be the repository root")

    if agents_marketplace.get("name") != "diagrammatical":
        errors.append("Codex compatibility marketplace name must be 'diagrammatical'")
    if not isinstance(agents_marketplace.get("plugins"), list):
        errors.append("Codex compatibility marketplace plugins must be an array")

    skill_path = root / SHARED_SKILL
    if not skill_path.is_file():
        errors.append(f"missing shared skill: {SHARED_SKILL}")
    else:
        skill = skill_path.read_text(encoding="utf-8")
        if not skill.startswith("---\n") or "name: diagrammatical" not in skill:
            errors.append("shared skill must contain discoverable Diagrammatical frontmatter")
        workflow = root / "skills/diagrammatical/references/workflow.md"
        if not workflow.is_file():
            errors.append("shared skill references a missing workflow file")

    for command in PUBLIC_COMMANDS:
        command_path = root / "commands" / f"{command}.md"
        if not command_path.is_file():
            errors.append(f"missing public command: commands/{command}.md")
            continue
        content = command_path.read_text(encoding="utf-8")
        if not content.startswith("---\n") or "description:" not in content:
            errors.append(f"command {command} must contain description frontmatter")
        if SHARED_SKILL.as_posix() not in content:
            errors.append(f"command {command} must route to the shared skill")

    for required in ("README.md", "LICENSE", "SPEC.md", "pyproject.toml"):
        if not (root / required).is_file():
            errors.append(f"missing repository file: {required}")

    for resource in MILESTONE_2_RESOURCES:
        resource_path = root / resource
        if not resource_path.is_file():
            errors.append(f"missing Milestone 2 resource: {resource}")
        elif resource_path.suffix == ".json":
            load_json(resource_path, errors)

    for resource in MILESTONE_3_RESOURCES:
        if not (root / resource).is_file():
            errors.append(f"missing Milestone 3 resource: {resource}")

    for resource in MILESTONE_4_RESOURCES:
        if not (root / resource).is_file():
            errors.append(f"missing Milestone 4 resource: {resource}")

    for resource in MILESTONE_5_RESOURCES:
        if not (root / resource).is_file():
            errors.append(f"missing Milestone 5 resource: {resource}")

    examples_root = root / "skills/diagrammatical/assets/examples/architecture"
    discovered_examples = (
        {path.name for path in examples_root.iterdir() if path.is_dir()}
        if examples_root.is_dir()
        else set()
    )
    if discovered_examples != set(ARCHITECTURE_EXAMPLES):
        errors.append(
            "architecture examples must match the reviewed Milestone 3 set: "
            + ", ".join(ARCHITECTURE_EXAMPLES)
        )
    for slug in ARCHITECTURE_EXAMPLES:
        example_dir = examples_root / slug
        expected = {"diagram.yaml", f"{slug}.html", f"{slug}.svg", "validation.json"}
        if example_dir.is_dir():
            found = {path.name for path in example_dir.iterdir() if path.is_file()}
            if found != expected:
                errors.append(
                    f"architecture example {slug} must contain exactly: "
                    + ", ".join(sorted(expected))
                )
            if list(example_dir.glob("*.png")):
                errors.append(f"architecture example {slug} must not include a default PNG")

    flowchart_root = root / "skills/diagrammatical/assets/examples/flowchart"
    discovered_flowcharts = (
        {path.name for path in flowchart_root.iterdir() if path.is_dir()}
        if flowchart_root.is_dir()
        else set()
    )
    if discovered_flowcharts != set(FLOWCHART_EXAMPLES):
        errors.append(
            "flowchart examples must match the reviewed Milestone 4 set: "
            + ", ".join(FLOWCHART_EXAMPLES)
        )
    for slug in FLOWCHART_EXAMPLES:
        example_dir = flowchart_root / slug
        expected = {"diagram.yaml", f"{slug}.html", f"{slug}.svg", "validation.json"}
        if example_dir.is_dir():
            found = {path.name for path in example_dir.iterdir() if path.is_file()}
            if found != expected:
                errors.append(
                    f"flowchart example {slug} must contain exactly: " + ", ".join(sorted(expected))
                )
            if list(example_dir.glob("*.png")):
                errors.append(f"flowchart example {slug} must not include a default PNG")

    milestone_5_examples = {
        "sequence": SEQUENCE_EXAMPLES,
        "sitemap": SITEMAP_EXAMPLES,
        "gantt": GANTT_EXAMPLES,
    }
    for example_type, slugs in milestone_5_examples.items():
        example_root = root / "skills/diagrammatical/assets/examples" / example_type
        discovered = (
            {path.name for path in example_root.iterdir() if path.is_dir()}
            if example_root.is_dir()
            else set()
        )
        if discovered != set(slugs):
            errors.append(
                f"{example_type} examples must match the reviewed Milestone 5 set: "
                + ", ".join(slugs)
            )
        for slug in slugs:
            example_dir = example_root / slug
            expected = {"diagram.yaml", f"{slug}.html", f"{slug}.svg", "validation.json"}
            if example_dir.is_dir():
                found = {path.name for path in example_dir.iterdir() if path.is_file()}
                if found != expected:
                    errors.append(
                        f"{example_type} example {slug} must contain exactly: "
                        + ", ".join(sorted(expected))
                    )
                if list(example_dir.glob("*.png")):
                    errors.append(f"{example_type} example {slug} must not include a default PNG")

    project_configuration_in_plugin = list(
        (root / "skills/diagrammatical").rglob(".diagrammatical")
    )
    if project_configuration_in_plugin:
        errors.append("user-owned .diagrammatical configuration must not be stored in the plugin")

    return errors


def main() -> int:
    errors = verify_repository()
    if errors:
        print("Package verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "Package verification passed: manifests, commands, shared skill, schemas, and "
        "visual-system resources and all five diagram-type example sets are coherent."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
