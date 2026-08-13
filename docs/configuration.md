# Project configuration

Project-owned configuration lives at `.diagrammatical/config.yaml`. The installed plugin remains
read-only. Unknown fields warn; invalid values fail before rendering.

```yaml
schemaVersion: 1
defaults:
  brand: editorial-blueprint
  style: editorial
  audience: mixed
  mode: light
  detail: balanced
  outputPreset: document-wide
output:
  directory: diagrams
  html: true
  svg: true
  png: false
behaviour:
  askBeforeSimplifyingCriticalContent: true
  reportFidelityLedger: true
  generateAlternatives: false
```

`defaults.brand` selects a built-in ID or a directory under `.diagrammatical/brands/`.
`defaults.style` is one of `editorial`, `technical`, `executive`, `clinical`, or `neutral`.
`audience` is `engineer`, `mixed`, or `executive`; `mode` is `light` or `dark`; `detail` is
`minimal`, `balanced`, or `detailed`; and `outputPreset` is `document-wide`, `document-narrow`,
`slide`, or `square`.

`output.directory` is a project-relative path. HTML and SVG default on; PNG defaults off and is not
created by branding. Behaviour flags control whether critical simplification requires confirmation,
whether fidelity is reported, and whether alternatives are generated.

## Resolution order

The single shared resolver applies diagram structural rules, art direction, brand, project defaults,
diagram overrides, and output-preset adaptations. Non-overridable safety/accessibility requirements
are applied last so lower layers cannot disable them. The resolver returns leaf-level provenance.
Unrelated values survive each deep merge.

Setting a brand as project default is a separately approved onboarding action. Existing unrelated
configuration and brand directories are preserved.
