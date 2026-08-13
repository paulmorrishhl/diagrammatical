# Export

Standalone SVG is always part of normal output. Re-extract it with:

```sh
python skills/diagrammatical/scripts/extract_svg.py diagram.html diagram.svg --json
```

PNG is never automatic. Install `pip install -e '.[export]'`, run `playwright install chromium`,
then explicitly use:

```sh
python skills/diagrammatical/scripts/export_png.py diagram.html diagram.png --scale 2 --json
```

Use `--full-frame` for the editorial page and `--force` only after approving replacement. Scale is
1–4. Network requests are blocked and missing fonts fall back after a bounded wait.
