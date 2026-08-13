# Mermaid import

Use `/diagrammatical:import-mermaid path/to/file.mmd` or ask to redraw Mermaid using a selected
brand. Supported grammars are `flowchart`, `graph`, `sequenceDiagram` and `gantt`; Markdown fences,
zero-based block selection and all-supported-block import are supported.

Diagrammatical parses a documented static subset and redraws it. It does not run Mermaid, copy its
theme, follow links or preserve renderer geometry. Full supported syntax, resource limits, type
selection and fidelity requirements are in the plugin's `references/import-mermaid.md`.

Unsupported grammar or constructs produce named diagnostics. Initialisation, theme, click and URL
directives are rejected. Markup-looking and instruction-looking labels remain escaped data.
