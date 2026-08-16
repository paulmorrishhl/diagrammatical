---
description: Validate a Diagrammatical source or generated deliverable
argument-hint: "[diagram source or output path]"
---

Use `skills/diagrammatical/SKILL.md` and
`skills/diagrammatical/references/validation.md` in validation mode for `$ARGUMENTS`.

Resolve the installed skill root, then invoke the canonical checker exactly once:

```text
python <skill-root>/scripts/self_check.py <diagram-directory> --json
```

Do not read helper implementations, reload diagram-type references, or rerun schema, brand,
HTML, SVG, extraction, or PNG checks individually: `self_check.py` already coordinates them. If
the canonical check fails, report its named errors and stop unless the user asked for repair. Do
not render or visually revise during a validation-only request. Distinguish errors from warnings,
and never describe mechanical validation as proof of aesthetic quality.
