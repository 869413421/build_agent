"""基于 ModelRuntime 的记忆抽取器。"""

from __future__ import annotations

from typing import Any

from agent_forge.components.memory.domain import (
    ExtractedMemoryItem,
    MemoryModelRuntime,
    MemoryWriteRequest,
)
from agent_forge.components.model_runtime import ModelRequest
from agent_forge.components.protocol import AgentMessage


class MemoryExtractor:
    """通过 ModelRuntime 执行结构化记忆抽取。"""

    def __init__(self, model_runtime: MemoryModelRuntime, model: str | None = None) -> None:
        """初始化抽取器。

        Args:
            model_runtime: 统一模型运行时。
            model: 可选模型覆盖名。

        Returns:
            None.
        """

        self._model_runtime = model_runtime
        self._model = model

    def extract(self, request: MemoryWriteRequest) -> list[ExtractedMemoryItem]:
        """按触发器执行记忆抽取。

        Args:
            request: 写入请求。

        Returns:
            list[ExtractedMemoryItem]: 标准化记忆项。
        """

        # 1. 允许上游直接提供抽取结果，用于测试或人工写入路径。
        if request.extracted_items:
            return [item.model_copy(deep=True) for item in request.extracted_items]

        # 2. 根据 trigger 构造抽取输入，保持 finish/fact/preference 语义分离。
        if request.trigger == "finish":
            return self.extract_from_finish(request)
        if request.trigger == "fact":
            return self.extract_facts(request)
        return self.extract_preferences(request)

    def extract_from_finish(self, request: MemoryWriteRequest) -> list[ExtractedMemoryItem]:
        """从最终答案抽取摘要记忆。

        Args:
            request: 写入请求。

        Returns:
            list[ExtractedMemoryItem]: 摘要记忆。
        """

        return self._extract_with_schema(
            request=request,
            task_name="finish_summary",
            instruction=(
                "你是 Memory 抽取器。请从最终答案中提炼会话摘要和长期摘要候选。"
                "只输出结构化 JSON，不要解释。"
            ),
            messages=self._build_finish_messages(request),
        )

    def extract_facts(self, request: MemoryWriteRequest) -> list[ExtractedMemoryItem]:
        """抽取事实类记忆。

        Args:
            request: 写入请求。

        Returns:
            list[ExtractedMemoryItem]: 事实记忆。
        """

        return self._extract_with_schema(
            request=request,
            task_name="facts",
            instruction=(
                "你是 Memory 抽取器。请从消息、最终答案和工具结果中抽取可长期复用的事实。"
                "不要编造，只保留明确事实。只输出结构化 JSON。"
            ),
            messages=self._build_fact_messages(request),
        )

    def extract_preferences(self, request: MemoryWriteRequest) -> list[ExtractedMemoryItem]:
        """抽取偏好类记忆。

        Args:
            request: 写入请求。

        Returns:
            list[ExtractedMemoryItem]: 偏好记忆。
        """

        return self._extract_with_schema(
            request=request,
            task_name="preferences",
            instruction=(
                "你是 Memory 抽取器。请从用户消息中抽取稳定偏好，如语言、输出格式、固定要求。"
                "不要抽取一次性临时请求。只输出结构化 JSON。"
            ),
            messages=self._build_preference_messages(request),
        )

    def _extract_with_schema(
        self,
        *,
        request: MemoryWriteRequest,
        task_name: str,
        instruction: str,
        messages: list[AgentMessage],
    ) -> list[ExtractedMemoryItem]:
        """执行一次结构化抽取。

        Args:
            request: 写入请求。
            task_name: 抽取任务名。
            instruction: 系统指令。
            messages: 送入模型的消息。

        Returns:
            list[ExtractedMemoryItem]: 规范化后的记忆项。
        """

        model_request = ModelRequest(
            messages=messages,
            system_prompt=instruction,
            model=self._model,
            temperature=0.0,
            response_schema=_memory_extraction_schema(task_name),
        )
        response = self._model_runtime.generate(model_request)
        raw_items = (response.parsed_output or {}).get("items", [])
        if not isinstance(raw_items, list):
            return []
        output: list[ExtractedMemoryItem] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            output.append(ExtractedMemoryItem.model_validate(item))
        return output

    def _build_finish_messages(self, request: MemoryWriteRequest) -> list[AgentMessage]:
        """构造 finish 抽取消息。

        Args:
            request: 写入请求。

        Returns:
            list[AgentMessage]: 模型输入消息。
        """

        final_answer = request.final_answer or (request.agent_state.final_answer if request.agent_state else None)
        if final_answer is None:
            return [AgentMessage(role="user", content="没有 final_answer，可返回空 items。")]
        return [
            AgentMessage(role="user", content=f"最终摘要: {final_answer.summary}"),
            AgentMessage(role="user", content=f"最终输出: {final_answer.output}"),
        ]

    def _build_fact_messages(self, request: MemoryWriteRequest) -> list[AgentMessage]:
        """构造事实抽取消息。

        Args:
            request: 写入请求。

        Returns:
            list[AgentMessage]: 模型输入消息。
        """

        messages: list[AgentMessage] = []
        for message in request.messages or (request.agent_state.messages if request.agent_state else []):
            messages.append(message.model_copy(deep=True))
        final_answer = request.final_answer or (request.agent_state.final_answer if request.agent_state else None)
        if final_answer is not None:
            messages.append(AgentMessage(role="assistant", content=f"final_answer: {final_answer.output}"))
        for result in request.tool_results or (request.agent_state.tool_results if request.agent_state else []):
            messages.append(AgentMessage(role="tool", content=f"tool_result[{result.tool_call_id}]: {result.output}"))
        if not messages:
            messages.append(AgentMessage(role="user", content="没有可抽取的事实，可返回空 items。"))
        return messages

    def _build_preference_messages(self, request: MemoryWriteRequest) -> list[AgentMessage]:
        """构造偏好抽取消息。

        Args:
            request: 写入请求。

        Returns:
            list[AgentMessage]: 模型输入消息。
        """

        source_messages = request.messages or (request.agent_state.messages if request.agent_state else [])
        user_messages = [item.model_copy(deep=True) for item in source_messages if item.role == "user"]
        if not user_messages:
            return [AgentMessage(role="user", content="没有用户消息，可返回空 items。")]
        return user_messages


def _memory_extraction_schema(task_name: str) -> dict[str, Any]:
    """返回统一的记忆抽取 schema。

    Args:
        task_name: 抽取任务名。

    Returns:
        dict[str, Any]: JSON schema。
    """

    return {
        "type": "object",
        "title": f"memory_extraction_{task_name}",
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["scope", "category", "record_key", "content"],
                    "properties": {
                        "scope": {"type": "string", "enum": ["session", "long_term"]},
                        "category": {"type": "string", "enum": ["summary", "fact", "preference", "other"]},
                        "record_key": {"type": "string"},
                        "content": {"type": "string"},
                        "summary": {"type": "string"},
                        "source_type": {"type": ["string", "null"], "enum": ["final_answer", "agent_message", "tool_result", "retrieval_citation", None]},
                        "source_id": {"type": ["string", "null"]},
                        "source_excerpt": {"type": "string"},
                        "expires_at": {"type": ["string", "null"]},
                        "metadata": {"type": "object"},
                    },
                },
            }
        },
    }
