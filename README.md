# Diagrammatical

Gorgeous, purposeful diagrams generated inside Claude Code — structured, brandable, and easy to revise conversationally.

Diagrammatical is an installable specialist diagram designer. It is being built to inspect source material, decide what a diagram needs to communicate, retain an editable semantic source, and produce self-contained HTML and SVG deliverables with honest validation and fidelity reporting.

## Project status

Diagrammatical supports architecture, flowchart, sequence, site-map/tree, and Gantt diagrams through
one shared workflow. Milestone 6 adds proposal-and-approval brand onboarding from manual values,
existing packs, repository CSS, static Tailwind tokens, supported token JSON, and public websites
using the active agent's available capabilities.

The plugin currently ships Editorial, Technical, Executive, Clinical, and Neutral art directions, light and dark static base templates, and a rendered calibration sheet. Validate a diagram, brand, or project configuration with:

```bash
python skills/diagrammatical/scripts/validate.py path/to/source.yaml --schema diagram --json
```

Diagram output uses the default four-file structure:

```text
diagrams/<diagram-slug>/
├── diagram.yaml
├── <diagram-slug>.html
├── <diagram-slug>.svg
└── validation.json
```

PNG remains explicit-only.

## Project branding

Ask:

```text
Configure Diagrammatical using the branding in this repository.
```

Or run `/diagrammatical:brand`. Diagrammatical proposes semantic mappings, checks contrast,
generates a calibration preview, and requests approval before saving reusable files under
`.diagrammatical/`. Brand identity remains independent from the five built-in art directions, and
one diagram can safely override semantic presentation tokens without changing the shared brand.

See [branding](docs/branding.md) and [configuration](docs/configuration.md) for manual, CSS,
Tailwind, token JSON, website, dark-variant, calibration, and override guidance.

## Install in Claude Code

Once this repository is published:

```text
/plugin marketplace add paulmorrishhl/diagrammatical
/plugin install diagrammatical@diagrammatical
```

Then use ordinary conversation:

```text
Generate an architecture diagram of this repository.
```

Explicit commands are also discoverable:

```text
/diagrammatical:create
/diagrammatical:brand
/diagrammatical:variants
/diagrammatical:restyle
/diagrammatical:import-mermaid
/diagrammatical:validate
/diagrammatical:export
```

## Local development

Requirements: Python 3.11 or newer and a current Claude Code installation.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check .
pytest
python scripts/verify_package.py
```

Test the plugin from a local checkout with either:

```bash
claude --plugin-dir .
```

or add the checkout as a local marketplace in Claude Code:

```text
/plugin marketplace add /absolute/path/to/diagrammatical
/plugin install diagrammatical@diagrammatical
```

## Licence

Diagrammatical is available under the [MIT License](LICENSE).
