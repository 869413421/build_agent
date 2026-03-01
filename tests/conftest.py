"""测试启动配置。

将 `framework/` 加入 Python 路径，确保测试可直接导入本地包。
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK_DIR = ROOT / "framework"
if str(FRAMEWORK_DIR) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_DIR))

