# Branding Diagrammatical

Diagrammatical brands give diagrams an organisation's identity without changing their information
grammar. Brand controls semantic colours, typography, logo, shape, stroke, connectors, icon family,
density, accessibility policy, and light/dark variants. Art direction (`editorial`, `technical`,
`executive`, `clinical`, or `neutral`) controls presentation character. Diagram type and composition
continue to control structure.

## Quick start

Ask “Configure Diagrammatical using the branding in this repository” or run
`/diagrammatical:brand`. Diagrammatical inspects supported sources, proposes a semantic mapping,
reports contrast and fallbacks, generates a calibration preview, and asks before saving. An inferred
mapping is never treated as approved.

Approved reusable files live at:

```text
.diagrammatical/
├── config.yaml
└── brands/<brand-id>/
    ├── brand.yaml
    ├── fidelity.json
    ├── calibration.html
    ├── calibration.svg
    └── logo.svg          # only when supplied, safe, and approved
```

Commit these small text files to version control when the brand is shared by the team. Review logo,
font, and icon licences before committing assets. Never commit secrets, caches, or temporary proposal
directories.

## Onboarding sources

- Manual: provide colours, font families, a local SVG logo path, and shape preferences in the
  conversation.
- Existing pack: provide a directory or `brand.yaml`; it is schema- and asset-validated before use.
- Repository CSS: root/theme variables, body/text, CTA/link, surface, border, status, typography, and
  dark selectors are prioritised; generated and third-party directories are ignored.
- Tailwind: literal colour/font values in common config files and CSS-first `@theme` tokens are read
  as text. JavaScript and TypeScript are never executed.
- Token JSON: nested primitive values and `$value`/`value` objects are supported, including exact
  local `{token.path}` references. Circular or missing references fail.
- Website: the active agent records inspected public URLs, samples representative computed styles
  where browser tools exist, and discloses inaccessible assets. No hosted scraper is required.

## Semantic token reference

`canvas`, `surface`, and `surfaceSecondary` form the backdrop. `ink`, `inkMuted`, and `rule` carry
text and structure. `connector` remains neutral by default. `emphasisPrimary`,
`emphasisPrimaryTint`, and `emphasisSecondary` carry restrained focus. `external`, `success`,
`warning`, `danger`, and `deprecated` carry semantic meaning together with non-colour cues.

Raw palette values never map directly to arbitrary diagram shapes. Existing status colours are
preserved; missing status roles use recorded accessible defaults. Primary accent ordinarily appears
on no more than two focal elements.

## Contrast and calibration

Brand validation uses WCAG relative luminance and checks normal/small text on canvas, surfaces,
accents, and status treatments. A failing value is never reported as accessible. When the policy
allows derived colours, the receipt records the original value and the smallest proposed adjustment;
the adjustment is saved only after approval. Shape, labels, line style, and icons provide redundant
meaning beyond colour.

The calibration sheet exercises typography, all semantic roles, node/connector/state treatments,
and small architecture and flowchart samples using the same static templates and safety checks as
normal output. Regenerate and visually inspect it after reusable changes. Calibration does not create
PNG.

## Diagram-only overrides

Use a semantic override in `diagram.yaml` when a change should affect only one diagram:

```yaml
presentation:
  brand: company
  style: executive
  mode: dark
  overrides:
    emphasisPrimary: "#E4B63D"
    deprecated: "#D97706"
    connectorWidth: 2
```

Overrides are schema-, accessibility-, and safety-validated, appear in resolution provenance, and
never modify shared branding. Remove the `overrides` block to return to brand/project defaults.

## Dark variants and limitations

Dark mode is optional. Explicit dark tokens are preferred. If absent, Diagrammatical may propose a
generated variant based on accessible dark surfaces and adjusted accents; it does not invert colours
and does not save the result without approval.

Static extraction intentionally does not evaluate CSS functions, execute Tailwind configuration,
implement every design-token standard, convert raster logos, download website fonts, infer licence
rights, or prove visual quality. Supply explicit values when static evidence is ambiguous.
