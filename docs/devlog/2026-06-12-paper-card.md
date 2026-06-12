# 2026-06-12 Paper Card 生成

## 背景

Chunk 与 citation 持久化完成后，Phase 1 进入 GNN-specific PaperCard。MVP 目标不是一次接入复杂 LLM 流程，而是先把可运行、可测试、可落盘的结构化卡片链路打通。

## 完成内容

- 新增规则版 `RuleBasedPaperCardExtractor`。
- 从 chunks 中抽取 GNN 垂直字段：
  - `task_type`
  - `graph_type`
  - `datasets`
  - `node_types`
  - `edge_types`
  - `model_modules`
  - `losses`
  - `attacks`
  - `defenses`
  - `metrics`
  - `baselines`
  - `training_setup`
  - `evaluation_protocol`
  - `main_results`
  - `limitations`
- 每个命中的结构化字段尽量绑定原始 chunk citation。
- 生成 `reproduction_difficulty` 与 `missing_implementation_details`。
- 新增 `POST /api/v1/papers/{paper_id}/card`。
- 新增 `GET /api/v1/papers/{paper_id}/card`。
- PaperCard 输出保存到 `data/cards/{paper_id}.json`。
- 生成成功后更新 paper status 为 `card_ready`。

## 当前策略

当前实现为规则/启发式抽取：

- 优点：无外部模型依赖，测试稳定，方便先跑通端到端闭环。
- 限制：复杂方法描述、隐式数据集设置、表格中的结果和细粒度超参仍可能漏抽。
- 后续：在同一服务接口下接入 LLM 结构化抽取 prompt，并保留 citation 校验。

## 验证

- 新增 PaperCard 抽取单元测试。
- 扩展 ingestion service 测试，覆盖 parse -> clean -> chunk -> card。
- 扩展 FastAPI 集成测试，覆盖 POST/GET card。

## 下一步

- 实现单篇论文 QA：
  - 基于 chunks 做轻量检索。
  - 生成带 citations 的回答。
  - evidence 不足时返回 `unsupported_claims`。
