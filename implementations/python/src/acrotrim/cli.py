"""Minimal command-line interface for AcroTrim."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from .engine import trim_name
from .errors import AcroTrimError


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="acrotrim",
        description="Remove configured name prefixes and suffixes.",
        epilog='Example: acrotrim "Dr. Jane Smith Jr."',
    )
    parser.add_argument("name", help="name string to trim; quote it if it contains spaces")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="also remove general word-plus-period abbreviations at name boundaries",
    )
    parser.add_argument(
        "--lang",
        metavar="TAG",
        help="limit literal rules to this language tag (including parent tags, e.g. es-MX includes es)",
    )
    args = parser.parse_args(argv)
    try:
        print(trim_name(args.name, strict=args.strict, lang=args.lang))
    except AcroTrimError as exc:
        print(f"acrotrim: {exc.code}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
