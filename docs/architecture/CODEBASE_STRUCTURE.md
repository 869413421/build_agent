# Codebase Structure（agent_forge）

## 目标

本文件定义仓库目录与依赖边界，作为跨会话单一事实源。

## 目录总览

1. `src/agent_forge/apps`：交付入口层（CLI/API）。
2. `src/agent_forge/components`：10 组件主干实现。
3. `src/agent_forge/support`：横切辅助（配置、日志、通用错误/类型）。
4. `src/agent_forge/contracts`：对外稳定导出面。
5. `tests/unit|integration|e2e`：分层测试。

## 分层规则

1. 每个组件内部按 `domain/application/infrastructure` 划分职责。
2. `domain` 禁止依赖外部 SDK/网络/文件 IO。
3. `application` 只编排流程，不直接耦合传输协议细节。
4. `infrastructure` 负责外部系统适配（如 OpenAI/DeepSeek）。

## 依赖方向

1. `apps -> components -> support`。
2. 组件间通过组件 `__init__.py` 公开接口通信。
3. 禁止跨组件引用对方 `infrastructure/*` 私有实现。

## 命名规范

1. Python 包名：`agent_forge`。
2. 分发名：`agent-forge`。
3. CLI 命令：`agent-forge`。

## 测试规范

1. 单元测试放 `tests/unit`，默认最先执行。
2. 集成测试放 `tests/integration`，可依赖多个组件协作。
3. 端到端测试放 `tests/e2e`，覆盖完整调用链。
