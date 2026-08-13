# Flowchart diagrams

Use this reference for an explicit flowchart request or when the source is primarily a process: ordered work, decisions, outcomes, exceptions, and retries. A flowchart explains what happens next and why. It is not a substitute for an architecture view of stable components and boundaries.

## Selection and communication intent

Select `flowchart` when the primary question is “what happens next?”, “which outcome follows this condition?”, or “how does this process recover?”. Select `architecture` when the primary question is “what are the meaningful system parts, boundaries, and relationships?”. For an ambiguous request, infer from relationship shape and purpose; state the choice. If the user explicitly asks for a flowchart, honour it unless the source has no process semantics, and explain before recommending another type.

Before composing, establish:

- source evidence and process scope;
- audience, purpose, and primary message;
- the successful path and material outcomes;
- decisions and their domain-language branch labels;
- failure, exception, optional, and retry paths;
- assumptions and any content that must be merged or split.

## Semantic source contract

Use the shared diagram schema. Flowchart nodes use `start`, `end`, `outcome`, `process`, `decision`, `state`, `input`, or `note`. Use `start` for each declared entry point, `end` for completion, and `outcome` for a terminal business result. A paired comparison may have one start per trace.

Edges use the shared `kind` plus a semantic `path` role:

- `normal`: the successful or expected journey;
- `conditional`: a labelled decision outcome;
- `failure`: an unsuccessful terminal or rejection route;
- `exception`: an abnormal route that needs handling or recovery;
- `optional`: work that may be skipped;
- `retry`: a loop returning to an earlier step or decision.

Every decision edge has actual text in `label`, using plain domain language such as `Valid`, `Missing details`, or `Approved`. Do not encode branch meaning only in status or colour. Use `groups` with `kind: phase`, `section`, or `workstream` only when phases or comparison lanes materially aid comprehension. Use `presentation.focalNodes` and/or primary node emphasis for no more than two distinct elements.

## Complexity and fidelity

The v1 default budget is 10 visible nodes, 4 decisions, 14 connectors, and 2 focal elements. These are communication budgets, not targets.

When the source exceeds a budget:

1. Preserve the main successful path.
2. Preserve failure or exception paths that materially change understanding.
3. Merge administrative or mechanically repeated steps only when they truthfully travel together.
4. Split an overview from detail flows when the process still exceeds the budget.
5. Never shrink labels or nodes to force the source onto one canvas.
6. Never silently remove a decision or outcome. Record every material merge, omission, normalisation, or assumption in `fidelity`.

Mechanical overflow is a warning because a documented exception can be intentional; ambiguous structure, missing branches, and missing outcomes are errors.

## Treatments

### Nodes, decisions, and states

- Start: compact capsule or circle with the word `Start`; it must be visually and textually explicit.
- End: terminal capsule or double-outline treatment with an explicit completion label.
- Outcome: terminal state card with an outcome noun or short result phrase.
- Process: rectilinear action card with a verb-led label; do not give every process identical emphasis.
- Decision: diamond or clipped-corner decision treatment with one concise question. Put supporting detail beside it when the question would otherwise become unreadable.
- State: state card with a noun-led label; use status roles only when the state truly has that meaning.
- Input: input/document treatment distinct from a process card.
- Focal step or decision: emphasis tint plus stronger rule or annotation; never colour alone and never more than two by default.
- Groups/phases: quiet semantic boundary and visible phase label. Boundaries must not compete with nodes.

Use Editorial Blueprint semantic roles (`canvas`, `surface`, `surfaceSecondary`, `ink`, `inkMuted`, `rule`, `connector`, `emphasisPrimary`, `emphasisPrimaryTint`, `emphasisSecondary`, `external`, `success`, `warning`, `danger`, `deprecated`) rather than raw diagram-specific colours.

### Connectors and path conventions

- Normal: solid, directional, orthogonal where practical; visually dominant through placement and continuity.
- Conditional: solid directional connector with a nearby text label for its outcome.
- Failure: labelled connector plus dash or double-line cue and a failure-shaped/textual destination; colour may reinforce but never carry meaning alone.
- Exception: labelled dashed connector and an exception/recovery label or node treatment. In SVG, set `data-path="exception"`, `data-path-label`, and `data-path-cue` on the connector.
- Optional: labelled dotted or dashed connector with `Optional` or a meaningful condition.
- Retry: labelled return connector with an obvious arrowhead; route outside the main spine and show its exit.

Attach connectors at deliberate sides of nodes. Use arrowheads unless a relation is explicitly non-directional. Do not cross nodes, labels, or decision text. Each decision's outgoing routes must remain individually traceable through placement, label, and attachment point.

### Art directions and templates

