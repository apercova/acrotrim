# Implementing AcroTrim in Another Language

This document describes what you need to implement AcroTrim in Go, Rust, Java, or .Net. The specification is language-neutral; the fixtures and rule schemas are the single source of truth.

## 1. Check the Specification Version

```text
spec/CURRENT
```

Contains the current spec version (currently `v1`). All implementations must declare the version they support.

## 2. Read the Narrative Contract

| Document | What It Covers |
|---|---|
| `spec/v1/matching.md` | String-in/string-out contract, rule matching, boundary behavior, punctuation/whitespace rules |
| `spec/v1/normalization.md` | Public operation signature, language tag filtering, rule group shape |
| `spec/v1/policies.md` | Rule enabling policies (`strict`, `lang`), approved vs unapproved rules |
| `spec/v1/result.md` | Public result is the cleaned Unicode string only (no rule IDs, spans, warnings) |

## 3. Rule File Format

Rule files reside flat under the `rules/` directory:

- `rules/en.json` — English prefix/suffix rules
- `rules/es.json` — Spanish prefix/suffix rules
- `rules/regexp-rules.json` — optional general regex patterns

**Each rule group** (in prefix or suffix files) has this shape per `rule-schema.json`:

```json
{
  "schemaVersion": "1.0",
  "id": "prefix.en.single-word",
  "lang": "en",
  "match": {
    "punctuationVariants": ["", "."],
    "leadingSeparators": []
  },
  "terms": ["Sr", "Mr", "Ms", "Mrs", "Jr", "Dr", "Prof"]
}
```

**Key points:**

- `position` (prefix/suffix) is **not** a field in the JSON. It is inferred from the parent directory name in the original layout (`prefix/` or `suffix/`), but the JSON files themselves carry no `position` field.
- `lang` comparison at match time is **case-insensitive** and includes parent tags: `es-MX` selects `es` and `es-MX`; `es` selects only `es`.
- `terms` is an **array of strings** (not a singular `term`). Each term becomes one literal rule.
- `match.punctuationVariants` — exact optional punctuation after the term. Empty string `""` means a match with no extra punctuation.
- `match.leadingSeparators` — suffix-only. Optional separator immediately before the term. Allowed: `,`, `;`, `:`, `–`, `—`. Whitespace may sit between separator and term.
- A term is a **whole token sequence**: Unicode letters, marks, or numbers. Punctuation inside the term is significant.
- Matching uses **NFC normalization** and **Unicode case folding**.

**Regexp rule file** (`regexp-rules.json`):

```json
[
  {
    "schemaVersion": "1.0",
    "id": "regexp.abbreviation.terminal-period",
    "lang": "all",
    "pattern": "\\w{1,10}\\.",
    "positions": ["prefix", "suffix"],
    "provenance": {
      "source": "AcroTrim v1 opt-in general abbreviation rule",
      "reviewStatus": "approved"
    }
  }
]
```

- `lang` is `"all"`. Caller language tag does **not** filter these rules.
- Patterns enabled only in **strict mode**.
- For competing matches at one boundary: longest complete component span wins; enabled regex rule wins over literal rule on equal span; then lexicographically smallest stable rule ID breaks ties.

## 4. Conformance Fixtures

Read these JSONL files from `spec/v1/conformance/`:

| File | Purpose |
|---|---|
| `names.jsonl` | Main trim test cases: `id`, `input`, `expected`, `strict` (boolean), `lang` (string or null) |
| `unicode.jsonl` | Unicode preservation test cases |
| `expected-failures.jsonl` | Invalid input cases: `{"id":"error.non-string","input":42,"expectedError":"invalid_input"}` |

**Each test case** has these fields:

| Field | Description |
|---|---|
| `id` | Stable case name (used for error reporting) |
| `input` | The Unicode string to trim |
| `expected` | The exact expected trimmed string |
| `strict` | Boolean — enable general regex rules (`true`/`false`) |
| `lang` | Language tag (e.g. `"en"`, `"es-MX"`, `null`/omitted for all languages) |
| `expectedError` | Optional — if present, the call **must** raise an error with this code |

**Running conformance** (per language):

```pseudo
for each line in names.jsonl:
    case = json.loads(line)
    result = trim_name(case.input, strict=case.strict, lang=case.lang)
    if case.expectedError:
        assert result raises error with code case.expectedError
    else:
        assert result == case.expected
```

## 5. Parameter Convention

Implementations should support a trim function with these semantics:

| Parameter | Type | Description |
|---|---|---|
| `value` (or `input`) | `string` | The Unicode name to trim |
| `strict` | `boolean` | Enable general regex rules (`true`/`false`) |
| `lang` | `string` or `null` | Language tag filtering; `null`/omitted considers all languages |

The conformance fixtures use these exact names as keyword arguments:
`trim_name(value, strict=case.strict, lang=case.lang)`.

## 6. Quick Checklist

- [ ] `trim_name` function accepts `(value, strict, lang)` or equivalent
- [ ] Rule files under `rules/` match `rule-schema.json` / `regexp-rule-schema.json`
- [ ] Conformance fixtures in `spec/v1/conformance/` pass for your language
- [ ] Language tag filtering: `lang` scoping to requested tag + parent tags (case-insensitive)
- [ ] `strict` mode enables language-neutral regexp rules from `regexp-rules.json`
- [ ] Non-string input raises an error
- [ ] Empty output: if removals consume all non-whitespace content, return `""`
- [ ] Preserve surviving spelling, capitalization, diacritics, and internal punctuation
- [ ] Idempotence: cleaning an already-cleaned value leaves it unchanged