"""Tests for the minimal AgentApp demo."""

from __future__ import annotations

import asyncio

from examples.agent.agent_app_demo import run_demo


def test_agent_app_demo_should_run_end_to_end() -> None:
    result = asyncio.run(run_demo())

    assert result["agent_name"] == "researcher"
    assert result["status"] == "success"
    assert result["summary"]
    assert str(result["trace_id"]).startswith("trace_")
