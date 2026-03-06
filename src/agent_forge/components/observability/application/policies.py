"""Observability 策略实现。"""

from __future__ import annotations

import hashlib
from typing import Any

from agent_forge.components.observability.domain.schemas import RedactionPolicy, TraceRecord


class Sampler:
    """确定性采样器。"""

    def __init__(self, success_sample_rate: float = 0.1, keep_error_events: bool = True) -> None:
        """初始化采样器。

        Args:
            success_sample_rate: 成功事件采样比例。
            keep_error_events: 错误事件是否强制保留。
        """

        self.success_sample_rate = success_sample_rate
        self.keep_error_events = keep_error_events

    def should_keep(self, record: TraceRecord) -> bool:
        """判断记录是否保留。

        Args:
            record: 待采样记录。

        Returns:
            bool: 需要保留返回 True。
        """

        if self.keep_error_events and record.error_code:
            return True
        if self.success_sample_rate >= 1.0:
            return True
        if self.success_sample_rate <= 0.0:
            return False
        basis = f"{record.trace_id}:{record.run_id}:{record.step_id}:{record.event_type}"
        hashed = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:8]
        ratio = int(hashed, 16) / 0xFFFFFFFF
        return ratio <= self.success_sample_rate


class Redactor:
    """递归脱敏器。"""

    def __init__(self, policy: RedactionPolicy | None = None) -> None:
        """初始化脱敏器。

        Args:
            policy: 脱敏策略，未传入则使用默认策略。
        """

        self.policy = policy or RedactionPolicy()
        self._masked_keys = {item.lower() for item in self.policy.masked_keys}

    def redact_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """脱敏 payload。

        Args:
            payload: 原始 payload。

        Returns:
            dict[str, Any]: 脱敏后的 payload 副本。
        """

        return self._redact_value(payload)

    def _redact_value(self, value: Any) -> Any:
        """递归处理任意值。

        Args:
            value: 待处理值。

        Returns:
            Any: 脱敏结果。
        """

        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for key, child in value.items():
                if key.lower() in self._masked_keys:
                    result[key] = self.policy.mask_text
                    continue
                result[key] = self._redact_value(child)
            return result
        if isinstance(value, list):
            return [self._redact_value(item) for item in value]
        return value

