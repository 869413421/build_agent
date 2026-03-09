"""`AgentRuntime` 编排层。"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from agent_forge.components.context_engineering import ContextEngineeringRuntime
from agent_forge.components.context_engineering.domain import CitationItem
from agent_forge.components.engine import EngineLimits, EngineLoop, ExecutionPlan, PlanStep, ReflectDecision, RunContext, StepOutcome
from agent_forge.components.evaluator import EvaluationRequest, EvaluatorRuntime
from agent_forge.components.memory import MemoryReadQuery, MemoryWriteRequest, to_context_messages
from agent_forge.components.model_runtime import ModelRequest, ModelResponse, ModelRuntime
from agent_forge.components.observability import ObservabilityRuntime
from agent_forge.components.protocol import AgentMessage, AgentState, ErrorInfo, ExecutionEvent, FinalAnswer, ToolCall, ToolResult, build_initial_state
from agent_forge.components.retrieval import RetrievalQuery, RetrievalRuntime
from agent_forge.components.safety import SafetyCheckRequest, SafetyRuntime, apply_output_safety
from agent_forge.components.tool_runtime import ToolRuntime
from agent_forge.runtime.defaults import build_default_agent_config, build_default_model_runtime, build_default_observability_runtime, build_default_tool_runtime
from agent_forge.runtime.schemas import AgentConfig, AgentResult, AgentRunRequest, build_generated_session_id


class AgentRuntime:
    """统一串联 Safety、Memory、Retrieval、Tool、Model 与 Engine 的编排器。"""

    def __init__(
        self,
        *,
        config: AgentConfig | None = None,
        model_name: str | None = None,
        engine_loop: EngineLoop | None = None,
        model_runtime: ModelRuntime | None = None,
        safety_runtime: SafetyRuntime | None = None,
        tool_runtime: ToolRuntime | None = None,
        context_runtime: ContextEngineeringRuntime | None = None,
        retrieval_runtime: RetrievalRuntime | None = None,
        memory_runtime: Any | None = None,
        evaluator_runtime: EvaluatorRuntime | None = None,
        observability_runtime: ObservabilityRuntime | None = None,
    ) -> None:
        """初始化 `AgentRuntime`。"""

        self.config = config or build_default_agent_config()
        self.observability_runtime = observability_runtime or build_default_observability_runtime()
        self.safety_runtime = safety_runtime or SafetyRuntime()
        self.tool_runtime = tool_runtime or build_default_tool_runtime(
            safety_runtime=self.safety_runtime,
            observability_runtime=self.observability_runtime,
        )
        self.context_runtime = context_runtime or ContextEngineeringRuntime()
        self.model_runtime = model_runtime or build_default_model_runtime()
        self.model_name = model_name or self.config.default_model
        self.engine_loop = engine_loop or EngineLoop(
            limits=EngineLimits(),
            event_listener=self.observability_runtime.engine_event_listener,
        )
        self.retrieval_runtime = retrieval_runtime
        self.memory_runtime = memory_runtime
        self.evaluator_runtime = evaluator_runtime

    async def arun(self, request: AgentRunRequest) -> AgentResult:
        """异步执行一条 Agent 主链路。"""

        # 1. 规范化请求，并初始化协议状态。
        normalized = self._normalize_request(request)
        state = self._build_initial_state(normalized)
        self.observability_runtime.set_default_context(trace_id=state.trace_id, run_id=state.run_id)

        # 2. 先做输入安全检查，命中阻断就直接返回统一 blocked 结果。
        input_decision = self.safety_runtime.check_input(
            SafetyCheckRequest(
                stage="input",
                task_input=normalized.task_input,
                trace_id=state.trace_id,
                run_id=state.run_id,
                context=normalized.context,
            )
        )
        if not input_decision.allowed:
            return self._build_blocked_result(normalized=normalized, state=state, decision=input_decision)

        # 3. 读取 memory 并注入上下文，再把用户输入写入对话状态。
        memory_context = self._maybe_read_memory(normalized)
        state.messages.append(AgentMessage(role="user", content=normalized.task_input, metadata={"source": "agent"}))

        async def _runtime_act_fn(current_state: AgentState, step: PlanStep, step_idx: int) -> StepOutcome:
            return await self._act_step(
                request=normalized,
                state=current_state,
                step=step,
                step_idx=step_idx,
                memory_messages=memory_context["messages"],
            )

        # 4. 委托 EngineLoop 驱动 plan -> act -> reflect。
        updated_state = await self.engine_loop.arun(
            state,
            plan_fn=lambda current_state: self._build_plan(request=normalized, state=current_state),
            act_fn=_runtime_act_fn,
            reflect_fn=self._reflect_step,
            context=self._build_run_context(normalized),
        )

        # 5. 汇总最终答案，并执行输出安全审查。
        final_answer = self._build_final_answer(normalized=normalized, state=updated_state)
        output_decision = self.safety_runtime.check_output(
            SafetyCheckRequest(
                stage="output",
                final_answer=final_answer,
                trace_id=updated_state.trace_id,
                run_id=updated_state.run_id,
                context=normalized.context,
            )
        )
        safe_answer = apply_output_safety(final_answer, output_decision)
        updated_state.final_answer = safe_answer

        # 6. 在安全输出基础上做评测和 memory 写回。
        evaluation = self._evaluate_if_needed(normalized=normalized, state=updated_state)
        memory_write = self._maybe_write_memory(normalized=normalized, state=updated_state)

        # 7. 收口成统一 `AgentResult`。
        return self._build_success_result(
            normalized=normalized,
            state=updated_state,
            final_answer=safe_answer,
            input_decision=input_decision,
            output_decision=output_decision,
            evaluation=evaluation,
            memory_read=memory_context,
            memory_write=memory_write,
        )

    def run(self, request: AgentRunRequest) -> AgentResult:
        """同步包装器。"""

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(request))
        raise RuntimeError("检测到运行中的事件循环，请改用 `await AgentRuntime.arun(...)`。")

    def _normalize_request(self, request: AgentRunRequest) -> AgentRunRequest:
        session_id = request.session_id or build_generated_session_id(self.config.session_id_prefix)
        principal = request.principal or self.config.default_principal
        evaluate = self.config.enable_evaluator_by_default if request.evaluate is None else request.evaluate
        return request.model_copy(
            update={
                "session_id": session_id,
                "principal": principal,
                "evaluate": evaluate,
                "context": dict(request.context),
                "metadata": dict(request.metadata),
            }
        )

    def _build_initial_state(self, request: AgentRunRequest) -> AgentState:
        state = build_initial_state(request.session_id or build_generated_session_id(self.config.session_id_prefix))
        if request.trace_id:
            state.trace_id = request.trace_id
        return state

    def _build_run_context(self, request: AgentRunRequest) -> RunContext:
        return RunContext(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            config_version=self.config.config_version,
            model_version=self.model_name,
            tool_version=self.config.tool_version,
            policy_version=self.config.policy_version,
        )

    def _build_plan(self, request: AgentRunRequest, state: AgentState) -> ExecutionPlan:
        _ = state
        return ExecutionPlan(
            global_task=request.task_input,
            success_criteria=["完成用户任务", "保留 trace/session 信息", "返回结构化最终答案"],
            constraints=["遵守安全策略", "如有工具必须经 ToolRuntime 执行", "输出必须经过输出安全审查"],
            metadata={"runtime": "agent_runtime"},
            steps=[PlanStep(key="answer_user_task", name="answer-user-task", kind="generate_answer", payload={"task_input": request.task_input})],
        )

    async def _act_step(
        self,
        *,
        request: AgentRunRequest,
        state: AgentState,
        step: PlanStep,
        step_idx: int,
        memory_messages: list[AgentMessage],
    ) -> StepOutcome:
        _ = step_idx
        if step.kind != "generate_answer":
            return StepOutcome(status="error", output={}, error=ErrorInfo(error_code="UNKNOWN_STEP_KIND", error_message=f"未知 step.kind: {step.kind}", retryable=False))

        try:
            retrieval_result = self._maybe_retrieve(request)
            bundle = self.context_runtime.build_bundle(
                system_prompt=self._build_system_prompt(request),
                developer_prompt=self._build_developer_prompt(request),
                messages=[*memory_messages, *state.messages],
                citations=retrieval_result["citations"],
                tools=self._build_tool_definitions(),
            )
            response = await self._call_model(self._build_model_request(request=request, state=state, bundle=bundle, allow_tools=True))
            tool_phase = await self._run_tool_phase(request=request, state=state, response=response)
            if tool_phase["error"] is not None:
                return StepOutcome(status="error", output={}, error=tool_phase["error"])

            final_response = response
            if tool_phase["used_tools"]:
                final_bundle = self.context_runtime.build_bundle(
                    system_prompt=self._build_system_prompt(request),
                    developer_prompt=self._build_developer_prompt(request),
                    messages=[*memory_messages, *state.messages],
                    citations=retrieval_result["citations"],
                )
                final_response = await self._call_model(
                    self._build_model_request(request=request, state=state, bundle=final_bundle, allow_tools=False)
                )

            payload = self._extract_response_payload(final_response)
            references = self._merge_references(payload.get("references") or [], retrieval_result["references"], tool_phase["references"])
            summary = str(payload.get("summary") or "模型未返回摘要。")
            output = payload.get("output") or {}
            if not isinstance(output, dict):
                output = {"raw": output}

            state.messages.append(
                AgentMessage(
                    role="assistant",
                    content=summary,
                    metadata={
                        "agent_output": output,
                        "references": references,
                        "model_stats": final_response.stats.model_dump(),
                    },
                )
            )
            state.events.append(
                self._build_state_update_event(
                    state=state,
                    step_id=f"agent_step_{step.key}",
                    payload={
                        "phase": "agent_runtime_model_response",
                        "step_key": step.key,
                        "step_name": step.name,
                        "references": references,
                        "used_tools": tool_phase["used_tools"],
                    },
                )
            )
            return StepOutcome(status="ok", output={"summary": summary, "output": output, "references": references})
        except Exception as exc:  # noqa: BLE001
            return StepOutcome(status="error", output={}, error=ErrorInfo(error_code="AGENT_STEP_FAILED", error_message=str(exc), retryable=False))

    def _reflect_step(self, state: AgentState, step: PlanStep, step_idx: int, outcome: StepOutcome) -> ReflectDecision:
        _ = state
        _ = step
        _ = step_idx
        if outcome.status == "ok":
            return ReflectDecision(action="continue", reason="当前 step 已成功完成。")
        if outcome.error and outcome.error.retryable:
            return ReflectDecision(action="retry", reason="step 失败但可重试。")
        return ReflectDecision(action="abort", reason="step 失败且不可重试。")

    def _build_model_request(self, *, request: AgentRunRequest, state: AgentState, bundle: Any, allow_tools: bool) -> ModelRequest:
        _ = state
        return ModelRequest(
            messages=bundle.messages,
            system_prompt=bundle.system_prompt,
            model=self.model_name,
            response_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "output": {"type": "object"},
                    "references": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["summary", "output"],
            },
            tools=bundle.tools if allow_tools and bundle.tools else None,
            request_id=f"agent_run_{request.session_id}_{'tools' if allow_tools else 'final'}",
        )

    def _build_system_prompt(self, request: AgentRunRequest) -> str:
        _ = request
        return "你是一个注重结构化输出、可追踪引用和安全边界的 Agent。"

    def _build_developer_prompt(self, request: AgentRunRequest) -> str | None:
        _ = request
        return "请优先返回结构化 JSON；如使用工具，先根据工具结果再给最终答案。"

    def _build_final_answer(self, *, normalized: AgentRunRequest, state: AgentState) -> FinalAnswer:
        assistant_messages = [message for message in state.messages if message.role == "assistant"]
        latest = assistant_messages[-1] if assistant_messages else None
        if latest is None:
            return FinalAnswer(status="failed", summary="Agent 未能产出最终 assistant 消息。", output={"task_input": normalized.task_input}, references=[])

        answer_output = latest.metadata.get("agent_output", {}) if isinstance(latest.metadata, dict) else {}
        references = latest.metadata.get("references", []) if isinstance(latest.metadata, dict) else []
        if not isinstance(answer_output, dict):
            answer_output = {"raw": answer_output}
        if not isinstance(references, list):
            references = []
        return FinalAnswer(
            status="success",
            summary=latest.content,
            output=answer_output,
            artifacts=[{"type": "agent_message", "name": "default_answer"}],
            references=[str(item) for item in references],
        )

    def _evaluate_if_needed(self, *, normalized: AgentRunRequest, state: AgentState) -> dict[str, Any] | None:
        if not normalized.evaluate or self.evaluator_runtime is None or state.final_answer is None:
            return None
        result = self.evaluator_runtime.evaluate(
            EvaluationRequest(final_answer=state.final_answer, events=state.events, trace_id=state.trace_id, run_id=state.run_id)
        )
        return result.model_dump()

    def _maybe_retrieve(self, request: AgentRunRequest) -> dict[str, list[Any]]:
        if self.retrieval_runtime is None:
            return {"citations": [], "references": []}
        retrieval_query = request.context.get("retrieval_query")
        if not isinstance(retrieval_query, str) or not retrieval_query.strip():
            return {"citations": [], "references": []}
        result = self.retrieval_runtime.search(RetrievalQuery(query_text=retrieval_query.strip()))
        citations = [
            CitationItem(
                source_id=item.document_id,
                title=item.title or item.document_id,
                url=item.source_uri or f"retrieval://{item.document_id}",
                snippet=item.snippet,
                score=item.score,
            )
            for item in result.citations
        ]
        return {"citations": citations, "references": [f"retrieval:{item.document_id}" for item in result.citations]}

    def _maybe_read_memory(self, request: AgentRunRequest) -> dict[str, Any]:
        # 1. 未配置 memory 时，直接返回空结果。
        if self.memory_runtime is None:
            return {"messages": [], "read_count": 0, "enabled": False}
        # 2. 缺少租户或用户身份时不启用 memory，避免跨用户污染。
        if not request.tenant_id or not request.user_id:
            return {"messages": [], "read_count": 0, "enabled": False}
        # 3. 读取 memory，并转换成可注入模型上下文的消息。
        memory_query = request.context.get("memory_query") or request.task_input
        top_k = request.context.get("memory_top_k", 5)
        if not isinstance(top_k, int) or top_k < 1:
            top_k = 5
        result = self.memory_runtime.read(
            MemoryReadQuery(
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                session_id=request.session_id,
                scope=None,
                top_k=top_k,
                query_text=str(memory_query),
            )
        )
        messages = to_context_messages(result)
        return {"messages": messages, "read_count": len(result.records), "enabled": True, "read_trace": result.read_trace}

    def _maybe_write_memory(self, *, normalized: AgentRunRequest, state: AgentState) -> dict[str, Any]:
        # 1. 未配置 memory、缺少隔离键，或 final_answer 失败时都跳过写回。
        if self.memory_runtime is None or state.final_answer is None:
            return {"write_count": 0, "enabled": False}
        if not normalized.tenant_id or not normalized.user_id:
            return {"write_count": 0, "enabled": False}
        if state.final_answer.status == "failed":
            return {"write_count": 0, "enabled": False, "skipped_reason": "final_answer_failed"}

        # 2. 先写 finish，总结最终答案；如果存在成功工具结果，再补写 fact。
        finish_result = self.memory_runtime.write(
            MemoryWriteRequest(
                tenant_id=normalized.tenant_id,
                user_id=normalized.user_id,
                session_id=normalized.session_id,
                trigger="finish",
                agent_state=state,
                final_answer=state.final_answer,
                messages=state.messages,
                tool_results=state.tool_results,
                metadata=dict(normalized.metadata),
                trace_id=state.trace_id,
                run_id=state.run_id,
            )
        )
        finish_written_count = self._memory_write_total(finish_result)
        fact_written_count = 0
        successful_tool_results = [item for item in state.tool_results if item.status == "ok"]
        if successful_tool_results:
            fact_result = self.memory_runtime.write(
                MemoryWriteRequest(
                    tenant_id=normalized.tenant_id,
                    user_id=normalized.user_id,
                    session_id=normalized.session_id,
                    trigger="fact",
                    agent_state=state,
                    final_answer=state.final_answer,
                    messages=state.messages,
                    tool_results=successful_tool_results,
                    metadata=dict(normalized.metadata),
                    trace_id=state.trace_id,
                    run_id=state.run_id,
                )
            )
            fact_written_count = self._memory_write_total(fact_result)
        return {
            "enabled": True,
            "write_count": finish_written_count + fact_written_count,
            "finish_write_count": finish_written_count,
            "fact_write_count": fact_written_count,
        }

    async def _call_model(self, request: ModelRequest) -> ModelResponse:
        return await asyncio.to_thread(self.model_runtime.generate, request)

    async def _run_tool_phase(self, *, request: AgentRunRequest, state: AgentState, response: ModelResponse) -> dict[str, Any]:
        if not response.tool_calls:
            return {"used_tools": False, "references": [], "error": None}

        references: list[str] = []
        for raw_call in response.tool_calls:
            tool_call = self._normalize_tool_call(request=request, state=state, tool_call=raw_call)
            state.tool_calls.append(tool_call)
            state.events.append(self._build_tool_call_event(state=state, tool_call=tool_call))

            result = await self.tool_runtime.execute_async(tool_call, principal=request.principal, capabilities=request.capabilities)
            state.tool_results.append(result)
            state.events.append(self._build_tool_result_event(state=state, tool_call=tool_call, result=result))
            state.messages.append(self._build_tool_message(tool_call=tool_call, result=result))
            references.append(f"tool:{tool_call.tool_name}:{tool_call.tool_call_id}")
            if result.status != "ok":
                error = result.error or ErrorInfo(
                    error_code="AGENT_TOOL_FAILED",
                    error_message=f"工具执行失败: {tool_call.tool_name}",
                    retryable=False,
                )
                return {"used_tools": True, "references": references, "error": error}
        return {"used_tools": True, "references": references, "error": None}

    def _build_tool_definitions(self) -> list[dict[str, Any]]:
        return [spec.model_dump() for spec in self.tool_runtime.list_tool_specs()]

    def _extract_response_payload(self, response: ModelResponse) -> dict[str, Any]:
        if response.parsed_output is not None:
            return dict(response.parsed_output)
        content = response.content.strip()
        if not content:
            return {}
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
        if parsed is not None:
            return {"summary": str(parsed), "output": {"raw": parsed}}
        return {"summary": content, "output": {"raw_text": content}}

    def _normalize_tool_call(self, *, request: AgentRunRequest, state: AgentState, tool_call: ToolCall) -> ToolCall:
        base_tool_call_id = tool_call.tool_call_id or f"tool_call_{uuid4().hex}"
        tool_call_id = f"{state.run_id}:{base_tool_call_id}"
        return tool_call.model_copy(update={"tool_call_id": tool_call_id, "principal": request.principal or self.config.default_principal})

    def _memory_write_total(self, result: Any) -> int:
        structured_count = int(getattr(result, "structured_written_count", 0) or 0)
        vector_count = int(getattr(result, "vector_written_count", 0) or 0)
        if structured_count or vector_count:
            return structured_count + vector_count
        return len(getattr(result, "records", []) or [])

    def _build_tool_message(self, *, tool_call: ToolCall, result: ToolResult) -> AgentMessage:
        if result.status == "ok":
            content = f"tool_result[{tool_call.tool_name}]: {result.output}"
        else:
            content = f"tool_error[{tool_call.tool_name}]: {result.error.error_message if result.error else 'unknown error'}"
        return AgentMessage(
            role="tool",
            content=content,
            metadata={
                "tool_call_id": tool_call.tool_call_id,
                "tool_name": tool_call.tool_name,
                "tool_status": result.status,
                "tool_output": result.output,
            },
        )

    def _merge_references(self, *groups: list[Any]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for group in groups:
            for item in group:
                normalized = str(item)
                if normalized in seen:
                    continue
                seen.add(normalized)
                merged.append(normalized)
        return merged

    def _build_blocked_result(self, *, normalized: AgentRunRequest, state: AgentState, decision: Any) -> AgentResult:
        blocked_reason = decision.reason or "输入被安全策略阻断。"
        error = ErrorInfo(error_code="AGENT_INPUT_BLOCKED", error_message=blocked_reason, retryable=False)
        return AgentResult(
            status="blocked",
            summary=blocked_reason,
            output={"message": blocked_reason, "safety_action": decision.action},
            session_id=state.session_id,
            trace_id=state.trace_id,
            safety={"input": decision.model_dump()},
            error=error,
            metadata={"principal": normalized.principal, "blocked_stage": "input"},
        )

    def _build_success_result(
        self,
        *,
        normalized: AgentRunRequest,
        state: AgentState,
        final_answer: FinalAnswer,
        input_decision: Any,
        output_decision: Any,
        evaluation: dict[str, Any] | None,
        memory_read: dict[str, Any] | None = None,
        memory_write: dict[str, Any] | None = None,
    ) -> AgentResult:
        status = "success"
        if final_answer.status == "partial":
            status = "partial"
        elif final_answer.status == "failed":
            status = "failed"
        memory_read = memory_read or {}
        memory_write = memory_write or {}
        terminal_error = self._extract_terminal_error(state) if status == "failed" else None
        return AgentResult(
            status=status,
            summary=final_answer.summary,
            output=final_answer.output,
            session_id=state.session_id,
            trace_id=state.trace_id,
            references=final_answer.references,
            safety={"input": input_decision.model_dump(), "output": output_decision.model_dump()},
            error=terminal_error,
            final_answer=final_answer,
            evaluation=evaluation,
            metadata={
                "principal": normalized.principal,
                "capabilities": sorted(normalized.capabilities or []),
                "event_count": len(state.events),
                "tool_records": len(state.tool_results),
                "memory_read_count": int(memory_read.get("read_count", 0)),
                "memory_write_count": int(memory_write.get("write_count", 0)),
            },
        )

    def _extract_terminal_error(self, state: AgentState) -> ErrorInfo | None:
        for event in reversed(state.events):
            if event.error is not None:
                return event.error
        return None

    def _build_state_update_event(self, *, state: AgentState, step_id: str, payload: dict[str, Any]) -> ExecutionEvent:
        return ExecutionEvent(trace_id=state.trace_id, run_id=state.run_id, step_id=step_id, event_type="state_update", payload=payload)

    def _build_tool_call_event(self, *, state: AgentState, tool_call: ToolCall) -> ExecutionEvent:
        return ExecutionEvent(
            trace_id=state.trace_id,
            run_id=state.run_id,
            step_id=tool_call.tool_call_id,
            event_type="tool_call",
            payload={"tool_name": tool_call.tool_name, "args": tool_call.args, "principal": tool_call.principal},
        )

    def _build_tool_result_event(self, *, state: AgentState, tool_call: ToolCall, result: ToolResult) -> ExecutionEvent:
        return ExecutionEvent(
            trace_id=state.trace_id,
            run_id=state.run_id,
            step_id=tool_call.tool_call_id,
            event_type="tool_result",
            payload={"tool_name": tool_call.tool_name, "output": result.output, "status": result.status},
            error=result.error,
        )


def build_default_agent_runtime(*, config: AgentConfig | None = None) -> AgentRuntime:
    return AgentRuntime(config=config)
