"""String-in/string-out AcroTrim API."""

from ._compat import SUPPORTED_SPEC_VERSION as __spec_version__
from .engine import trim_name

__all__ = ["__spec_version__", "trim_name"]
