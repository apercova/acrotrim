# v1 matching semantics

## Rule set

The cleaner loads every approved literal rule from each language or region directory. Rule files reside under the `rules/` directory. For example, `rules/en.json` and `rules/es-MX.json`. (There is also `rules/regexp-rules.json` for general regex rules.) There is no general literal fallback file. When `lang` is omitted, every configured literal rule is considered. When supplied, only rules whose `lang` tag equals the requested tag or one of its parent tags are considered. Tag comparison is case-insensitive. Thus `es-MX` selects rules tagged with `es` and `es-MX`; `es` selects only rules tagged `es`. Script and region subtags use the same parent-chain behavior.

Each rule group in a rule file has the shape defined by the v1 rule schema: `schemaVersion`, `id`, `lang`, `match` (containing `punctuationVariants` and `leadingSeparators`), and `terms` (an array of term strings). The boundary behavior (start or end of input) is determined by the position inferred from the parent directory name.

General regular-expression rules are optional. Implementations enable them only when strict mode is requested; a supplied `lang` does not filter these language-neutral rules. For competing matches at one boundary, select the longest complete component span first; when spans are equal, an enabled regular-expression rule wins over a literal rule, then stable rule ID breaks remaining ties.

The v1 pattern `\w{1,10}\.` matches one whole word token of 1–10 Unicode letter, mark, or number characters followed immediately by a literal period. The period is not counted toward the 10-character limit. It can match at either boundary. After a removal, boundary matching may continue. `lang: "all"` marks it for all languages.

## Boundaries

Matching operates at the start boundary and end boundary of the non-whitespace input. A rule's term sequence is tested for a match at one of these boundaries. At each boundary, the candidate with the longest complete component span wins. If a regex and literal rule tie in span, the regex rule wins; remaining ties are broken by the lexicographically smallest stable rule ID. Results are independent of rule-file ordering.

Rule terms match whole token sequences, never substrings inside a token. A token character is any Unicode letter, mark, or number. Punctuation and whitespace delimit tokens. Rule terms may contain multiple tokens. Matching compares the term's tokens after NFC normalization and Unicode case folding. Punctuation within a term is significant and must match exactly. Whitespace runs between tokens are equivalent.

Prefix and suffix matches may both be removed in one call. Continue matching at each boundary until no rule matches or no non-whitespace text remains.

A rule is applied only at a boundary and only as a complete token sequence.

## Punctuation and whitespace

`punctuationVariants` defines exact optional punctuation immediately after the matched term, for either boundary position. An empty string means no punctuation is also accepted. Whitespace between a term and its optional punctuation is not accepted.

For the end boundary, `leadingSeparators` lists optional separator characters immediately before the term; whitespace may occur between the separator and the term. For example, `Acme, Inc.` can match a rule with `.` in `punctuationVariants` and `,` in `leadingSeparators`. That comma is removed with the match.

When a match is removed, consume adjacent boundary whitespace and only punctuation explicitly allowed by the matching rule. Preserve all internal characters. If no rule matches, return the input exactly as supplied, including whitespace.

## Empty output

If removals consume all non-whitespace content, return the empty string. Do not substitute a guessed value or treat the result as an error.