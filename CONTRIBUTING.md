# Contributing

## Environment

The project requires Python 3.12 or newer and
[uv](https://docs.astral.sh/uv/).

```bash
make setup
```

This installs the locked development dependencies and enables the local
pre-commit hooks.

## Development workflow

Before opening a pull request:

```bash
make format
make check
```

`make check` verifies formatting, lint rules, static types, tests, coverage,
and asset checksums. `make build` additionally creates the source distribution
and wheel.

## Adding or changing a pipeline

Follow the extension contract in `docs/ARCHITECTURE.md`. Every behavior change
must include a focused test and an updated `ruleset` or pipeline version when
the calculation semantics change.

If a pipeline declares an `asset_pack`, that pack must exist in
`assets/manifest.json`. New or modified raster assets must include their prompt
and updated SHA-256 checksum.

## Pull requests

- Keep changes focused and explain any algorithm or ruleset decision.
- Add regression tests for bug fixes.
- Preserve the JSON envelope unless the schema version is intentionally
  changed.
- Do not add copied divination tables, text, or artwork without clear rights
  and attribution.
