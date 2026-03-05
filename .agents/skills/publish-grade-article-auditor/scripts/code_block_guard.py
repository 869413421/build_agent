#!/usr/bin/env python3
"""Code block guard for markdown articles.

Purpose:
1. Create an inventory of all fenced code blocks before editing.
2. Verify that no original code block is deleted after editing.

This guard enforces "no code deletion" while still allowing extra code blocks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

FENCE_RE = re.compile(r"^```(?P<lang>[A-Za-z0-9_+-]*)\s*$")


@dataclass
class CodeBlock:
    """Represent one fenced code block."""

    lang: str
    content: str

    @property
    def digest(self) -> str:
        """Return stable sha256 digest of code content."""

        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()


def extract_code_blocks(md_text: str) -> list[CodeBlock]:
    """Extract fenced code blocks from markdown text.

    Args:
        md_text: Raw markdown content.

    Returns:
        List of extracted code blocks.
    """

    lines = md_text.splitlines()
    blocks: list[CodeBlock] = []

    in_block = False
    lang = ""
    buf: list[str] = []

    for line in lines:
        if not in_block:
            m = FENCE_RE.match(line)
            if m:
                in_block = True
                lang = m.group("lang") or "plain"
                buf = []
            continue

        # inside block
        if line.strip() == "```":
            blocks.append(CodeBlock(lang=lang, content="\n".join(buf)))
            in_block = False
            lang = ""
            buf = []
            continue

        buf.append(line)

    return blocks


def _count_digests(blocks: Iterable[CodeBlock]) -> dict[str, int]:
    """Count block digests."""

    result: dict[str, int] = {}
    for b in blocks:
        result[b.digest] = result.get(b.digest, 0) + 1
    return result


def inventory(file_path: Path, out_path: Path) -> int:
    """Create code inventory json file.

    Args:
        file_path: Markdown file path.
        out_path: Output inventory json file.

    Returns:
        Process exit code.
    """

    text = file_path.read_text(encoding="utf-8")
    blocks = extract_code_blocks(text)
    digest_counts = _count_digests(blocks)

    payload = {
        "file": str(file_path),
        "total_blocks": len(blocks),
        "digest_counts": digest_counts,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[inventory] file={file_path} blocks={len(blocks)} out={out_path}")
    return 0


def verify(before_path: Path, file_path: Path) -> int:
    """Verify no original code block has been deleted.

    Args:
        before_path: Baseline inventory json path.
        file_path: Current markdown file path.

    Returns:
        0 when pass, 1 when fail.
    """

    before = json.loads(before_path.read_text(encoding="utf-8"))
    before_counts: dict[str, int] = before.get("digest_counts", {})

    text = file_path.read_text(encoding="utf-8")
    now_blocks = extract_code_blocks(text)
    now_counts = _count_digests(now_blocks)

    missing: list[tuple[str, int, int]] = []
    for digest, old_count in before_counts.items():
        new_count = now_counts.get(digest, 0)
        if new_count < old_count:
            missing.append((digest, old_count, new_count))

    if missing:
        print("[verify] FAILED: some original code blocks were removed or changed.")
        for digest, old_count, new_count in missing:
            print(f"  - digest={digest[:12]} old={old_count} new={new_count}")
        return 1

    print(
        "[verify] PASS: no original code block deleted "
        f"(before={before.get('total_blocks', 0)} now={len(now_blocks)})."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""

    parser = argparse.ArgumentParser(description="Markdown code block guard")
    sub = parser.add_subparsers(dest="cmd", required=True)

    inv = sub.add_parser("inventory", help="create baseline inventory")
    inv.add_argument("--file", required=True, help="markdown file path")
    inv.add_argument("--out", required=True, help="output json path")

    ver = sub.add_parser("verify", help="verify no code block deletion")
    ver.add_argument("--before", required=True, help="baseline json path")
    ver.add_argument("--file", required=True, help="markdown file path")

    return parser


def main() -> int:
    """CLI entry."""

    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "inventory":
        return inventory(Path(args.file), Path(args.out))
    if args.cmd == "verify":
        return verify(Path(args.before), Path(args.file))

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
