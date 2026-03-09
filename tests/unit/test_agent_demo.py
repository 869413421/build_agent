"""Tests for the minimal Agent demo."""

from __future__ import annotations

import asyncio

from examples.agent.agent_demo import run_demo


def test_agent_demo_should_run_end_to_end() -> None:
    result = asyncio.run(run_demo())

    assert result["status"] == "success"
    assert result["summary"]
    assert isinstance(result["output"], dict)
    assert str(result["trace_id"]).startswith("trace_")