- Editorial: generous space, selective annotations, and one restrained focal moment for report-facing process explanations.
- Technical: compact but legible routing, explicit conditions, and contextual implementation detail.
- Executive: fewer stages, outcome-led labels, and a strong primary journey; retain material decisions.
- Clinical: explicit responsibility, safety-led outcomes, and strong non-colour failure/exception cues.
- Neutral: clean, low-expression embedding while preserving all process semantics.

Use `assets/templates/minimal-light.html` or `minimal-dark.html` as the static shell. Replace the sample SVG with the composed flowchart while retaining self-contained CSS, inline SVG, semantic tokens, accessible metadata, and no JavaScript. The LLM owns information design and high-level SVG composition; helpers do not perform automatic layout.

## Composition recipes

These are distinct information structures, not cosmetic variants.

### `linear`

- When to use: a mostly sequential process with few or no decisions.
- When not to use: a process whose meaning depends on several branches or recovery routes.
- Suitable process shapes: onboarding checklists, handoffs, simple production stages.
- Reading direction: left-to-right for short wide sequences or top-to-bottom for document flows.
- Placement rules: one uninterrupted spine, even stage rhythm, start first and end last.
- Decision placement: at most one minor decision; promote to another recipe if it creates substantial branching.
- Branch and merge behaviour: a short optional detour may leave and rejoin once without obscuring the spine.
- Exception-path treatment: place below or outside the spine with a label and dashed cue.
- Connector routing: direct orthogonal segments with consistent attachment points.
- Appropriate audiences: mixed, executive, operational.
- Complexity constraints: normally 3–8 nodes and no more than 1 decision.
- Common failure modes: disguising a branching process as a line, duplicate transition labels, or excessive stage compression.

### `decision-spine`

- When to use: one dominant journey punctuated by decisions that lead to secondary outcomes.
- When not to use: several outcomes are equally important or branches stay separate for most of the process.
- Suitable process shapes: approvals, eligibility, progressive review, guided onboarding.
- Reading direction: top-to-bottom or left-to-right along the primary spine.
- Placement rules: align normal-path steps and decisions on one axis; place secondary outcomes consistently to one side.
- Decision placement: decisions sit on the spine with their successful branch continuing straight.
- Branch and merge behaviour: secondary branches leave orthogonally; only rejoin where the source explicitly reconverges.
- Exception-path treatment: separate from ordinary negative outcomes and use a labelled dashed route.
- Connector routing: maintain one continuous main path and short, clearly separated branch runs.
- Appropriate audiences: mixed, operational, executive.
- Complexity constraints: normally 1–4 decisions within the shared 10-node budget.
- Common failure modes: equally weighting rejection and success, zig-zagging the spine, or leaving branches unlabelled.

### `branching`

- When to use: multiple outcomes or routes are equally meaningful.
- When not to use: one success path clearly dominates and the other routes are exceptions.
- Suitable process shapes: policy selection, triage, routing, multi-outcome eligibility.
- Reading direction: from one top/left entry toward separated outcome regions.
- Placement rules: give sibling branches comparable space and align peer outcomes.
- Decision placement: place the governing decision before the visual split; cascade decisions only with adequate separation.
- Branch and merge behaviour: branches remain separate unless a truthful shared state follows; label every fork.
- Exception-path treatment: reserve a distinct outer lane and add dash/text cues so it is not confused with a peer outcome.
- Connector routing: fan out from distinct ports; avoid shared segments that make destinations ambiguous.
- Appropriate audiences: operational, policy, clinical, mixed.
- Complexity constraints: keep to 4 decisions and 14 connectors; split nested subtrees when labels crowd.
- Common failure modes: hairball routing, false symmetry, tiny diamonds, and branches identifiable only by colour.

### `exception-path`

- When to use: a dominant successful journey has one or more material failure, rejection, or recovery routes.
- When not to use: alternatives are ordinary peer outcomes rather than exceptions.
- Suitable process shapes: validation, submission, payment, deployment, incident recovery.
- Reading direction: success path on a central/top spine; exceptions in a parallel outer lane.
- Placement rules: keep successful steps contiguous and place failure/recovery states in a clearly labelled lane.
- Decision placement: put the relevant decision adjacent to the divergence; keep its success exit on the spine.
- Branch and merge behaviour: recovery may rejoin at the exact retried step; terminal failures do not imply a merge.
- Exception-path treatment: always combine a text label with dash, stroke, or node-shape treatment; use `data-path` SVG metadata.
- Connector routing: route exceptions outside the spine, never behind it, and show loop exits.
- Appropriate audiences: technical, operational, clinical, compliance.
- Complexity constraints: normally one main path plus one or two exception families; split detailed error taxonomies.
- Common failure modes: a coloured red line with no other cue, invisible retry exit, or exceptions visually stronger than success.

