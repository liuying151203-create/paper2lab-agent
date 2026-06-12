# 2026-06-12 Streamlit ReproductionPlan UI

## 背景

复现 checklist service 和 API 已经完成。为了让 Phase 2 的复现规划能在本地 MVP 中直接验证，本次将 ReproductionPlan 接入 Streamlit 单篇论文工作台。

## 本次实现

- 在单篇论文页面新增 `Reproduction checklist` 区块。
- 支持点击生成或复用 `ReproductionPlan`。
- 支持强制重新生成 reproduction plan。
- 展示复现目标、难度、生成时间和 checklist item 总数。
- 按 GNN 复现流程分组展示：
  - Environment
  - Data preparation
  - Model implementation
  - Attack or defense setup
  - Training pipeline
  - Evaluation
  - Ablation studies
  - Risks
  - Missing details
- 每个 checklist item 展示状态、rationale 和 citations。

## 边界

- UI 不隐式生成 PaperCard。
- 如果 PaperCard 尚未生成，生成 ReproductionPlan 时会提示先生成 PaperCard。
- 当前页面只显示本次会话中生成的 ReproductionPlan；后续可以增加显式加载已落盘 plan 的按钮。

## 后续

- 进入 `method_spec.yaml`，把 PaperCard 与 ReproductionPlan 转换成代码模板可消费的结构化实验规格。
