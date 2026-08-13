# Diagrammatical implementation plan

This plan maps the authoritative specification to seven sequential milestones. Only one milestone is implemented at a time; later milestones remain planned until explicitly started.

## Milestone 1 — Foundation and packaging (completed)

Establish the public repository skeleton, MIT licensing, current Claude Code plugin and marketplace manifests, thin command wrappers, the portable shared skill entry point, Python 3.11 packaging, package verification, CI, contributor guidance, and a minimal outcome-led README.

Verification: validate manifest consistency and resource paths, prove every public command is discoverable, prove `/diagrammatical:create` routes to the shared workflow, run Ruff and Pytest, and run the same checks in CI.

## Milestone 2 — Schemas and default visual system (completed)

Add diagram, brand, and project-config JSON Schemas; safe YAML/schema validation; configuration precedence tests; the Editorial Blueprint brand; five independent art-direction definitions; light and dark base templates; and a role-complete calibration sheet with contrast checks.

Verification: validate representative valid and invalid documents, prove missing edge endpoints fail with named diagnostics and a non-zero CLI result, verify immutable safety precedence, check every required calibration role, run default-identity contrast checks in both modes, render and inspect the calibration sheet, and preserve all Milestone 1 package gates.

## Milestone 3 — Architecture diagrams (implemented; live Claude invocation verification pending)

Add the complete architecture reference, six composition recipes, complexity rules, source-to-output workflow, SVG extraction/validation integration, and at least three reviewed examples with materially different content shapes and fidelity ledgers.

Verification: validate architecture semantics and budgets; run HTML/SVG safety, accessibility, extraction, and self-check coverage; inspect the linear-pipeline, central-platform, and bounded-domains examples in rendered Chromium output; verify the exact four-file deliverable set and absence of PNG; install from an isolated local marketplace; and invoke the create command against a representative repository. The isolated and normal Claude CLI profiles available during implementation were not authenticated, so the final live command invocation must be repeated in an authenticated Claude Code session.

## Milestone 4 — Flowchart (implemented; live Claude invocation verification pending)

Add the complete flowchart reference, five compositions, decision and exception semantics, accessible non-colour-only treatments, overflow/splitting guidance, and at least three reviewed examples.

Verification: validate flowchart semantics and graph integrity; test all five compositions, decision branches, starts/outcomes, retry cycles, complexity and focal budgets, and exception non-colour cues; render and inspect three materially different examples; rerun every architecture self-check; verify the exact four-file deliverable set and absence of PNG; install from an isolated local marketplace; and invoke the shared create command against a representative process fixture. Live invocation requires an authenticated Claude Code session.

## Milestone 5 — Sequence, site map, and Gantt (implemented; live Claude invocation verification pending)

Add full references and reviewed examples for the remaining types, type-specific semantic validation, chronological sequence rules, rooted hierarchy checks, and deterministic Gantt date/duration calculations.

Verification: validate sequence chronology, participants and fragments; validate site-map roots, hierarchy, routes and cross-links; validate Gantt ranges, dependencies, milestones, budgets and inclusive-date geometry; prove exact date-to-coordinate mappings for every checked-in Gantt bar; render and inspect nine materially different examples; rerun all architecture and flowchart self-checks; verify packaging and absence of PNG; install from an isolated local marketplace; and invoke each diagram type through the shared create command. Live invocation requires an authenticated Claude Code session.

## Milestone 6 — Branding workflow (planned)

Add manual and repository-source brand onboarding, CSS/Tailwind/token inspection, semantic mapping and contrast review, calibration approval, project-owned persistence, brand fidelity receipts, and one-off diagram overrides. Plugin installation files remain immutable.

## Milestone 7 — Import, export, and final quality (planned)

Add bounded Mermaid extraction for the three supported grammars, canonical SVG extraction, explicit Playwright PNG export, final self-check orchestration, visual regression coverage, gallery/release tooling, and complete configuration, branding, source-format, and contributor documentation.

## Cross-milestone gates

- Keep the LLM responsible for information design; do not introduce a general layout engine.
- Treat all inspected or imported content as untrusted data.
- Preserve semantic source and fidelity reporting across rendering changes.
- Do not generate PNG during ordinary creation.
- Do not start work assigned to a later milestone merely to make the current milestone appear more complete.
