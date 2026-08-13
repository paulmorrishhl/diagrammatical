# Gantt diagrams

Use Gantt for dated tasks, phases, milestones and dependencies. Do not use it for undated roadmaps or chronological messages between systems.

## Semantic and deterministic grammar

`gantt.planStart` and `planEnd` bound the plan; `scale` is `week`, `month`, or `quarter`. Tasks have stable IDs, labels, ISO `start`, and either ISO `end` or positive `durationDays`; optional fields cover phase, workstream, milestone, dependencies, progress, owner, status and critical emphasis. Dates are inclusive: a task from 2026-09-01 through 2026-09-12 lasts 12 calendar days. Same-day tasks last one inclusive day; milestones must start and end on the same date.

Use `scripts/gantt_dates.py` for strict ISO parsing, inclusive durations, derived ends, scale recommendation and bounded date coordinates. Bar positions must come from these calculations. Ambiguous input such as `03/04/2027` requires clarification or a recorded locale assumption; missing dates are never invented. Progress appears only when supplied. Critical-path emphasis requires dependency evidence or explicit user identification and is limited to one primary emphasis.

Budget: 12 tasks, 4 workstreams, 8 milestones, 1 critical emphasis. Group truthful phases, remove low-value subtask detail, preserve milestones/dependencies, recommend overview plus workstream detail, and record every collapsed task.

## Compositions

### `phased-plan`

- When to use: delivery progresses through sequential or overlapping phases.
- When not to use: parallel team ownership or milestones dominate.
- Scale selection: week for short plans, month for medium, quarter for long.
- Task/phase placement: phase bands group ordered task rows.
- Workstreams: secondary labels only when useful.
- Dependencies: restrained orthogonal arrows between dependent bars.
- Milestones: diamonds on exact dates.
- Critical path: one labelled emphasis only with evidence.
- Audiences: delivery, mixed, executive.
- Complexity: 12 tasks; collapse administrative subtasks.
- Failure modes: manually estimated bars, phase dates inconsistent with tasks, dense grid.

### `workstreams`

- When to use: parallel teams or disciplines are the primary structure.
- When not to use: a single phased plan is clearer.
- Scale selection: chosen deterministically from plan span and audience.
- Task/phase placement: rows grouped by workstream with aligned calendar grid.
- Workstreams: maximum four visible groups in an overview.
- Dependencies: cross-workstream arrows only when material.
- Milestones: align shared milestones across rows.
- Critical path: restrained and dependency-supported.
- Audiences: programme, technical, operational.
- Complexity: 4 workstreams and 12 tasks.
- Failure modes: swimlane process grammar, unreadable labels, implied progress.

### `milestone-led`

- When to use: commitments, gates or release dates are the primary message.
- When not to use: task duration and ownership need equal emphasis.
- Scale selection: month or quarter commonly; validate against actual span.
- Task/phase placement: supporting bars lead visually to milestone diamonds.
- Workstreams: quiet grouping beneath milestone narrative.
- Dependencies: show only those governing milestone readiness.
- Milestones: prominent labelled diamonds on mathematically exact dates.
- Critical path: one evidence-backed chain or none.
- Audiences: executive, release, mixed.
- Complexity: at most 8 milestones and 12 tasks.
- Failure modes: milestone diamonds with duration, decorative dates, false critical path.

## Accessibility, safety, and anti-patterns

The accessible description states inclusive plan range, scale, workstream/phase order, material dependencies and milestones. Task labels and dates are visible text. Milestones use diamonds; status uses text/pattern/stroke in addition to colour. Avoid arbitrary geometry, dates outside range, missing dates, reversed ranges, invented progress, unsupported critical paths, excessive grids, squeezed long programmes and duration bars for milestones. Use Editorial Blueprint roles, light/dark templates, safe SVG and the shared extraction/self-check workflow.

## Natural-language workflow

For “Create a Gantt diagram from this delivery plan”: inspect dated source; establish purpose, audience and message; clarify or record ambiguous dates; model tasks, groups, dependencies and milestones; select composition and deterministic scale; validate/derive dates with `gantt_dates.py`; write `diagram.yaml`; calculate every bar coordinate from plan dates; compose HTML/SVG; extract; self-check to `validation.json`; render and inspect; report fidelity and date assumptions. Output the standard four files and never generate PNG by default.
