# v1 rule policy

The public cleaner removes approved literal rule groups when they match at their configured prefix or suffix position. Rule groups are stored under `../rules/<lang>/` with the shape `schemaVersion`, `id`, `lang`, `match` (containing `punctuationVariants` and `leadingSeparators`), and `terms` (an array of term strings). The `position` (prefix or suffix) is inferred from the parent directory name.

By default, regular-expression rules are ignored. The optional `strict` flag enables the approved general regex rules from `regexp-rules.json`. The optional `lang` argument scopes literal rules to the requested tag and its parent tags; omitted `lang` considers all literal rules. `strict` controls the language-neutral regex rules independently. No other per-call policies or rule configuration are supported in v1.

Rules that are not approved MUST NOT be included in a published default rule set. Ambiguous terms should be omitted until reviewed; the cleaner does not guess from context.
