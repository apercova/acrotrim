# AcroTrim for Python

This is the Python implementation of AcroTrim. The public API takes one string and returns one trimmed string. An optional `lang` argument scopes literal rules to that language and its parent tags; omitting it keeps the default behavior of considering all configured literal rules.

```python
from acrotrim import trim_name

print(trim_name("Dr. Jane Smith Jr."))  # Jane Smith
print(trim_name("Sra. Ana López", lang="es-MX"))  # Ana López
```

## CLI

After syncing the project environment, pass a quoted name to the command:

```sh
uv sync
uv run acrotrim "Dr. Jane Smith Jr."
uv run acrotrim "ACME, Inc."
uv run acrotrim --strict "Company Name."
uv run acrotrim --lang es-MX "Sra. Ana López"
```

The command prints the trimmed string. General regex rules are disabled by default; `--strict` enables them. Use `uv run acrotrim --help` for usage.

## Rules

All canonical rule data lives under `../../rules/`. Literal groups live in `../../rules/prefix/<lang>.json` and `../../rules/suffix/<lang>.json`, for example `rules/prefix/es.json` and `rules/suffix/es-mx.json`. Each object is one match policy and a `terms` array; the loader expands that array into one literal rule per term. See `../../rules/README.md`. There is no general literal fallback file. Optional general regex rules remain in `regexp-rules.json` and are enabled by `--strict`. Without `--lang`, all configured literal rules are used. With `--lang es-MX`, rules tagged `es` and `es-mx` apply; matching is case-insensitive, so `ES-mx` behaves the same. A base tag such as `es` does not select region-specific child rules. The language-neutral regex rule remains controlled only by `--strict`.

## Build and versioning

The Python package version in `pyproject.toml` and specification version in `../../spec/CURRENT` are independent. Before building, the package checks that it declares support for the current spec and runs that spec's conformance fixtures. A wheel bundles the current contents of `../../rules/`, so it runs without the repository checkout. The sdist contains a snapshot of the spec and rules for rebuilding.

Build both distribution files with:

```sh
uv build
```

The build fails when the implementation does not declare the current spec version or does not match its conformance fixtures.
