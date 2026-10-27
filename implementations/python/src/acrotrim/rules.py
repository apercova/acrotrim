#!/usr/bin/env python3
"""Load and validate the shared AcroTrim prefix and suffix rules."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .errors import DuplicateRuleIdError, InvalidRuleError

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_LANG_RE = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
_PUNCT_RE = re.compile(r"^[.!?·]*$")
_SEPARATORS = {",", ";", ":", "–", "—"}


@dataclass(frozen=True)
class Rule:
    id: str
    lang: str
    term: str
    punctuation_variants: tuple[str, ...]
    leading_separators: tuple[str, ...]


@dataclass(frozen=True)
class RegexRule:
    id: str
    lang: str
    pattern: str


def _shared_rules_dir() -> Path:
    """Return the canonical shared rules directory from an install or checkout."""
    package_data = Path(__file__).resolve().parent / "data"
    if (package_data / "rules").is_dir():
        return package_data / "rules"

    for parent in Path(__file__).resolve().parents:
        shared = parent / ".acrotrim-shared"
        if (shared / "spec" / "CURRENT").is_file() and (shared / "rules").is_dir():
            return shared / "rules"
        if (parent / "spec" / "CURRENT").is_file() and (parent / "rules").is_dir():
            return parent / "rules"
    raise InvalidRuleError("AcroTrim rules are missing")


def _required_object(value: Any, required: set[str], where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InvalidRuleError(f"{where} must be an object")
    missing = required - value.keys()
    extra = value.keys() - required
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing {', '.join(sorted(missing))}")
        if extra:
            details.append(f"extra {', '.join(sorted(extra))}")
        raise InvalidRuleError(f"{where}: " + "; ".join(details))
    return value


def _string_array(value: Any, field: str, *, pattern: re.Pattern[str] | None = None, allowed: set[str] | None = None) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise InvalidRuleError(f"{field} must be an array of strings")
    if len(set(value)) != len(value):
        raise InvalidRuleError(f"{field} must not contain duplicates")
    if pattern and any(not pattern.fullmatch(item) for item in value):
        raise InvalidRuleError(f"{field} contains invalid punctuation")
    if allowed and any(item not in allowed for item in value):
        raise InvalidRuleError(f"{field} contains an unsupported separator")
    return tuple(value)


def _validate_term(rule_id: str, term: Any) -> str:
    if not isinstance(term, str) or not term or term[0].isspace() or term[-1].isspace():
        raise InvalidRuleError(f"Rule {rule_id}: each term must be non-empty and have no outer whitespace")
    if not any(unicodedata.category(char)[0] in {"L", "M", "N"} for char in term):
        raise InvalidRuleError(f"Rule {rule_id}: each term must contain at least one letter or number")
    return term


def validate_rule_group(raw: Any, *, expected_lang: str | None) -> list[Rule]:
    """Validate one grouped rule and expand it to one literal rule per term."""
    rule = _required_object(raw, {"schemaVersion", "id", "lang", "match", "terms"}, "rule")
    if rule["schemaVersion"] != "1.0":
        raise InvalidRuleError("Rule schemaVersion must be '1.0'")
    rule_id = rule["id"]
    if not isinstance(rule_id, str) or not _ID_RE.fullmatch(rule_id):
        raise InvalidRuleError("Rule id must be a lowercase stable identifier")
    lang = rule["lang"]
    if not isinstance(lang, str) or not _LANG_RE.fullmatch(lang) or lang.casefold() == "all":
        raise InvalidRuleError(f"Rule {rule_id}: lang must be a language tag such as 'en' or 'es-mx'")
    if expected_lang is not None and lang.casefold() != expected_lang.casefold():
        raise InvalidRuleError(f"Rule {rule_id}: lang {lang} does not match file {expected_lang}")

    match = _required_object(rule["match"], {"punctuationVariants", "leadingSeparators"}, f"rule {rule_id} match")
    variants = _string_array(match["punctuationVariants"], "punctuationVariants", pattern=_PUNCT_RE)
    if not variants:
        raise InvalidRuleError(f"Rule {rule_id}: punctuationVariants cannot be empty")
    separators = _string_array(match["leadingSeparators"], "leadingSeparators", allowed=_SEPARATORS)

    terms = rule["terms"]
    if not isinstance(terms, list) or not terms:
        raise InvalidRuleError(f"Rule {rule_id}: terms must be a non-empty array of strings")
    parsed_terms = [_validate_term(rule_id, term) for term in terms]
    folded = [term.casefold() for term in parsed_terms]
    if len(set(folded)) != len(folded):
        raise InvalidRuleError(f"Rule {rule_id}: terms must not contain duplicates")

    return [Rule(rule_id, lang, term, variants, separators) for term in parsed_terms]


def _read_rule_file(path: Path) -> list[Rule]:
    try:
        raw_rules = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidRuleError(f"Cannot load rule file {path}: {exc}") from exc
    if not isinstance(raw_rules, list):
        raise InvalidRuleError(f"Rule file {path} must contain an array")

    rules: list[Rule] = []
    seen_ids: set[str] = set()
    for raw in raw_rules:
        expanded = validate_rule_group(raw, expected_lang=None)
        if expanded[0].id in seen_ids:
            raise DuplicateRuleIdError(f"Duplicate rule id: {expanded[0].id}")
        seen_ids.add(expanded[0].id)
        rules.extend(expanded)
    return rules


def load_builtin_rules() -> tuple[Rule, ...]:
    """Load the built-in prefix and suffix rules from the shared rules directory."""
    rules_dir = _shared_rules_dir()
    rule_files = sorted(rules_dir.glob("*.json"))
    # Skip regexp-rules.json (handled separately)
    rule_files = [f for f in rule_files if f.name != "regexp-rules.json"]
    rules: list[Rule] = []
    seen_ids: set[str] = set()
    seen_terms: set[tuple[str, str]] = set()
    for path in rule_files:
        file_rules = _read_rule_file(path)
        file_ids = {rule.id for rule in file_rules}
        overlap = seen_ids & file_ids
        if overlap:
            raise DuplicateRuleIdError(f"Duplicate rule id: {', '.join(sorted(overlap))}")
        seen_ids |= file_ids
        for rule in file_rules:
            key = (rule.lang.casefold(), rule.term.casefold())
            if key in seen_terms:
                raise InvalidRuleError(f"Duplicate term {rule.term!r} for {rule.lang}")
            seen_terms.add(key)
        rules.extend(file_rules)
    return tuple(rules)


def load_regexp_rules() -> tuple[RegexRule, ...]:
    """Load the optional, language-neutral regular-expression rules."""
    rules_dir = _shared_rules_dir()
    path = rules_dir / "regexp-rules.json"
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidRuleError(f"Cannot load regexp rule file {path}: {exc}") from exc
    if not isinstance(records, list):
        raise InvalidRuleError(f"Regexp rule file {path} must contain an array")

    parsed: list[RegexRule] = []
    for raw in records:
        # Pop lang before _required_object (lang is validated separately)
        lang = raw.pop("lang")
        rule = _required_object(
            raw,
            {"schemaVersion", "id", "pattern"},
            "regexp rule",
        )
        rule_id = rule["id"]
        if rule["schemaVersion"] != "1.0" or not isinstance(rule_id, str) or not _ID_RE.fullmatch(rule_id):
            raise InvalidRuleError("Regexp rule requires schemaVersion '1.0' and a valid stable id")
        if not isinstance(lang, str) or not _LANG_RE.fullmatch(lang):
            raise InvalidRuleError(f"Regexp rule {rule_id}: invalid lang value")
        if rule["pattern"] != r"\w{1,10}\.":
            raise InvalidRuleError(f"Regexp rule {rule_id}: unsupported v1 pattern")
        parsed.append(RegexRule(rule_id, lang, rule["pattern"]))

    if len({rule.id for rule in parsed}) != len(parsed):
        raise DuplicateRuleIdError("Duplicate regexp rule id")
    return tuple(parsed)
