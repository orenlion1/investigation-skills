#!/usr/bin/env python3
"""Deterministic, dependency-free validation for one repository skill package."""

from __future__ import annotations

import re
import sys
from pathlib import Path


MAX_SKILL_BYTES = 1_048_576
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def main() -> int:
    if len(sys.argv) != 2:
        return fail("usage: quick-validate-skill.py <skill-directory>")

    skill_dir = Path(sys.argv[1])
    skill_file = skill_dir / "SKILL.md"
    if not skill_dir.is_dir() or skill_dir.is_symlink():
        return fail(f"skill directory must be a real directory: {skill_dir}")
    if not skill_file.is_file() or skill_file.is_symlink():
        return fail(f"SKILL.md must be a regular non-symlink file: {skill_file}")

    size = skill_file.stat().st_size
    if size < 1 or size > MAX_SKILL_BYTES:
        return fail(f"SKILL.md size is outside 1..{MAX_SKILL_BYTES} bytes: {size}")

    source = skill_file.read_text(encoding="utf-8")
    lines = source.splitlines()
    if not lines or lines[0] != "---":
        return fail(f"SKILL.md lacks opening YAML frontmatter: {skill_file}")
    try:
        closing_index = lines.index("---", 1)
    except ValueError:
        return fail(f"SKILL.md lacks closing YAML frontmatter: {skill_file}")

    fields: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if not line.strip() or line.startswith((" ", "\t", "#")):
            continue
        if ":" not in line:
            return fail(f"invalid frontmatter line in {skill_file}: {line}")
        key, value = line.split(":", 1)
        fields[key.strip()] = unquote(value.strip())

    name = fields.get("name", "")
    description = fields.get("description", "")
    if not NAME_PATTERN.fullmatch(name):
        return fail(f"invalid or missing skill name: {name or '<missing>'}")
    if name != skill_dir.name:
        return fail(f"skill name {name!r} does not match directory {skill_dir.name!r}")
    if not description:
        return fail(f"missing description: {skill_file}")
    if len(description) > 1024:
        return fail(f"description exceeds 1024 characters: {skill_file}")
    if "<" in description or ">" in description:
        return fail(f"description contains unsupported angle brackets: {skill_file}")
    if re.search(r"\[TODO(?:[:\]])|\bTBD\b|\bYOUR_[A-Z_]+\b", source, re.IGNORECASE):
        return fail(f"scaffold placeholder remains in {skill_file}")

    print(f"valid skill package: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
