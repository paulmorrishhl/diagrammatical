# Contributing

Diagrammatical is implemented one milestone at a time against `SPEC.md`. Before contributing, read the specification and `IMPLEMENTATION_PLAN.md`, keep plugin wrappers thin, and avoid implementing later-milestone features in an earlier change.

Run the local checks before opening a pull request:

```bash
ruff check .
pytest
python scripts/verify_package.py
python scripts/release_check.py
python scripts/visual_regression.py
```

Visual baselines are never accepted automatically. Render and inspect the changed source, then run
`python scripts/visual_regression.py --update` deliberately and include the reviewed baseline.

See `docs/contributing-diagram-types.md`, `docs/releasing.md`, `SECURITY.md` and
`THIRD_PARTY_NOTICES.md` before changing public behavior or dependencies.

Consequential implementation decisions belong in `docs/decisions/`.
