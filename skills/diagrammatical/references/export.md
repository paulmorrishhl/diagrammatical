# Export

HTML and standalone SVG are normal Diagrammatical outputs. PNG is optional and explicit-only.

For SVG, run `extract_svg.py INPUT.html OUTPUT.svg`. The extractor requires exactly one canonical
inline SVG unless a simple `#id` selector is supplied. It preserves the viewBox, title, description,
definitions, markers, masks, patterns, styles and safe font fallbacks while rejecting scripts,
event handlers, remote resources, duplicate IDs and ambiguous candidates. It never includes the
surrounding editorial HTML and will not overwrite without `--force`.

For PNG, install the optional dependency and browser:

```sh
pip install -e '.[export]'
playwright install chromium
```

Then run `export_png.py INPUT OUTPUT.png --scale 2 --json`. Scale must be 1–4. Diagram-only capture
is the default; add `--full-frame` for the surrounding editorial page and `--force` to approve
replacement. Dimensions derive from the SVG viewBox and scale. Browser requests are blocked, fonts
have a bounded readiness wait, and documented fallbacks are used after timeout. Missing Playwright
or Chromium never prevents ordinary HTML/SVG work.
