# 2026-06-12 Streamlit 多论文对比 UI

## 背景

多论文 comparison service 和 API 完成后，需要在本地工作台里直接验证 Phase 2 的横向对比体验。本次将 comparison 接入 Streamlit。

## 完成内容

- Streamlit 主界面新增两个 tab：
  - `Single paper`
  - `Compare papers`
- `Compare papers` 支持：
  - 只列出已生成 PaperCard 的论文。
  - 勾选两篇或更多 paper。
  - 选择 comparison dimensions。
  - 调用 `PaperIngestionService.compare_papers()`。
  - 展示 summary。
  - 展示横向对比表。
  - 展示聚合 citations。

## 当前策略

- UI 不隐式生成 PaperCard；论文必须先在单篇流程中完成 card generation。
- 对比表使用 Streamlit 原生 `dataframe`，不引入 pandas。
- Summary 仍由 deterministic comparison service 生成，不调用 LLM。

## 下一步

- 进入复现 checklist：基于 PaperCard 生成 ReproductionPlan。
