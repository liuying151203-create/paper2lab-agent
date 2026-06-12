# 2026-06-12 复现 Checklist

## 背景

Phase 2 的多论文对比已经完成 service、API 和 Streamlit UI。下一步进入单篇论文复现规划：基于已生成的 GNN PaperCard 生成可执行的 checklist，帮助后续 `method_spec.yaml` 和代码骨架生成之前先明确实验复现缺口。

## 本次实现

- 新增 `ReproductionChecklistService`。
- 基于 `PaperCard` 生成 `ReproductionPlan`。
- checklist 拆分为：
  - environment
  - data_preparation
  - model_implementation
  - attack_or_defense_setup
  - training_pipeline
  - evaluation
  - ablation_studies
  - risks
  - missing_details
- 新增 `POST /api/v1/papers/{paper_id}/reproduction-plan`。
- 输出保存到 `data/specs/{paper_id}.reproduction_plan.json`。
- 支持 `force=false` 复用已生成 plan。

## 设计原则

- 只基于已生成的 PaperCard，不隐式触发 PDF 解析、chunk 或 PaperCard 生成。
- 有论文 evidence 的 checklist item 保留 citations。
- PaperCard 未明确给出的实现细节标记为 `needs_manual_check` 或 `blocked`。
- 不在此阶段自动生成实验代码，也不声称已经完成论文复现。

## 验证

- 新增 `tests/unit/test_reproduction.py`，覆盖 GNN 字段到 checklist 区块的映射。
- 扩展 FastAPI 集成测试，覆盖 reproduction plan 生成与复用。

## 后续

- 将 ReproductionPlan 接入 Streamlit UI。
- 进入 `method_spec.yaml`：把 PaperCard 和 ReproductionPlan 转为更接近代码模板输入的结构化 spec。
