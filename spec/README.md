# AcroTrim specification

This directory contains the language-neutral, normative contract for AcroTrim. Implementations live separately under `implementations/`; canonical rule data lives under `../rules/`. `CURRENT` names the current specification version used by implementation build checks.

## Current version: v1

- `v1/normalization.md`, `v1/matching.md`, `v1/policies.md`, and `v1/result.md` define the string-in/string-out contract, including optional language-tag filtering.
- Language-specific prefix and suffix rule files live under `../rules/<lang>/`.
- `v1/rule-schema.json` and `v1/regexp-rule-schema.json` define the portable rule shapes.
- `v1/conformance/` contains language-neutral input/output examples, including language filtering cases.

A change that can alter a cleaned value, match, warning, or error is a behavioral specification change and must be recorded in the current specification and its conformance fixtures. Implementations declare the specification version they support.

Unless a document says otherwise, normative words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are used in their ordinary standards-document sense. Implementations package canonical rule files while keeping the source data in the shared `rules/` directory.
