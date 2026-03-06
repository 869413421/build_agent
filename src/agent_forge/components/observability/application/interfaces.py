"""Observability 抽象接口。"""

from __future__ import annotations

from typing import Protocol

from agent_forge.components.observability.domain.schemas import MetricPoint, TraceRecord


class TraceSink(Protocol):
    """Trace 存储接口。"""

    def write_trace(self, record: TraceRecord) -> None:
        """写入一条 trace 记录。

        Args:
            record: 标准化 trace 记录。
        """

    def query_traces(self, trace_id: str | None = None, run_id: str | None = None) -> list[TraceRecord]:
        """按条件查询 trace 记录。

        Args:
            trace_id: 可选链路 ID。
            run_id: 可选运行 ID。

        Returns:
            list[TraceRecord]: 命中的 trace 列表。
        """


class MetricsSink(Protocol):
    """指标存储接口。"""

    def write_metric(self, point: MetricPoint) -> None:
        """写入一条指标记录。

        Args:
            point: 指标点对象。
        """

    def query_metrics(self, name: str | None = None) -> list[MetricPoint]:
        """查询指标记录。

        Args:
            name: 可选指标名。

        Returns:
            list[MetricPoint]: 命中的指标点列表。
        """


class ReplayStore(Protocol):
    """回放记录存储接口。"""

    def append_tool_record(self, trace_id: str, run_id: str, record: dict) -> None:
        """追加工具执行录制记录。

        Args:
            trace_id: 链路 ID。
            run_id: 运行 ID。
            record: 工具执行记录字典。
        """

    def get_tool_records(self, trace_id: str, run_id: str) -> list[dict]:
        """读取工具执行录制记录。

        Args:
            trace_id: 链路 ID。
            run_id: 运行 ID。

        Returns:
            list[dict]: 录制记录列表。
        """

