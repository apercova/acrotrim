"""String-in/string-out AcroTrim engine."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

from .errors import InvalidInputError
from .rules import Rule, RegexRule, load_builtin_rules, load_regexp_rules

_LANG_RE = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")


@dataclass(frozen=True)
class _Token:
    text: str
    start: int
    end: int


def _is_token_char(char: str) -> bool:
    return unicodedata.category(char)[0] in {"L", "M", "N"}


def _tokens(value: str) -> list[_Token]:
    result: list[_Token] = []
    index = 0
    while index < len(value):
        if not _is_token_char(value[index]):
            index += 1
            continue
        start = index
        index += 1
        while index < len(value) and _is_token_char(value[index]):
            index += 1
        result.append(_Token(value[start:index], start, index))
    return result


def _normalize_token(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _separator_key(value: str) -> str:
    output: list[str] = []
    in_space = False
    for char in value:
        if char.isspace():
            if not in_space:
                output.append(" ")
            in_space = True
        else:
            output.append(char)
            in_space = False
    return "".join(output)


def _term_parts(term: str) -> tuple[list[_Token], list[str], str]:
    term_tokens = _tokens(term)
    separators = [term[term_tokens[i].end : term_tokens[i + 1].start] for i in range(len(term_tokens) - 1)]
    trailing = term[term_tokens[-1].end :]
    return term_tokens, separators, trailing


def _match_term_at_position(
    text: str, tokens: list[_Token], start: int, rule: Rule
) -> int | None:
    term_tokens, separators, trailing = _term_parts(rule.term)
    if start < 0 or start + len(term_tokens) > len(tokens):
        return None
    actual = tokens[start : start + len(term_tokens)]
    if any(_normalize_token(a.text) != _normalize_token(b.text) for a, b in zip(actual, term_tokens)):
        return None
    for index, separator in enumerate(separators):
        observed = text[actual[index].end : actual[index + 1].start]
        if _separator_key(observed) != _separator_key(separator):
            return None
    end = actual[-1].end
    if trailing:
        if not text.startswith(trailing, end):
            return None
        end += len(trailing)
    return end


def _match_regexp_rule(rule: RegexRule, text: str) -> tuple[int, int] | None:
    """Match a regexp rule's pattern anywhere in the text (prefix or suffix position)."""
    import re as re_mod
    pattern = rule.pattern
    match = re_mod.search(pattern, text)
    if match is None:
        return None
    start = match.start()
    end = match.end()
    if start == 0:
        # Prefix match
        remove_end = end
        while remove_end < len(text) and text[remove_end].isspace():
            remove_end += 1
        return (0, remove_end)
    if end == len(text):
        # Suffix match
        remove_start = start
        while remove_start > 0 and text[remove_start - 1].isspace():
            remove_start -= 1
        return (remove_start, len(text))
    # Match in the middle - treat as suffix if at end, prefix if at start
    if end == len(text):
        remove_start = start
        while remove_start > 0 and text[remove_start - 1].isspace():
            remove_start -= 1
        return (remove_start, len(text))
    if start == 0:
        remove_end = end
        while remove_end < len(text) and text[remove_end].isspace():
            remove_end += 1
        return (0, remove_end)
    return None


def _match_term_anywhere(
    text: str, rule: Rule | RegexRule
) -> tuple[int, int] | None:
    """Match a rule's term anywhere in the text (prefix or suffix position)."""
    if isinstance(rule, RegexRule):
        return _match_regexp_rule(rule, text)
    
    tokens = _tokens(text)
    if not tokens:
        return None
    
    term_token_count = len(_tokens(rule.term))
    
    # Try to match at the beginning (position 0)
    if term_token_count <= len(tokens):
        end_idx = _match_term_at_position(text, tokens, 0, rule)
        if end_idx is not None:
            # Handle punctuation variants at the end
            tail = text[end_idx:]
            variant = next(
                (p for p in sorted(rule.punctuation_variants, key=len, reverse=True) if tail.startswith(p)),
                None,
            )
            if variant is not None:
                end_idx += len(variant)
            remove_end = end_idx
            while remove_end < len(text) and text[remove_end].isspace():
                remove_end += 1
            return (0, remove_end)
    
    # Try to match at the end
    end_start_idx = len(tokens) - term_token_count
    if end_start_idx >= 0:
        end_idx = _match_term_at_position(text, tokens, end_start_idx, rule)
        if end_idx is not None:
            # Handle punctuation variants at the end
            tail = text[end_idx:]
            variant = next(
                (p for p in sorted(rule.punctuation_variants, key=len, reverse=True) if tail.startswith(p)),
                None,
            )
            if variant is not None:
                end_idx += len(variant)
            remove_end = end_idx
            while remove_end < len(text) and text[remove_end].isspace():
                remove_end += 1
            # Handle leading separators
            actual_start = tokens[end_start_idx].start
            cursor = actual_start
            # Skip whitespace backwards
            while cursor > 0 and text[cursor - 1].isspace():
                cursor -= 1
            # Then skip leading separators if present
            if cursor > 0 and text[cursor - 1] in rule.leading_separators:
                cursor -= 1
                while cursor > 0 and text[cursor - 1].isspace():
                    cursor -= 1
            actual_start = cursor
            return (actual_start, remove_end)
    
    return None


def _remove_match(text: str, start: int, end: int) -> str:
    return text[:start] + text[end:]


@lru_cache(maxsize=1)
def _rules() -> tuple[Rule, ...]:
    return load_builtin_rules()


def _language_scope(lang: str | None) -> set[str] | None:
    if lang is None:
        return None
    if not isinstance(lang, str) or not _LANG_RE.fullmatch(lang) or lang.casefold() == "all":
        raise InvalidInputError("lang must be a language tag such as 'en' or 'es-MX'")
    subtags = lang.casefold().split("-")
    return {"-".join(subtags[:index]) for index in range(1, len(subtags) + 1)}


def trim_name(value: str, *, strict: bool = False, lang: str | None = None) -> str:
    """Remove configured prefixes and suffixes, optionally scoped to a language."""
    if not isinstance(value, str):
        raise InvalidInputError("input must be a string")
    if not isinstance(strict, bool):
        raise InvalidInputError("strict must be a boolean")
    language_scope = _language_scope(lang)
    current = value
    rules = _rules()
    if language_scope is not None:
        rules = tuple(rule for rule in rules if rule.lang.casefold() in language_scope)
    if strict:
        rules = rules + load_regexp_rules()
    
    changed = True
    while changed:
        changed = False
        tokens = _tokens(current)
        if not tokens:
            break
        
        for rule in rules:
            match = _match_term_anywhere(current, rule)
            if match is not None:
                start, end = match
                current = _remove_match(current, start, end)
                changed = True
                break  # restart the while loop since current changed
    
    return current