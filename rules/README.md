# Rule files

Approved trim rules live in this directory. Each file is a JSON array of **rule groups**. A group states the match policy once and lists every term that uses that policy. This replaces the draft shape under `../rules_draft/`, where each term was its own object and repeated `lang`, `position`, `match`, and `provenance`.

Matching behavior for a single term is still `../spec/v1/matching.md`. These files are the storage shape. A loader expands each group into one literal rule per term before matching.

Research notes and unapproved candidates stay under `../research/language-candidates/`. They are not loaded.

## Layout

```
rules/
  prefix/<lang>.json      # prefix groups for one language or region
  suffix/<lang>.json      # suffix groups for one language or region
  regexp-rules.json       # optional general patterns
```

`<lang>` is a BCP 47 tag in lowercase, matching the group's `lang` field (`es`, `es-mx`). There is one file per position and tag. There is no language-neutral literal file.

The directory name is the position. Every group in that file uses the same `position` value.

## Literal group

```json
{
  "schemaVersion": "1.0",
  "id": "suffix.es-mx.comp",
  "lang": "es-mx",
  "position": "suffix",
  "match": {
    "punctuationVariants": [""],
    "leadingSeparators": [","]
  },
  "terms": ["S.A.", "S. de R. L.", "S.A.S.", "S.A. de C.V."]
}
```

| Field | Meaning |
| --- | --- |
| `schemaVersion` | Always `"1.0"`. |
| `id` | Stable id of the **group**, unique across all prefix and suffix files. Pattern: `^[a-z0-9][a-z0-9._-]*$`. |
| `lang` | Language or region tag. Lowercase. Not `all`. Comparison at match time is case-insensitive and includes parent tags (`es-mx` selects `es` and `es-mx`; `es` selects only `es`). |
| `position` | `"prefix"` or `"suffix"`. Must match the parent directory. |
| `match.punctuationVariants` | Exact optional punctuation immediately after the term. `""` means a match with no extra punctuation. At least one entry. Characters limited to `.`, `!`, `?`, and `·`. No whitespace between the term and this punctuation. |
| `match.leadingSeparators` | Suffix only. Optional separator immediately before the term. Allowed values: `,`, `;`, `:`, `–`, `—`. Whitespace may sit between the separator and the term. The separator is removed with the match. Prefix groups use `[]`. |
| `terms` | Non-empty array of distinct term strings. Order is not significant for matching. |

A term is a whole token sequence. Tokens are Unicode letters, marks, and numbers. Punctuation inside the term is significant. Matching uses NFC and Unicode case folding, as in `../spec/v1/matching.md`.

Only terms that share **all** of `lang`, `position`, and `match` belong in one group. A different separator or punctuation list is a different group.

### Expansion

Each string in `terms` becomes one literal rule with that group's `lang`, `position`, and `match`. Group order and term order do not affect which span wins. Span length still wins; an enabled regexp rule still beats a literal rule on an equal span. If two expanded literals tie, the tie-break is the group's `id`, then the term string in code-point order.

Provenance is not stored on the group. Source and review status stay in the language research notes. A term is listed here only after it is approved.

## Regular-expression file

`regexp-rules.json` is an array of pattern objects, one object per pattern. Patterns are not grouped by term.

```json
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
```

`lang` is `"all"`. A caller language tag does not filter these rules. Implementations apply them only in strict mode. The pattern and precedence rules are in `../spec/v1/matching.md` and `../spec/v1/regexp-rule-schema.json`.

## What must not be repeated

- Do not emit one object per term when `match` is identical.
- Do not copy `schemaVersion`, `lang`, `position`, or `match` onto each term.
- Do not put the same term twice in one group, or in two groups that would match the same span for the same tag and position.
