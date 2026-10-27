"""Errors raised while loading rules or validating input."""


class AcroTrimError(Exception):
    code = "acrotrim_error"


class InvalidInputError(AcroTrimError, TypeError):
    code = "invalid_input"


class InvalidRuleError(AcroTrimError, ValueError):
    code = "invalid_rule"


class DuplicateRuleIdError(InvalidRuleError):
    code = "duplicate_rule_id"
