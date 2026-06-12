# 2026-06-12 多论文对比 MVP

## 背景

Phase 1 已经完成单篇论文从上传到 PaperCard/QA 的闭环。Phase 2 第一块是多论文对比：基于已有 PaperCard 对 GNN 复现关心的维度做横向比较。

## 完成内容

- 新增 `PaperComparisonRequest`、`PaperComparisonRow`、`PaperComparisonResponse`。
- 新增 `PaperComparisonService`。
- 新增 `POST /api/v1/comparisons`。
- 对比维度支持：
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
  - `missing_implementation_details`
  - `reproduction_difficulty`
- 每个 row 保留原 PaperCard 的 `CitedValue` 和 citations。
- 顶层 `citations` 会聚合去重，便于 UI 或后续报告展示。

## 当前策略

- Comparison 只读取已存在的 `data/cards/{paper_id}.json`。
- 不隐式触发 parse、chunk 或 PaperCard 生成。
- 不支持的 dimensions 会被忽略。
- 若所有 dimensions 无效，则使用默认对比维度。
- Summary 当前为 deterministic 规则生成，不调用 LLM。

## 验证

- 新增 comparison service 单测。
- 扩展 FastAPI 集成测试，覆盖两个 paper 的 PaperCard 生成和 `/comparisons` 调用。

## 下一步

- 在 Streamlit UI 中增加多论文选择和 comparison table 展示。
- 之后进入复现 checklist。
