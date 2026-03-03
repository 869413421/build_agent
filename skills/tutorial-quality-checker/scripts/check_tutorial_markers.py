"""Tutorial chapter hard-rule checker.

Checks:
1) Required top-level headings exist.
2) No empty bash/powershell code blocks.
3) Every "文件：" marker has nearby bash + powershell creation blocks.
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

    if issues:
        print("[FAIL] 发现问题:")
        for item in issues:
            print(f"- {item}")
        return 1

    print("[PASS] 结构与硬约束检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