### `paired-comparison`

- When to use: two processes, policies, or scenarios should be compared stage by stage.
- When not to use: the traces share too few comparable stages or one trace is merely an exception.
- Suitable process shapes: current/future, manual/automated, policy A/policy B.
- Reading direction: parallel left-to-right or top-to-bottom traces with matched stage order.
- Placement rules: use two labelled lanes, align comparable stages, and expose the point of divergence.
- Decision placement: align equivalent decisions; if only one trace decides, annotate that divergence explicitly.
- Branch and merge behaviour: keep traces separate; a shared destination may align visually but must retain traceable connectors.
- Exception-path treatment: keep exceptions within their owning lane with labels and non-colour cues.
- Connector routing: parallel routes with consistent ports; avoid connectors crossing the comparison gutter.
- Appropriate audiences: executive, policy, transformation, mixed.
- Complexity constraints: usually 3–5 comparable stages per lane and no more than 10 total visible nodes.
- Common failure modes: unaligned stages, cosmetic differences presented as process change, or an unclear divergence point.

## Anti-patterns

- No obvious start or reading direction.
- An unlabelled decision branch or ambiguous arrow.
- Long prose squeezed into a decision diamond.
- Every node rendered as the same rounded rectangle at equal emphasis.
- Failure, exception, or start/end meaning communicated only by colour.
- Retry loops without an explicit exit.
- Connectors crossing through nodes, labels, or each other without traceable routing.
- Repeated labels where position already makes the transition obvious.
- More than two focal elements or pervasive accent colour.
- Tiny text, compressed nodes, or silent omission used to fit one canvas.

## Accessibility and safety

The SVG first child is `<title>`, followed by a useful `<desc>` referenced by `aria-labelledby`; the root carries `role="img"`. The description follows visual reading order and summarises the principal process, decisions, and material outcomes. Branch labels are real SVG `<text>`. Start/end and failure/exception distinctions use words, shape, dash, or stroke treatment. Use safe static HTML/SVG, escape source text, prefix SVG IDs with the diagram slug, and reject scripts, event handlers, remote resources, unsafe links, and ambiguous multi-SVG HTML.

## Validation severity

Errors block handoff: schema violations; unknown endpoints; duplicate IDs; missing start; missing end/outcome; no reachable terminal from a start; decisions with fewer than two outgoing paths; unlabelled decision branches; more than two focal elements; and failure/exception paths without a text-based non-colour cue.

Warnings require explicit review: unreachable or rootless nodes, cycles with no represented exit, and complexity overflow. These may occasionally represent an intentional excerpt or bounded loop, so they do not automatically invalidate source, but checked-in examples must have none.

## Natural-language generation workflow

For “Create a flowchart for this process” or an equivalent request:

1. Inspect the supplied process description, document, and only relevant non-secret repository files.
2. Identify meaningful starts, actions, decisions, outcomes, states, exception/failure paths, optional work, and retry loops.
3. Determine audience, purpose, primary message, and the main successful path.
4. Select one of the five compositions from process shape; do not force the source into a favourite recipe.
5. Apply the complexity budget. Merge only truthful repetition, recommend overview/detail flows where necessary, and record every material simplification.
6. Resolve configuration in shared precedence order without mutating branding inside the installed plugin. If the target lacks project configuration, create it non-destructively under the target project's `.diagrammatical/` only when needed.
7. Create `diagrams/<diagram-slug>/diagram.yaml` and validate it with `<skill-root>/scripts/validate.py --schema diagram`.
8. Start from `<skill-root>/assets/templates/minimal-light.html` or `minimal-dark.html`; compose self-contained HTML containing one accessible inline SVG with semantic theme tokens.
9. Extract `<diagram-slug>.svg` using `<skill-root>/scripts/extract_svg.py`. Never generate PNG by default.
10. Run `<skill-root>/scripts/self_check.py --write-validation`, producing `validation.json`; resolve all errors and review every warning.
11. Render the HTML and perform visual inspection where tooling permits. Check reading order, branch labels, path traceability, exception cues, clipping, overlaps, hierarchy, and contrast. Revise and rerun checks. Record actual findings in `validation.json`; mechanical checks alone are not visual review.
12. Report the four paths, selected composition/style/mode, validation and visual-review outcome, and every merged, collapsed, omitted, normalised, or assumed process concept from the fidelity ledger.

Default output:

```text
diagrams/<diagram-slug>/
├── diagram.yaml
├── <diagram-slug>.html
├── <diagram-slug>.svg
└── validation.json
```
