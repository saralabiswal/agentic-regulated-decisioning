# Author: Sarala Biswal
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {
    ".css",
    ".html",
    ".json",
    ".md",
    ".py",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
EXCLUDED_PARTS = {
    ".git",
    ".local",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
}
EXCLUDED_FILES = {
    Path("docs/planning/NAMING_CONVENTIONS.md"),
    Path("tests/test_naming_conventions.py"),
    Path("ui/package-lock.json"),
}

PROHIBITED_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bduck[\s_-]*creek\b",
        r"\bduckcreek\b",
        r"\bguidewire\b",
        r"\bverisk\b",
        r"\biso[\s_/-]",
        r"[\s_/-]iso\b",
        r"\bequifax\b",
        r"\bexperian\b",
        r"\btransunion\b",
        r"\bfannie\b",
        r"\bfreddie\b",
        r"\bepic\b",
        r"\bcerner\b",
        r"\bathena\b",
        r"\bmcg\b",
        r"\binterqual\b",
        r"\bavaility\b",
        r"\bsalesforce\b",
        r"\benvestnet\b",
        r"\borion\b",
        r"\bpershing\b",
        r"\bschwab\b",
        r"\bmorningstar\b",
        r"\bbloomberg\b",
        r"\bfinra\b",
        r"\becoa\b",
        r"\bhipaa\b",
        r"\bcfpb\b",
        r"\bsec\s+reg\b",
        r"\breg\s+bi\b",
        r"\bsnowflake\b",
        r"\bdatabricks\b",
        r"\bconfluent\b",
        r"\baws\b",
        r"\bazure\b",
        r"\bgoogle\s+cloud\b",
        r"\bnaic\b",
        r"\bsox\b",
    )
)


def _is_scanned_file(path: Path) -> bool:
    relative_path = path.relative_to(REPO_ROOT)
    if relative_path in EXCLUDED_FILES:
        return False
    if any(part in EXCLUDED_PARTS for part in relative_path.parts):
        return False
    return path.suffix in TEXT_EXTENSIONS


def test_codebase_uses_generic_names_only() -> None:
    violations: list[str] = []

    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file() or not _is_scanned_file(path):
            continue

        relative_path = path.relative_to(REPO_ROOT)
        haystacks = [relative_path.as_posix()]
        haystacks.extend(path.read_text(encoding="utf-8", errors="ignore").splitlines())

        for line_number, text in enumerate(haystacks):
            for pattern in PROHIBITED_PATTERNS:
                if pattern.search(text):
                    if line_number == 0:
                        location = str(relative_path)
                    else:
                        location = f"{relative_path}:{line_number}"
                    violations.append(
                        f"{location} contains disallowed name matching {pattern.pattern!r}"
                    )

    assert not violations, "\n".join(violations)
