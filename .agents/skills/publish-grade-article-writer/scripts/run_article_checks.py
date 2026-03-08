from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> int:
    print(f"[run] {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=str(cwd))
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run article validation checks for this repository.")
    parser.add_argument("--file", required=True, help="Path to the article markdown file")
    parser.add_argument("--snapshot", help="Path to an existing code_block_guard snapshot for verify")
    parser.add_argument("--inventory-out", help="Create a new snapshot at this path before verify")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[4]
    article = (repo_root / args.file).resolve() if not Path(args.file).is_absolute() else Path(args.file)
    if not article.exists():
        print(f"[error] article not found: {article}")
        return 2

    checker = repo_root / ".agents/skills/tutorial-quality-checker/scripts/check_tutorial_markers.py"
    guard = repo_root / ".agents/skills/publish-grade-article-auditor/scripts/code_block_guard.py"

    rc = run([sys.executable, str(checker), "--file", str(article)], repo_root)
    if rc != 0:
        return rc

    if args.inventory_out:
        inventory_out = (repo_root / args.inventory_out).resolve() if not Path(args.inventory_out).is_absolute() else Path(args.inventory_out)
        inventory_out.parent.mkdir(parents=True, exist_ok=True)
        rc = run([sys.executable, str(guard), "inventory", "--file", str(article), "--out", str(inventory_out)], repo_root)
        if rc != 0:
            return rc

    if args.snapshot:
        snapshot = (repo_root / args.snapshot).resolve() if not Path(args.snapshot).is_absolute() else Path(args.snapshot)
        rc = run([sys.executable, str(guard), "verify", "--before", str(snapshot), "--file", str(article)], repo_root)
        if rc != 0:
            return rc

    print("[ok] article checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
