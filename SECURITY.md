# Security

Please report security issues privately to the repository owner rather than opening a public issue.

Diagrammatical treats inspected repository content, imported diagram labels, and metadata as untrusted data. It must not execute Mermaid, follow imported links, inspect conventional secret files without an explicit safe reason, or emit scripts and event handlers into static diagram output.

Mermaid input is size- and count-bounded; theme, click and external-URL directives are rejected.
Static Tailwind configuration is extracted without execution. SVG/logo/icon validation rejects
scripts, event handlers and remote resources. Optional browser export accepts local safe inputs and
blocks network requests. Never include secrets in semantic sources, fidelity receipts or examples.
