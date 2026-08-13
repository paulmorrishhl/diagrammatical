# Site map and tree diagrams

Use a site map for user-facing pages, screens, product sections or another parent/child hierarchy. Do not diagram repository folders or API endpoints unless explicitly requested. Inspect common route evidence such as Next.js App/Pages Router, Astro routes, React Router configuration and static route manifests without building a general parser.

## Semantic and visual grammar

Declare one `sitemap.root`. Nodes use `page`, `section`, `state`, `external-service`, or `note`, with optional `route`, `pageKind`, `visibility`, and `lifecycle`. `sitemap.hierarchy` records ordered parent/child relationships. `crossLinks` are exceptional navigation and must use a labelled dashed/dotted treatment distinct from solid hierarchy links. Use groups for product areas and presentation focal nodes for at most two sections or journey points.

The root/hub is unmistakable. Hierarchy reads top-to-bottom or left-to-right with consistent sibling order. Authenticated, external, planned and deprecated areas use shape, label or stroke cues as well as colour. Dynamic route families collapse under a truthful label. Budget: 4 levels, 16 visible nodes, 5 siblings per parent, 2 focal elements. Preserve global/primary navigation, group truthful sections, split top-level and detail maps, and record collapsed routes and assumptions.

## Compositions

### `conventional-tree`

- When to use: one rooted hierarchy with stable levels.
- When not to use: a hub or user journey is the primary message.
- Root/hierarchy: single root above descendants; every non-root has one parent.
- Parent/child placement: aligned ranks with solid orthogonal links.
- Sibling ordering: navigation order, then stable source order.
- Cross-links: rare, dashed, labelled and routed outside branches.
- Section grouping: use quiet boundaries only where they clarify ownership.
- Reading direction: top-to-bottom.
- Audiences: content, product, mixed.
- Complexity: 4 levels, 16 nodes, 5 siblings.
- Failure modes: tangled cross-links, hidden root, filesystem-folder mapping.

### `product-sections`

- When to use: a signed-in product organised into meaningful areas.
- When not to use: a shallow public website or journey is clearer.
- Root/hierarchy: application shell/root leads to grouped product sections.
- Parent/child placement: section headers form columns or lanes; pages align beneath.
- Sibling ordering: primary navigation order within each section.
- Cross-links: dashed between sections and used only for important shortcuts.
- Section grouping: explicit product-area boundaries with labels.
- Reading direction: top-to-bottom, then left-to-right across sections.
- Audiences: product, design, engineering.
- Complexity: regroup above five siblings and split dense areas.
- Failure modes: sections derived from code folders, equal emphasis everywhere, API routes.

### `hub-navigation`

- When to use: a central home/hub is the dominant navigation model.
- When not to use: depth and ancestry are more important than hub access.
- Root/hierarchy: root hub centred; first-level destinations surround it.
- Parent/child placement: second-level items stay near their owning spoke.
- Sibling ordering: clockwise or row order stated consistently.
- Cross-links: outer dashed arcs; never confused with radial hierarchy links.
- Section grouping: optional clusters around major spokes.
- Reading direction: hub outward, then within each spoke.
- Audiences: product, executive, mixed.
- Complexity: shallow, normally 1–2 levels and 4–8 spokes.
- Failure modes: architecture-style service hub, crossing spokes, unclear root.

### `user-journey`

- When to use: hierarchy must foreground a primary navigation journey.
- When not to use: journey order would obscure the actual hierarchy.
- Root/hierarchy: hierarchy remains solid and rooted; focal journey overlays it.
- Parent/child placement: preserve ranks, then align journey nodes where practical.
- Sibling ordering: journey siblings first only if navigation truth supports it.
- Cross-links: focal journey uses a labelled dashed/dotted path distinct from hierarchy.
- Section grouping: show phase or product areas when journey crosses them.
- Reading direction: root hierarchy first, highlighted journey second.
- Audiences: product, research, executive.
- Complexity: one focal journey, two focal elements; companion flowchart if decision logic dominates.
- Failure modes: mixing process arrows with ancestry, colour-only journey, false parentage.

## Accessibility, safety, and anti-patterns

The accessible description names the root, major sections, depth, and important cross-links or focal journey. Solid hierarchy and dashed/dotted cross-navigation remain understandable without colour. Visible text identifies authenticated, external, planned and deprecated areas. Avoid multiple roots, cycles, orphans, distant connector tangles, dynamic-route instances, API pages, inconsistent siblings, illegible labels, and mixing hierarchy with flowchart logic. Use semantic tokens, light/dark templates, safe inline SVG, prefixed IDs, extraction and shared self-check.

## Natural-language workflow

For “Create a site map from the routes in this project”: inspect relevant route sources; derive meaningful user-facing routes; determine audience, purpose and message; declare root and hierarchy; select composition; group/collapse honestly; write and validate `diagram.yaml`; compose HTML/SVG; extract; self-check; render and inspect; report fidelity. Use the standard four files and never create PNG by default.
