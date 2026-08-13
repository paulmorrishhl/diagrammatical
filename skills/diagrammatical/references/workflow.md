# Shared workflow

This is the portable orchestration contract used by natural-language activation and every command wrapper.

## 1. Frame the communication intent

- Identify source material, audience, purpose, primary message, and output context.
- Ask only when missing information would materially change the result; otherwise state a bounded assumption.
- Do not inspect conventional secret files or disclose sensitive values found during repository inspection.

## 2. Model meaning

- Select one supported diagram type from the structure of the information. Choose architecture for stable components, boundaries, and relationships; choose flowchart for ordered steps, decisions, outcomes, and exception paths. If an ambiguous request could fit either, use the purpose and dominant relationship shape, then state the choice.
- Honour an explicit flowchart request unless it would misrepresent source with no process semantics; explain before recommending another type.
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

- Run schema, graph/reference-integrity, safety, accessibility, and SVG checks that exist for the current milestone.
- Validate YAML/JSON with `scripts/validate.py`; select the diagram, brand, or config schema explicitly when the filename is ambiguous.
- Inspect a rendered preview when the environment supports it and revise visible defects.
- Never claim visual review occurred when only source or geometry checks ran.

## 6. Hand off

Report what was created, the selected type/composition/audience/style, material fidelity changes, validation and visual-review outcomes, and paths to deliverables.
