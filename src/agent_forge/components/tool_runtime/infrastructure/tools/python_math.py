"""安全数学表达式工具。"""

from __future__ import annotations

import ast
import math
from typing import Any

from agent_forge.components.tool_runtime.domain.schemas import ToolRuntimeError, ToolSpec

_SAFE_FUNCTIONS: dict[str, Any] = {
    "abs": abs,
    "round": round,
    "pow": pow,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "ceil": math.ceil,
    "floor": math.floor,
    "log": math.log,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
}
_SAFE_CONSTANTS: dict[str, float] = {"pi": math.pi, "e": math.e}


class PythonMathTool:
    """基于 AST 白名单的数学表达式工具。"""

    @property
    def tool_spec(self) -> ToolSpec:
        """返回适合 `AgentApp` 注册的工具规格。"""

        return ToolSpec(
            name="calculator",
            description="安全执行数学表达式计算。",
            args_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
                "additionalProperties": False,
            },
            side_effect_level="none",
        )

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        """执行数学表达式计算。

        Args:
            args: 工具参数，必须包含 `expression` 字段。

        Returns:
            dict[str, Any]: 包含原表达式与计算结果。

        Raises:
            ToolRuntimeError: 参数非法或表达式执行失败时抛出。
        """

        expression = args.get("expression", "")
        if not isinstance(expression, str) or not expression.strip():
            raise ToolRuntimeError("TOOL_VALIDATION_ERROR", "expression 必须是非空字符串")
        try:
            # 1. 解析阶段：先把输入表达式转换成语法树，拒绝语法错误。
            tree = ast.parse(expression, mode="eval")
            # 2. 校验阶段：遍历 AST，确保只出现白名单节点和函数。
            _validate_ast(tree)
            # 3. 执行阶段：递归求值，不使用 eval/exec，避免代码注入。
            value = _evaluate_node(tree.body)
        except ToolRuntimeError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ToolRuntimeError("TOOL_EXECUTION_ERROR", f"数学表达式执行失败: {exc}") from exc
        return {"expression": expression, "value": value}


def build_python_math_handler(tool: PythonMathTool | None = None):
    """构建可注册到 ToolRuntime 的 handler。

    Args:
        tool: 可选工具实例；为空时创建默认实例。

    Returns:
        Callable[[dict[str, Any]], dict[str, Any]]: 可直接注册的处理函数。
    """

    active_tool = tool or PythonMathTool()
    return active_tool.execute


def _validate_ast(tree: ast.AST) -> None:
    """校验 AST 是否只包含白名单节点。

    Args:
        tree: 已解析的表达式语法树。

    Raises:
        ToolRuntimeError: 检测到危险节点、函数或标识符时抛出。
    """

    allowed_node_types = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.Pow,
        ast.UAdd,
        ast.USub,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed_node_types):
            raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"不允许的表达式节点: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ToolRuntimeError("TOOL_VALIDATION_ERROR", "仅允许直接调用白名单函数")
            if node.func.id not in _SAFE_FUNCTIONS:
                raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"不允许调用函数: {node.func.id}")
            if node.keywords:
                raise ToolRuntimeError("TOOL_VALIDATION_ERROR", "不允许关键字参数")
        if isinstance(node, ast.Name):
            if node.id not in _SAFE_FUNCTIONS and node.id not in _SAFE_CONSTANTS:
                raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"不允许使用标识符: {node.id}")


def _evaluate_node(node: ast.AST) -> float:
    """递归求值 AST 节点。

    Args:
        node: 当前待求值节点。

    Returns:
        float: 节点计算值。

    Raises:
        ToolRuntimeError: 节点类型不支持或值越界时抛出。
    """

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ToolRuntimeError("TOOL_VALIDATION_ERROR", "仅允许数值常量")
        return float(node.value)

    if isinstance(node, ast.Name):
        return float(_SAFE_CONSTANTS[node.id])

    if isinstance(node, ast.UnaryOp):
        operand = _evaluate_node(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise ToolRuntimeError("TOOL_VALIDATION_ERROR", "不支持的一元操作")

    if isinstance(node, ast.BinOp):
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            if abs(right) > 1000:
                raise ToolRuntimeError("TOOL_VALIDATION_ERROR", "指数过大，最大允许绝对值 1000")
            return left**right
        raise ToolRuntimeError("TOOL_VALIDATION_ERROR", "不支持的二元操作")

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ToolRuntimeError("TOOL_VALIDATION_ERROR", "仅支持白名单函数")
        fn = _SAFE_FUNCTIONS[node.func.id]
        call_args = [_evaluate_node(arg) for arg in node.args]
        return float(fn(*call_args))

    raise ToolRuntimeError("TOOL_VALIDATION_ERROR", f"未知表达式节点: {type(node).__name__}")
