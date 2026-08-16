---
description: Create a purposeful diagram from a repository, notes, or other source material
argument-hint: "[request or source]"
---

Apply the shared workflow in `skills/diagrammatical/SKILL.md` to create a diagram from the user's request and `$ARGUMENTS`.

Start by establishing the communication purpose and audience. Inspect only relevant, non-secret project sources. Keep the semantic source as the canonical editable artefact, report material simplifications, and do not claim completion until the available validation and visual-review checks have run.

Load exactly one matching type reference: `skills/diagrammatical/references/types/architecture.md`,
`skills/diagrammatical/references/types/flowchart.md`,
`skills/diagrammatical/references/types/sequence.md`,
`skills/diagrammatical/references/types/sitemap.md`, or
`skills/diagrammatical/references/types/gantt.md`. Do not read helper implementations. For
ambiguous requests, use purpose and dominant relationship shape as directed by the shared
workflow. Keep this command as a routing wrapper; selection, composition, validation, and output
rules remain in the shared references.

Use the bounded execution contract in the shared workflow. Run the canonical self-check once,
perform one visual-review pass, and make no more than one automatic correction followed by one
final self-check. If defects remain, hand off valid artifacts with specific findings instead of
continuing to revise. Do not generate alternatives, onboard a brand, or export PNG unless the user
explicitly requested that work.

Treat the configured turn ceiling as a real execution budget. For the standard path:

- Batch the shared workflow, one type reference, chosen template, selected style, and selected brand
  into one read-only tool call. Do not list or read other references, schemas, examples, helper
  implementations, or brand-onboarding material.
- Inspect relevant project files in one bounded tool call. Do not inspect them again after modelling.
- Record the diagnostic trace at start and final handoff only; the final update infers artifact
  stages. Do not update it after every stage. The exact calls are
  `workflow_trace.py start <project> <slug> --type <type> --max-turns <limit>` and
  `workflow_trace.py update <trace> --diagram-directory <output> --stage inspect-model=completed
  --stage select-presentation=completed --stage correction=<not-needed|completed> --stage
  final-validation=completed --stage handoff=completed`; do not call `--help` first.
- Author `diagram.yaml` and HTML directly, then use extraction and self-check helpers as documented.
- Use an already available bounded browser/screenshot tool for visual review. Never launch a system
  browser from an unbounded shell command. If no bounded visual tool is available, record visual
  review as `not-performed`; do not probe for renderers or improvise a browser process.
- Reserve enough of the configured budget for the final trace update and handoff. A correction may
  use remaining turns, but may occur only once.
