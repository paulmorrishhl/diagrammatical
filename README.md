# Diagrammatical

Gorgeous, purposeful diagrams generated inside Claude Code — structured, brandable, and easy to revise conversationally.

Diagrammatical is an installable specialist diagram designer. It is being built to inspect source material, decide what a diagram needs to communicate, retain an editable semantic source, and produce self-contained HTML and SVG deliverables with honest validation and fidelity reporting.

## Project status

Milestone 3 adds the complete repository-to-architecture workflow, six intentional architecture compositions, safe HTML/SVG validation, standalone SVG extraction, structured self-checks, and three visually reviewed examples. Flowchart, sequence, site-map, and Gantt generation remain later milestones; see [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

The plugin currently ships Editorial, Technical, Executive, Clinical, and Neutral art directions, light and dark static base templates, and a rendered calibration sheet. Validate a diagram, brand, or project configuration with:

```bash
python skills/diagrammatical/scripts/validate.py path/to/source.yaml --schema diagram --json
```

Architecture output uses the default four-file structure:

```text
diagrams/<diagram-slug>/
├── diagram.yaml
├── <diagram-slug>.html
├── <diagram-slug>.svg
└── validation.json
```

The supported architecture compositions are `linear-pipeline`, `layered-stack`,
`central-platform`, `hub-and-spoke`, `bounded-domains`, and `current-future`. PNG remains
explicit-only.

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
