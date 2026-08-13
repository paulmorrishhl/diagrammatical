# Troubleshooting

- Marketplace added but plugin absent: run `/plugin install diagrammatical@diagrammatical`.
- Command not discovered: run `/reload-plugins`, then inspect `/plugin` for the installed version.
- Local path confusion: add the repository root containing `.claude-plugin/marketplace.json`.
- Cache differs from checkout: uninstall/reinstall the local marketplace plugin, then reload plugins.
- Python import missing: activate the project environment and run `pip install -e '.[dev]'`.
- Playwright/Chromium missing: install `.[export]`, then `playwright install chromium`.
- Font differs: check the calibration fallback disclosure; Diagrammatical does not copy font files.
- Unsupported Mermaid: use one of flowchart, graph, sequenceDiagram or Gantt and the documented subset.
- Schema failure: run `validate.py ... --schema diagram --json` and fix each named path.
- Complexity warning: preserve the primary message, split detail, and record simplification.
- Visual review unavailable: leave `visualReview.status` as `not-performed`; do not infer a pass.
