# Diagram source

`diagram.yaml` is the editable source of truth. It identifies the audience, purpose and primary
message; uses stable semantic IDs; selects one diagram type and composition; separates presentation
from meaning; and records all material collapse, omission and assumption in `fidelity`.

The shared schema supports architecture nodes and edges, flowchart paths, ordered sequence messages,
rooted site-map hierarchy and date-driven Gantt tasks. Validate with:

```sh
python skills/diagrammatical/scripts/validate.py diagrams/example/diagram.yaml --schema diagram --json
```

HTML and SVG are regenerated views, not editing sources. Diagram overrides belong under
`presentation.overrides`; removing them returns to brand and project defaults. Never disable safety
or accessibility through an override.
