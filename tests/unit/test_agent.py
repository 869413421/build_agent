"""Tests for the user-facing Agent facade."""

from __future__ import annotations

import asyncio

from agent_forge import Agent, AgentResult, AgentRunRequest
from agent_forge.runtime.runtime import AgentRuntime


def test_agent_should_run_with_minimal_code() -> None:
    result = asyncio.run(Agent().arun("帮我梳理一下当前任务的下一步"))

    assert result.status == "success"
    assert result.summary
    assert "answer" in result.output
    assert result.trace_id.startswith("trace_")
    assert result.session_id.startswith("session_")


def test_agent_should_support_sync_wrapper_for_script_callers() -> None:
    result = Agent().run("帮我给这个需求做一个最小实现建议")

    assert result.status == "success"
    assert result.output["task_input"] == "帮我给这个需求做一个最小实现建议"


def test_agent_subclass_should_override_context_and_after_run() -> None:
    class DemoAgent(Agent):
        def _get_context(self, task_input: str, **options: object) -> dict[str, object]:
            return {"domain": "labor", "original": task_input, **dict(options.get("context") or {})}

        def _after_run(self, request: AgentRunRequest, result: AgentResult) -> AgentResult:
            result.metadata["domain"] = request.context["domain"]
            result.summary = f"[demo] {result.summary}"
            return result

    result = asyncio.run(DemoAgent().arun("帮我总结一下争议焦点"))

    assert result.summary.startswith("[demo] ")
    assert result.metadata["domain"] == "labor"


def test_agent_should_allow_runtime_injection() -> None:
    class FakeRuntime(AgentRuntime):
        async def arun(self, request: AgentRunRequest) -> AgentResult:  # type: ignore[override]
            return AgentResult(
                status="success",
                summary=f"fake:{request.task_input}",
                output={"message": "from-fake-runtime"},
                session_id=request.session_id or "session_fake",
                trace_id=request.trace_id or "trace_fake",
            )

    result = asyncio.run(Agent(runtime=FakeRuntime()).arun("test"))

    assert result.summary == "fake:test"
    assert result.output["message"] == "from-fake-runtime"


def test_agent_subclass_should_override_capabilities() -> None:
    class CapAgent(Agent):
        def _get_capabilities(self, task_input: str, **options: object) -> set[str] | None:
            _ = task_input
            _ = options
            return {"safety:tool:high_risk"}

        def _after_run(self, request: AgentRunRequest, result: AgentResult) -> AgentResult:
            result.metadata["capabilities_seen"] = sorted(request.capabilities or [])
            return result

    result = asyncio.run(CapAgent().arun("帮我确认这个任务是否需要高风险工具"))

    assert result.metadata["capabilities_seen"] == ["safety:tool:high_risk"]
