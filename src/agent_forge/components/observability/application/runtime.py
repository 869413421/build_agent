"""Observability 运行时实现。"""

from __future__ import annotations

import math
from contextvars import ContextVar
from datetime import datetime
from typing import TYPE_CHECKING, Any

from agent_forge.components.observability.application.interfaces import MetricsSink, ReplayStore, TraceSink
from agent_forge.components.observability.application.policies import Redactor, Sampler
from agent_forge.components.observability.domain.schemas import (
    ExportEnvelope,
    MetricPoint,
    RedactionPolicy,
    ReplayBundle,
    ReplayStep,
    SamplingPolicy,
    TraceRecord,
)
from agent_forge.components.observability.infrastructure import InMemoryMetricsSink, InMemoryReplayStore, InMemoryTraceSink
from agent_forge.components.protocol import ExecutionEvent, ToolCall, ToolResult
from agent_forge.components.tool_runtime import ToolExecutionRecord, ToolRuntimeEvent

if TYPE_CHECKING:
    from agent_forge.components.observability.application.hooks import ToolRuntimeObservabilityHook


class ObservabilityRuntime:
    """统一观测运行时。"""

    def __init__(
        self,
        *,
        sampling_policy: SamplingPolicy | None = None,
        redaction_policy: RedactionPolicy | None = None,
        trace_sink: TraceSink | None = None,
        metrics_sink: MetricsSink | None = None,
        replay_store: ReplayStore | None = None,
    ) -> None:
        """初始化观测运行时。

        Args:
            sampling_policy: 采样策略。
            redaction_policy: 脱敏策略。
            trace_sink: trace 存储实现。
            metrics_sink: 指标存储实现。
            replay_store: 回放存储实现。
        """

        self.sampling_policy = sampling_policy or SamplingPolicy()
        self.redaction_policy = redaction_policy or RedactionPolicy()
        self.trace_sink = trace_sink or InMemoryTraceSink()
        self.metrics_sink = metrics_sink or InMemoryMetricsSink()
        self.replay_store = replay_store or InMemoryReplayStore()
        self.sampler = Sampler(
            success_sample_rate=self.sampling_policy.success_sample_rate,
            keep_error_events=self.sampling_policy.keep_error_events,
        )
        self.redactor = Redactor(self.redaction_policy)
        self._trace_id_var: ContextVar[str] = ContextVar("obs_trace_id", default="trace_unknown")
        self._run_id_var: ContextVar[str] = ContextVar("obs_run_id", default="run_unknown")

    def set_default_context(self, trace_id: str, run_id: str) -> None:
        """设置默认上下文。

        Args:
            trace_id: 默认链路 ID。
            run_id: 默认运行 ID。
        """

        self._trace_id_var.set(trace_id)
        self._run_id_var.set(run_id)

    def get_current_context(self) -> tuple[str, str]:
        """读取当前任务上下文。

        Returns:
            tuple[str, str]: 当前任务的 (trace_id, run_id)。
        """

        return self._trace_id_var.get(), self._run_id_var.get()

    def engine_event_listener(self, event: ExecutionEvent) -> None:
        """Engine 监听器入口。

        Args:
            event: Engine 事件对象。
        """

        self.capture_engine_event(event)

    def capture_engine_event(self, event: ExecutionEvent) -> None:
        """记录 Engine 事件。

        Args:
            event: Engine 事件对象。
        """

        payload = self.redactor.redact_payload(event.payload)
        record = TraceRecord(
            trace_id=event.trace_id,
            run_id=event.run_id,
            step_id=event.step_id,
            parent_step_id=event.parent_step_id,
            event_type=event.event_type,
            source="engine",
            payload=payload,
            error_code=event.error.error_code if event.error else None,
            error_message=event.error.error_message if event.error else None,
        )
        self._write_trace_and_metrics(record)

    def capture_tool_event(self, event: ToolRuntimeEvent, trace_id: str | None = None, run_id: str | None = None) -> None:
        """记录 Tool Runtime 事件。

        Args:
            event: ToolRuntime 事件对象。
            trace_id: 可选链路 ID（优先级高于 payload 与默认上下文）。
            run_id: 可选运行 ID（优先级高于 payload 与默认上下文）。
        """

        payload = self.redactor.redact_payload(event.payload)
        current_trace_id, current_run_id = self.get_current_context()
        resolved_trace_id = str(trace_id or payload.get("trace_id") or current_trace_id)
        resolved_run_id = str(run_id or payload.get("run_id") or current_run_id)
        record = TraceRecord(
            trace_id=resolved_trace_id,
            run_id=resolved_run_id,
            step_id=event.step_id or f"tool_{event.tool_call_id or 'unknown'}",
            parent_step_id=str(payload.get("parent_step_id")) if payload.get("parent_step_id") else None,
            event_type=event.event_type,
            source="tool_runtime",
            payload=payload,
            error_code=event.error.error_code if event.error else None,
            error_message=event.error.error_message if event.error else None,
            latency_ms=event.latency_ms,
        )
        self._write_trace_and_metrics(record)

    def capture_tool_result(
        self,
        tool_call: ToolCall,
        result: ToolResult,
        trace_id: str | None = None,
        run_id: str | None = None,
    ) -> None:
        """记录工具执行结果用于回放。

        Args:
            tool_call: 工具调用对象。
            result: 工具执行结果对象。
            trace_id: 可选链路 ID。
            run_id: 可选运行 ID。
        """

        record = ToolExecutionRecord(
            tool_call_id=tool_call.tool_call_id,
            tool_name=tool_call.tool_name,
            principal=tool_call.principal,
            status=result.status,
            args_masked=self.redactor.redact_payload(tool_call.args),
            output=self.redactor.redact_payload(result.output),
            error=result.error,
            latency_ms=result.latency_ms,
        )
        self.capture_tool_record(record, trace_id=trace_id, run_id=run_id)

    def capture_tool_record(self, record: ToolExecutionRecord, trace_id: str | None = None, run_id: str | None = None) -> None:
        """写入工具录制记录。

        Args:
            record: 结构化工具执行记录。
            trace_id: 可选链路 ID。
            run_id: 可选运行 ID。
        """

        current_trace_id, current_run_id = self.get_current_context()
        self.replay_store.append_tool_record(
            trace_id=trace_id or current_trace_id,
            run_id=run_id or current_run_id,
            record=record.model_dump(),
        )

    def build_tool_hook(self) -> "ToolRuntimeObservabilityHook":
        """构建 Tool Runtime 观测 hook。

        Returns:
            ToolRuntimeObservabilityHook: 可直接注册到 ToolRuntime 的 hook。
        """

        from agent_forge.components.observability.application.hooks import ToolRuntimeObservabilityHook

        return ToolRuntimeObservabilityHook(self)

    def replay_structure(self, trace_id: str, run_id: str) -> ReplayBundle:
        """按链路构建回放结构。

        Args:
            trace_id: 链路 ID。
            run_id: 运行 ID。

        Returns:
            ReplayBundle: 回放数据包。
        """

        traces = sorted(
            self.trace_sink.query_traces(trace_id=trace_id, run_id=run_id),
            key=lambda item: item.created_at,
        )
        steps = [
            ReplayStep(
                step_id=record.step_id,
                parent_step_id=record.parent_step_id,
                event_type=record.event_type,
                source=record.source,
                payload=record.payload,
                error_code=record.error_code,
                created_at=record.created_at,
            )
            for record in traces
        ]
        tool_records = self.replay_store.get_tool_records(trace_id=trace_id, run_id=run_id)
        return ReplayBundle(trace_id=trace_id, run_id=run_id, steps=steps, tool_records=tool_records)

    def export(self, trace_id: str | None = None, run_id: str | None = None) -> ExportEnvelope:
        """导出观测数据。

        Args:
            trace_id: 可选链路 ID。
            run_id: 可选运行 ID。

        Returns:
            ExportEnvelope: 导出数据包。
        """

        traces = self.trace_sink.query_traces(trace_id=trace_id, run_id=run_id)
        metrics = self.metrics_sink.query_metrics()
        replay = None
        if trace_id is not None and run_id is not None:
            replay = self.replay_structure(trace_id=trace_id, run_id=run_id)
        return ExportEnvelope(traces=traces, metrics=metrics, replay=replay)

    def aggregate_metrics(self, trace_id: str | None = None, run_id: str | None = None) -> dict[str, float]:
        """计算聚合指标。

        Args:
            trace_id: 可选链路 ID。
            run_id: 可选运行 ID。

        Returns:
            dict[str, float]: 聚合指标字典。
        """

        records = self.trace_sink.query_traces(trace_id=trace_id, run_id=run_id)
        total = len(records)
        errors = sum(1 for item in records if item.error_code is not None)
        retries = sum(1 for item in records if item.payload.get("decision") == "retry" or item.payload.get("attempt", 0) > 0)
        latencies = sorted(item.latency_ms for item in records if item.latency_ms is not None)
        unique_runs = {item.run_id for item in records}

        if total == 0:
            return {
                "success_rate": 0.0,
                "failure_rate": 0.0,
                "p95_latency_ms": 0.0,
                "retry_rate": 0.0,
                "throughput_runs_per_second": 0.0,
            }

        start = min(_parse_iso(item.created_at) for item in records)
        end = max(_parse_iso(item.created_at) for item in records)
        duration_sec = max((end - start).total_seconds(), 1.0)
        p95 = _p95(latencies) if latencies else 0.0
        return {
            "success_rate": round((total - errors) / total, 4),
            "failure_rate": round(errors / total, 4),
            "p95_latency_ms": round(p95, 3),
            "retry_rate": round(retries / total, 4),
            "throughput_runs_per_second": round(len(unique_runs) / duration_sec, 4),
        }

    def _write_trace_and_metrics(self, record: TraceRecord) -> None:
        """按策略写入 trace 和指标。

        Args:
            record: 标准化 trace 记录。
        """

        if self.sampler.should_keep(record):
            self.trace_sink.write_trace(record)
        self.metrics_sink.write_metric(
            MetricPoint(
                name="events_total",
                value=1.0,
                labels={
                    "source": record.source,
                    "event_type": record.event_type,
                    "status": "error" if record.error_code else "ok",
                },
            )
        )
        if record.latency_ms is not None:
            self.metrics_sink.write_metric(
                MetricPoint(
                    name="latency_ms",
                    value=float(record.latency_ms),
                    labels={"source": record.source, "event_type": record.event_type},
                )
            )


def _parse_iso(value: str) -> datetime:
    """解析 ISO 时间字符串。

    Args:
        value: ISO 时间字符串。

    Returns:
        datetime: 解析后的时间对象。
    """

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _p95(values: list[int]) -> float:
    """计算 P95。

    Args:
        values: 排序后的整数列表。

    Returns:
        float: P95 数值。
    """

    if not values:
        return 0.0
    idx = max(0, math.ceil(len(values) * 0.95) - 1)
    return float(values[idx])
