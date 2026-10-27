"""Build hook: enforce current-spec support and bundle canonical rule data."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist

PROJECT_DIR = Path(__file__).resolve().parent


def shared_root() -> Path:
    """Locate canonical shared artifacts in a checkout or generated sdist."""
    bundled = PROJECT_DIR / ".acrotrim-shared"
    if (bundled / "spec" / "CURRENT").is_file():
        return bundled
    repository = PROJECT_DIR.parents[1]
    if (repository / "spec" / "CURRENT").is_file():
        return repository
    raise RuntimeError("Cannot find repository-level spec/ and rules/ artifacts")


def current_spec(shared: Path) -> str:
    version = (shared / "spec" / "CURRENT").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"v[1-9][0-9]*", version):
        raise RuntimeError("spec/CURRENT must contain a version such as 'v1'")
    if not (shared / "spec" / version / "conformance").is_dir():
        raise RuntimeError(f"Current spec {version} has no conformance directory")
    return version


def check_spec_compatibility(shared: Path) -> str:
    version = current_spec(shared)
    compat_file = PROJECT_DIR / "src" / "acrotrim" / "_compat.py"
    source = compat_file.read_text(encoding="utf-8")
    match = re.search(r'^SUPPORTED_SPEC_VERSION\s*=\s*[\"\']([^\"\']+)[\"\']', source, re.MULTILINE)
    if not match:
        raise RuntimeError("Python implementation must declare SUPPORTED_SPEC_VERSION in acrotrim/_compat.py")
    supported = match.group(1)
    if supported != version:
        raise RuntimeError(
            f"Cannot build AcroTrim Python package: current spec is {version}, "
            f"but this implementation declares {supported}. Update the implementation and conformance first."
        )
    return version


def run_current_conformance(shared: Path) -> None:
    """Run the current spec's language-neutral fixtures before packaging."""
    version = check_spec_compatibility(shared)
    sys.path.insert(0, str(PROJECT_DIR / "src"))
    try:
        from acrotrim import trim_name
        from acrotrim.errors import AcroTrimError

        fixture_dir = shared / "spec" / version / "conformance"
        fixtures = sorted(fixture_dir.glob("*.jsonl"))
        if not fixtures:
            raise RuntimeError(f"No conformance fixtures found for {version}")
        count = 0
        for fixture_file in fixtures:
            for line_number, line in enumerate(fixture_file.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                count += 1
                case = json.loads(line)
                label = f"{fixture_file.name}:{line_number} ({case.get('id', 'unnamed')})"
                try:
                    result = trim_name(
                        case.get("input"),
                        strict=case.get("strict", False),
                        lang=case.get("lang"),
                    )
                except AcroTrimError as exc:
                    expected_error = case.get("expectedError")
                    if expected_error != exc.code:
                        raise RuntimeError(f"Conformance failure {label}: got error {exc.code}, expected {expected_error}") from exc
                    continue
                except Exception as exc:  # report unexpected implementation failures clearly
                    raise RuntimeError(f"Conformance failure {label}: unexpected {type(exc).__name__}: {exc}") from exc

                if "expectedError" in case:
                    raise RuntimeError(f"Conformance failure {label}: expected error {case['expectedError']}, got a result")
                expected = case["expected"]
                if result != expected:
                    raise RuntimeError(f"Conformance failure {label}: got {result!r}, expected {expected!r}")
        if count == 0:
            raise RuntimeError(f"No conformance cases found for {version}")
        return version
    finally:
        if sys.path and sys.path[0] == str(PROJECT_DIR / "src"):
            sys.path.pop(0)
        for module_name in tuple(sys.modules):
            if module_name == "acrotrim" or module_name.startswith("acrotrim."):
                del sys.modules[module_name]


class build_py(_build_py):
    """Bundle the repository's canonical data into the wheel package."""

    def run(self):
        shared = shared_root()
        version = run_current_conformance(shared)
        package_dir = Path(self.build_lib) / "acrotrim"
        if package_dir.exists():
            shutil.rmtree(package_dir)
        super().run()

        data_dir = package_dir / "data"
        rules_target = data_dir / "rules"
        if rules_target.exists():
            shutil.rmtree(rules_target)
        shutil.copytree(shared / "rules", rules_target)
        version_file = data_dir / "spec-version.txt"
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(version + "\n", encoding="utf-8")
        self._acrotrim_data_outputs = [str(path) for path in data_dir.rglob("*") if path.is_file()]

    def get_outputs(self, include_bytecode=1):
        outputs = super().get_outputs(include_bytecode)
        return outputs + getattr(self, "_acrotrim_data_outputs", [])


class sdist(_sdist):
    """Carry a snapshot of current shared inputs so an sdist remains buildable."""

    def run(self):
        run_current_conformance(shared_root())
        super().run()

    def make_release_tree(self, base_dir, files):
        super().make_release_tree(base_dir, files)
        shared = shared_root()
        target = Path(base_dir) / ".acrotrim-shared"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(shared / "spec", target / "spec")
        shutil.copytree(shared / "rules", target / "rules")


setup(cmdclass={"build_py": build_py, "sdist": sdist})
