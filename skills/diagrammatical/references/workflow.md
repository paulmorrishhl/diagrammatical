# Shared workflow

This is the portable orchestration contract used by natural-language activation and every command wrapper.

## Bounded execution contract

A standard creation has these stages, in order:

1. Inspect relevant sources once and model the meaning. Do not reinspect the whole repository after
   `diagram.yaml` is modelled.
2. Select one type, one composition, and one art direction. Load only the matching type reference.
3. Write and validate the semantic YAML.
4. Generate the self-contained HTML and extract its standalone SVG.
5. Run `scripts/self_check.py <diagram-directory> --write-validation` once. This is the canonical
   mechanical check; do not rerun its schema, brand, HTML, SVG, extraction, or PNG subchecks.
6. Perform one visual-review pass when rendering or screenshot capability is available. Otherwise
   record `not-performed` truthfully. Use only an already available tool with a bounded timeout;
   never probe for renderers or launch Chrome/Chromium from an unbounded shell command.
7. Make at most one automatic correction pass, then run the same canonical self-check once more.
8. Deliver, or report a specific blocker. If subjective issues remain after the correction pass,
   retain valid artifacts and report those findings.

Never retry an unchanged failing command or enter a render/review/revise loop. Do not inspect helper
source merely to invoke it. Alternatives, brand onboarding, PNG export, and broad optional audits
are outside the default creation path unless explicitly requested. For diagnostic smoke tests,
record bounded stage outcomes with `scripts/workflow_trace.py`; it stores no prompt or repository
content. Invoke that recorder only at start and final handoff; its final artifact inference fills
the durable stage outcomes without spending a tool turn on every transition.

Reserve the final two turns for the trace update and handoff. Batch related read-only operations:
load the workflow, one type reference, one template, one style, and one brand together; inspect
relevant project sources together. Do not list the entire plugin asset tree, read checked-in
examples, read schemas, inspect helper implementations, call helper `--help`, or load brand-
onboarding guidance during ordinary default-brand creation. Those are not prerequisites for
authoring output with the documented contracts.

## 1. Frame the communication intent

- Identify source material, audience, purpose, primary message, and output context.
- Ask only when missing information would materially change the result; otherwise state a bounded assumption.
- Do not inspect conventional secret files or disclose sensitive values found during repository inspection.

## 2. Model meaning

- Select one supported diagram type from dominant relationship shape: structural components and relationships → architecture; decisions and branches → flowchart; chronological messages → sequence; parent/child pages or navigation → site map; dated tasks on a calendar → Gantt.
- If two views are genuinely useful, recommend a primary and optional companion rather than combining incompatible visual grammars.
- Honour an explicit type unless it would materially misrepresent the source; explain before recommending another type.
- Build or update semantic `diagram.yaml` before rendered outputs.
- Preserve stable IDs for concepts that remain unchanged.
- Record collapsed, omitted, normalised, and assumed content in the fidelity ledger.

## 3. Compose and style

- Select composition from the primary message, relationship pattern, label lengths, grouping, and destination dimensions.
- Apply diagram-type rules, art direction, brand, project defaults, diagram overrides, and output-preset adaptations in the specified precedence order.
- Respect complexity budgets. Never silently delete critical content to make a layout fit.

## 4. Produce outputs

- Save the canonical source, self-contained HTML, standalone SVG, and structured validation report under the configured output directory.
- Escape source text before placing it in HTML or SVG.
- Do not create PNG unless explicitly requested.

## 5. Check quality

- Run schema, graph/reference-integrity, safety, accessibility, and SVG checks through the canonical
  self-check. Direct schema validation is only for the pre-render semantic-source check.
- Inspect one rendered preview when the environment supports it and revise visible defects once.
- Never claim visual review occurred when only source or geometry checks ran.

## 6. Hand off

Report what was created, the selected type/composition/audience/style, material fidelity changes, validation and visual-review outcomes, and paths to deliverables.
