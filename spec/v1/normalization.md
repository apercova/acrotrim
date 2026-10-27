# v1 trimming contract

## Public operation

The public operation accepts one Unicode string, an optional strict-mode flag, and an optional language tag, and returns one Unicode string:

```text
trim_name(input: string, strict: boolean = false, lang: string | null = null) -> string
```

The caller does not provide person/company type, jurisdiction, or rule configuration. If `lang` is omitted or null, all configured literal prefixes and suffixes are considered. If supplied, `lang` MUST match `^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$` and MUST NOT be `all`; tag matching is case-insensitive. A regional or script tag selects rules tagged with itself and each parent tag (`es-MX` selects `es` and `es-MX`); a base tag does not select more-specific child tags (`es` does not select `es-MX`). The optional `strict` flag enables the approved general regex rules from `regexp-rules.json`; it defaults to false and is not restricted by `lang`. AcroTrim does not parse identity fields, infer an entity type, translate, transliterate, change spelling/capitalization, or resolve nicknames.

Rule groups live under `../rules/<lang>/` with the shape `schemaVersion`, `id`, `lang`, `match` (containing `punctuationVariants` and `leadingSeparators`), and `terms` (an array of term strings). The `position` (prefix or suffix) is inferred from the parent directory name (`prefix/` or `suffix/`). If `lang` is omitted or null, all literal rules across all languages are considered; if supplied, only rules whose `lang` tag matches the requested tag or one of its parent tags are considered.

Non-string input is invalid.

## Matching and preservation

- Non-string input is invalid.
- Matching uses Unicode case folding and NFC normalization on a comparison representation. It MUST NOT transliterate characters or remove diacritics.
- Matching normalization MUST NOT rewrite surviving characters. Removed components are taken from the original text.
- Preserve all surviving spelling, capitalization, diacritics, and internal punctuation.
- If no component is removed, the returned value MUST equal the input exactly, including whitespace.
- If components are removed, strip whitespace that directly borders the removed boundary component. Do not normalize unrelated whitespace.

## Deterministic behavior

Identical input and rule-set version MUST produce identical output. Cleaning an already-cleaned value with the same rule set MUST leave it unchanged (idempotence).
