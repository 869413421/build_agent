"""Tutorial chapter hard-rule checker.

Checks:
1) Required top-level headings exist.
2) No empty bash/powershell code blocks.
3) Every "文件：" marker has nearby bash + powershell creation blocks.
4) Code drift check: code block after "文件：[...](path)" matches real file content.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


REQUIRED_HEADING_KEYWORDS = [
    "## 目标",
    "架构位置说明",
    "## 前置条件",
    "本章主线改动范围",
    "## 运行命令",
    "增量闭环验证",
    "## 验证清单",
    "## 常见问题",
    "本章 DoD",
    "下一章预告",
]


def find_missing_headings(text: str) -> list[str]:
    return [h for h in REQUIRED_HEADING_KEYWORDS if h not in text]


def find_empty_code_blocks(lines: list[str]) -> list[str]:
    issues: list[str] = []
    for i in range(len(lines) - 1):
        line = lines[i].strip().lower()
        nxt = lines[i + 1].strip()
        if line in ("```bash", "```powershell") and nxt == "```":
            issues.append(f"空代码块: 行 {i+1} ({line})")
    return issues


def find_file_block_issues(lines: list[str]) -> list[str]:
    issues: list[str] = []
    file_line_idxs = [i for i, l in enumerate(lines) if "文件：" in l]
    for idx in file_line_idxs:
        # Scan a small window before each 文件： marker.
        start = max(0, idx - 18)
        window = "\n".join(lines[start:idx])
        has_bash = "```bash" in window
        has_ps = "```powershell" in window
        if not has_bash or not has_ps:
            issues.append(
                f"文件块缺创建命令: 行 {idx+1} (bash={has_bash}, powershell={has_ps})"
            )
    return issues


def find_bad_file_markers(lines: list[str]) -> list[str]:
    """Heuristic: files should be markdown links for click-through consistency."""
    issues: list[str] = []
    pattern = re.compile(r"^文件：\s*(?!\[).+")
    for i, line in enumerate(lines):
        if pattern.search(line.strip()):
            issues.append(f"文件路径非链接形式: 行 {i+1}")
    return issues


def _normalize_text(text: str) -> str:
    # Normalize line endings and trim right-side whitespace to reduce false positives.
    text = text.lstrip("\ufeff")
    norm_lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(norm_lines).strip() + "\n"


def find_code_drift_issues(md_path: Path, lines: list[str]) -> list[str]:
    issues: list[str] = []
    file_link_re = re.compile(r"^文件：\s*\[[^\]]+\]\(([^)]+)\)")

    i = 0
    while i < len(lines):
        m = file_link_re.match(lines[i].strip())
        if not m:
            i += 1
            continue

        rel = m.group(1).strip()
        file_path = (md_path.parent / rel).resolve()
        if not file_path.exists():
            issues.append(f"漂移检查目标文件不存在: 行 {i+1} -> {rel}")
            i += 1
            continue

        # Find next fenced code block after file marker.
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith("```"):
            j += 1
        if j >= len(lines):
            issues.append(f"文件标记后缺代码块: 行 {i+1}")
            i += 1
            continue

        fence = lines[j].strip()
        if fence == "```":
            issues.append(f"代码块语言缺失: 行 {j+1}")
            i = j + 1
            continue

        lang = fence[3:].strip().lower()
        if lang not in {"python", "toml", "json", "yaml", "yml"}:
            # Skip non-source snippets.
            i = j + 1
            continue

        k = j + 1
        while k < len(lines) and lines[k].strip() != "```":
            k += 1
        if k >= len(lines):
            issues.append(f"代码块未闭合: 行 {j+1}")
            i = j + 1
            continue

        snippet = "\n".join(lines[j + 1 : k]) + "\n"
        actual = file_path.read_text(encoding="utf-8")

        if _normalize_text(snippet) != _normalize_text(actual):
            issues.append(f"代码漂移: 行 {i+1} -> {rel}")

        i = k + 1

    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to tutorial markdown file")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"[ERROR] 文件不存在: {path}")
        return 2

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    issues: list[str] = []

    missing = find_missing_headings(text)
    if missing:
        issues.extend([f"缺少段落: {h}" for h in missing])

    issues.extend(find_empty_code_blocks(lines))
    issues.extend(find_file_block_issues(lines))
    issues.extend(find_bad_file_markers(lines))
    issues.extend(find_code_drift_issues(path, lines))

    if issues:
        print("[FAIL] 发现问题:")
        for item in issues:
            print(f"- {item}")
        return 1

    print("[PASS] 结构与硬约束检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
