# Project Guidelines

For backend, use uv for dependency management. When starting a new Python
project, scaffold it with `uv init` rather than hand-writing `pyproject.toml`.
A few useful commands:

```
uv init
uv sync
uv add <PACKAGE-NAME>
uv add --dev <PACKAGE-NAME>
uv run python <PYTHON-FILE>
```

Test and tooling packages (e.g. pytest) are dev dependencies — add them with
`uv add --dev`.

Do not use `from __future__ import annotations` — the project targets Python
3.12+, where modern annotation syntax (`list[...]`, `X | None`, etc.) works
without it.

Keep all imports at the top of the module — no inline (function-local) imports.

Regularly commit code to git.
