"""Tool Runtime application shared utilities."""

from __future__ import annotations

from typing import Any


def mask_sensitive_fields(args: dict[str, Any], sensitive_fields: set[str]) -> dict[str, Any]:
    """脱敏指定参数字段。

    Args:
        args: 原始参数字典。
        sensitive_fields: 需要脱敏的字段集合。

    Returns:
        dict[str, Any]: 脱敏后的参数副本。
    """
    masked = dict(args)
    for key in sensitive_fields:
        if key in masked:
            masked[key] = "***"
    return masked
