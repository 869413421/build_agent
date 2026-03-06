"""Observability 内存存储实现。"""

from __future__ import annotations

from collections import defaultdict

from agent_forge.components.observability.domain.schemas import MetricPoint, TraceRecord


class InMemoryTraceSink:
    """内存 Trace 存储。"""

    def __init__(self) -> None:
        """初始化容器。"""

        self._records: list[TraceRecord] = []

    def write_trace(self, record: TraceRecord) -> None:
        """写入 trace 记录。

        Args:
            record: 标准化 trace 记录。
        """

        self._records.append(record)

    def query_traces(self, trace_id: str | None = None, run_id: str | None = None) -> list[TraceRecord]:
        """按条件查询 trace 记录。

        Args:
            trace_id: 可选链路 ID。
            run_id: 可选运行 ID。

        Returns:
            list[TraceRecord]: 命中的 trace 列表。
        """

        records = list(self._records)
        if trace_id is not None:
            records = [item for item in records if item.trace_id == trace_id]
        if run_id is not None:
            records = [item for item in records if item.run_id == run_id]
        return records


class InMemoryMetricsSink:
    """内存指标存储。"""

    def __init__(self) -> None:
        """初始化容器。"""

        self._points: list[MetricPoint] = []

    def write_metric(self, point: MetricPoint) -> None:
        """写入指标点。

        Args:
            point: 指标点对象。
        """

        self._points.append(point)

    def query_metrics(self, name: str | None = None) -> list[MetricPoint]:
        """查询指标点。

        Args:
            name: 可选指标名。

        Returns:
            list[MetricPoint]: 命中的指标点。
        """

        points = list(self._points)
        if name is not None:
            points = [item for item in points if item.name == name]
        return points


class InMemoryReplayStore:
    """内存回放数据存储。"""

    def __init__(self) -> None:
        """初始化容器。"""

        self._records: dict[tuple[str, str], list[dict]] = defaultdict(list)

    def append_tool_record(self, trace_id: str, run_id: str, record: dict) -> None:
        """追加工具录制记录。

        Args:
            trace_id: 链路 ID。
            run_id: 运行 ID。
            record: 录制记录。
        """

        self._records[(trace_id, run_id)].append(record)

    def get_tool_records(self, trace_id: str, run_id: str) -> list[dict]:
        """读取录制记录。

        Args:
            trace_id: 链路 ID。
            run_id: 运行 ID。

        Returns:
            list[dict]: 命中记录列表。
        """

        return list(self._records[(trace_id, run_id)])

