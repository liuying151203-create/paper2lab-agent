# 2026-06-12 单篇论文 QA

## 背景

PaperCard 生成链路完成后，Phase 1 进入单篇论文问答。当前目标是先形成可运行、可测试、可追溯 citation 的最小 QA 闭环，不在 MVP 中直接引入复杂 RAG 或外部 LLM 依赖。

## 完成内容

- 新增 `ChunkQAService`。
- 基于单篇论文的 `data/chunks/{paper_id}.jsonl` 做轻量词项检索。
- 按问题词与 chunk 文本重合度排序，返回 top-k evidence。
- 从命中的 chunk 中选择最相关句子作为 `Citation.evidence_text`。
- 新增 `POST /api/v1/papers/{paper_id}/qa`。
- 当没有匹配证据时，返回 `unsupported_claims`。
- QA 不隐式触发 parse、clean 或 chunk，缺少 chunks 时返回 `409`。

## 当前策略

当前实现是 extractive QA：

- 优点：答案完全来自 chunk evidence，行为稳定，测试可控。
- 限制：不会做复杂归纳、跨表格推理或自然语言改写。
- 后续：在同一接口下接入 LLM answer composer，但必须继续使用检索到的 citations 约束回答。

## 验证

- 新增 QA 单元测试，覆盖命中 evidence 和 evidence 不足两种情况。
- 扩展 ingestion service 测试，覆盖 chunk 后问答。
- 扩展 FastAPI 集成测试，覆盖 `POST /qa`。

## 下一步

- 增加 Streamlit MVP UI：
  - PDF 上传。
  - parse/clean/chunk/card 按钮。
  - PaperCard 展示。
  - 单篇 QA 输入框与 citations 展示。
