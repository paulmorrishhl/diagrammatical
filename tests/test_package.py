from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.verify_package import (
    ARCHITECTURE_EXAMPLES,
    FLOWCHART_EXAMPLES,
    GANTT_EXAMPLES,
    MILESTONE_2_RESOURCES,
    MILESTONE_3_RESOURCES,
    MILESTONE_4_RESOURCES,
    MILESTONE_5_RESOURCES,
    PUBLIC_COMMANDS,
    ROOT,
    SEQUENCE_EXAMPLES,
    SITEMAP_EXAMPLES,
    verify_repository,
)


class PackageTests(unittest.TestCase):
    def test_repository_package_is_coherent(self) -> None:
        self.assertEqual(verify_repository(), [])

    def test_public_commands_are_present(self) -> None:
        discovered = {path.stem for path in (ROOT / "commands").glob("*.md")}
        self.assertEqual(discovered, set(PUBLIC_COMMANDS))

    def test_create_command_routes_to_shared_workflow(self) -> None:
        create_command = (ROOT / "commands/create.md").read_text(encoding="utf-8")
        self.assertIn("skills/diagrammatical/SKILL.md", create_command)
        self.assertIn("communication purpose and audience", create_command)
        self.assertIn("Do not read helper implementations", create_command)
        self.assertIn("one automatic correction", create_command)

    def test_validate_command_invokes_only_the_canonical_checker(self) -> None:
        validate_command = (ROOT / "commands/validate.md").read_text(encoding="utf-8")
        self.assertIn("invoke the canonical checker exactly once", validate_command)
        self.assertIn("self_check.py", validate_command)
        self.assertIn("Do not read helper implementations", validate_command)

    def test_manifest_versions_are_consistent(self) -> None:
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads(
            (ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8")
        )
        self.assertEqual(marketplace["plugins"][0]["version"], plugin["version"])

    def test_verifier_resolves_repository_independently_of_cwd(self) -> None:
        unrelated_path = Path("/tmp")
        self.assertNotEqual(unrelated_path, ROOT)
        self.assertEqual(verify_repository(ROOT), [])

    def test_milestone_2_resources_ship_inside_the_plugin(self) -> None:
        for resource in MILESTONE_2_RESOURCES:
            self.assertTrue((ROOT / resource).is_file(), resource)

    def test_milestone_3_resources_and_examples_ship_inside_the_plugin(self) -> None:
        for resource in MILESTONE_3_RESOURCES:
            self.assertTrue((ROOT / resource).is_file(), resource)
        examples = ROOT / "skills/diagrammatical/assets/examples/architecture"
        self.assertEqual(
            {path.name for path in examples.iterdir() if path.is_dir()},
            set(ARCHITECTURE_EXAMPLES),
        )

    def test_milestone_4_resources_and_examples_ship_inside_the_plugin(self) -> None:
        for resource in MILESTONE_4_RESOURCES:
            self.assertTrue((ROOT / resource).is_file(), resource)
        examples = ROOT / "skills/diagrammatical/assets/examples/flowchart"
        self.assertEqual(
            {path.name for path in examples.iterdir() if path.is_dir()},
            set(FLOWCHART_EXAMPLES),
        )

    def test_milestone_5_resources_and_examples_ship_inside_the_plugin(self) -> None:
        for resource in MILESTONE_5_RESOURCES:
            self.assertTrue((ROOT / resource).is_file(), resource)
        for kind, expected in (
            ("sequence", SEQUENCE_EXAMPLES),
            ("sitemap", SITEMAP_EXAMPLES),
            ("gantt", GANTT_EXAMPLES),
        ):
            root = ROOT / "skills/diagrammatical/assets/examples" / kind
            self.assertEqual({path.name for path in root.iterdir() if path.is_dir()}, set(expected))


if __name__ == "__main__":
    unittest.main()
