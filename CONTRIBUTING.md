# Contributing

Diagrammatical is implemented one milestone at a time against `SPEC.md`. Before contributing, read the specification and `IMPLEMENTATION_PLAN.md`, keep plugin wrappers thin, and avoid implementing later-milestone features in an earlier change.

Run the local checks before opening a pull request:

```bash
ruff check .
pytest
python scripts/verify_package.py
```

Consequential implementation decisions belong in `docs/decisions/`.

