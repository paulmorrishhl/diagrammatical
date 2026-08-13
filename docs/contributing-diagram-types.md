# Contributing diagram types

v0.1.0 supports exactly architecture, flowchart, sequence, site map/tree and Gantt. Propose a new
type before implementation. A contribution needs a semantic model, selection guidance, materially
different compositions, complexity budget, accessibility and safety rules, validation with error/
warning rationale, reviewed examples, visual baselines, workflow integration and regression tests.

Keep command wrappers as routing text. The shared skill owns orchestration; Python owns bounded
parsing, validation, extraction and date math; the agent owns information design and SVG composition.
Do not add a general layout engine or encode an art direction into a brand.

Run Ruff, the complete Pytest suite, package verification, release checks, all example self-checks,
visual regression and `git diff --check`. Baselines change only after a maintainer renders, inspects
and explicitly runs the documented update command.
