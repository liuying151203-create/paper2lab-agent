# 2026-06-12 method_spec.yaml

## 背景

Phase 2 已经完成多论文对比和 ReproductionPlan。`method_spec.yaml` 是从论文阅读结果走向实验项目骨架的中间层：它不直接生成代码，而是把 GNN 复现实验需要的任务、数据、模型、攻击/防御、训练、评估和缺失细节整理成稳定结构。

## 本次实现

- 新增 `MethodSpecService`。
- 从 `PaperCard` 生成 `MethodSpec`。
- 若已存在 `ReproductionPlan`，吸收其中的数据准备、消融、人工确认和 blocked 项。
- 新增 `POST /api/v1/papers/{paper_id}/method-spec`。
- 新增 `GET /api/v1/papers/{paper_id}/method-spec.yaml`。
- 输出：
  - `data/specs/{paper_id}.yaml`
  - `data/specs/{paper_id}.method_spec.json`
- 在 Streamlit UI 中支持生成、预览和下载 `method_spec.yaml`。

## 设计原则

- 不隐式触发 PDF 解析、chunk、PaperCard 或 ReproductionPlan 生成。
- `method_spec.yaml` 只依赖已审核的结构化 artifacts。
- 不在 Phase 2 生成实验代码，避免从论文文本直接生成不可控代码。
- 当前不新增 YAML 依赖，使用内部 deterministic YAML emitter 覆盖本项目 schema。
- JSON sidecar 仅用于服务端复用，用户面向的实验规格文件仍是 YAML。

## 验证

- 新增 `tests/unit/test_method_spec.py`。
- 扩展 FastAPI 集成测试，覆盖 method spec 生成、复用和 YAML 下载。

## Phase 2 状态

Phase 2 的核心功能已经完成：

- 多论文对比
- 复现 checklist
- `method_spec.yaml`
- Streamlit MVP 中的对比、checklist、YAML 预览和下载

接下来按计划暂停功能开发，先用真实 GNN 论文实际跑一轮效果，再决定 Phase 3 的模板代码骨架生成策略。
