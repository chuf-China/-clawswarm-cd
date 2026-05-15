# ClawSwarm-CD — Claude Code Runtime 分支

基于 ClawSwarm（小米官方开源多智能体群聊框架）的二次开发分支。

## 新增特性

- **Claude Code Runtime**：群聊 Agent 具备 Read/Edit/Bash/WebSearch 工具调用
- **DeepSeek 后端对接**：ANTHROPIC_BASE_URL + API_KEY + MODEL 三件套
- **Hermes Agent 双向通信**：MCP协议，全自动协作

## 改造规模

27 文件，+959/-204 行。核心修改：`hermes_dispatch_service.py`、`agent_dialogue_runner.py`、`runtime_target_service.py`。

## 配套系统

Hermes 量化交易系统（163 Python 模块、100 步全自动管线、2007 条 ML 训练样本）与本分支配合使用，实现交易决策 Agent ↔ 编码执行 Agent 全自动协作。

## 原项目

[1Panel-dev/ClawSwarm](https://github.com/1Panel-dev/ClawSwarm) — GPL-3.0
