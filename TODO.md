# TODO

本文将 Paper2GNNLab-Agent 拆成三个开发阶段。优先完成单篇 GNN 论文从上传到带 citation QA 的闭环，再扩展到多论文复现规划和实验项目骨架。

## Phase 1：单篇论文 MVP

目标：完成单篇 GNN 论文上传、解析、结构化卡片和带引用问答。

### 1. 项目骨架

- [x] 初始化 Python 项目配置。
- [x] 建立 FastAPI app 入口。
- [x] 建立 Streamlit demo 入口。
- [x] 建立 `.env` 配置加载。
- [x] 建立 SQLite metadata repository 抽象。
- [x] 建立本地文件存储路径约定。

### 2. 论文上传与 hash 去重

- [x] 实现 PDF 上传接口。
- [x] 计算 SHA-256 `file_hash`。
- [x] 基于 hash 复用已有 `paper_id`。
- [x] 保存原始 PDF 到 `data/papers/`。
- [x] 记录 paper metadata 和处理状态。

### 3. PDF 解析与文本清洗

- [x] 选择并封装 PDF 解析库。
- [x] 输出 page-level text。
- [x] 识别基础章节信息。
- [x] 清洗页眉页脚、页码、参考文献噪声和重复断行。
- [x] 保留页码、章节和来源位置。

### 4. Chunk 与 citation 持久化

- [x] 设计 chunk 切分策略。
- [x] 生成稳定 `chunk_id`。
- [x] 保存 chunk JSONL 到 `data/chunks/`。
- [x] 写入 chunk metadata 到 SQLite。
- [x] 定义 citation evidence 截取策略。

### 5. GNN-specific Paper Card

- [x] 实现 Pydantic schema。
- [x] 实现规则版结构化抽取器，后续再接 LLM prompt。
- [x] 抽取 `task_type`、`graph_type`、`datasets`、`node_types`、`edge_types`。
- [x] 抽取 `model_modules`、`losses`、`attacks`、`defenses`。
- [x] 抽取 `metrics`、`baselines`、`main_results`。
- [x] 评估 `reproduction_difficulty`。
- [x] 输出 `missing_implementation_details`。
- [x] 保证关键字段带 citations。
- [x] 设计并接入可选 LLM 结构化抽取 prompt，未配置模型时回退规则版。

### 6. 单篇论文 QA

- [x] 实现单篇 chunk 检索。
- [x] 实现 extractive QA 生成策略。
- [x] 接入可选 LLM answer composer，未配置模型时自动回退 extractive QA。
- [x] 回答中返回 citations。
- [x] evidence 不足时返回 unsupported claims。
- [x] 增加 QA API。
- [x] 增加 Streamlit QA UI。

### 8. Streamlit MVP UI

- [x] 支持 PDF 上传和 hash 复用反馈。
- [x] 支持选择最近处理的论文。
- [x] 支持触发 parse/clean、chunk、PaperCard。
- [x] 展示 artifact readiness 和处理状态。
- [x] 展示 GNN PaperCard 与 citations。
- [x] 支持单篇 QA 输入和 citation evidence 展示。

### 7. 验证

- [x] 准备最小样例 PDF 生成器。
- [x] 增加上传和 hash 复用测试。
- [x] 增加 chunk/citation schema 测试。
- [x] 增加 paper card 字段完整性测试。
- [x] 增加 QA citation 行为测试。
- [x] 增加端到端 smoke 脚本。

## Phase 2：多论文分析与复现规划

目标：在单篇结构化结果稳定后，支持多论文对比和复现计划生成。

### 1. 多论文对比

- [x] 基于 PaperCard 设计 comparison service。
- [x] 支持按 `task_type`、`graph_type`、`datasets`、`metrics` 对比。
- [x] 支持按 `attacks`、`defenses`、`baselines` 对比。
- [x] 输出横向对比表和 summary。
- [x] 保留每个结论的 citations。
- [x] 在 Streamlit UI 中展示多论文横向对比。

### 2. 复现 checklist

- [x] 基于 PaperCard 生成 ReproductionPlan。
- [x] 拆分环境、数据、模型、训练、评估、消融实验。
- [x] 标记 missing details 和人工确认项。
- [x] 为高风险复现步骤给出原因和 citations。
- [x] 在 Streamlit UI 中展示 ReproductionPlan。

### 3. method_spec.yaml

- [x] 定义 MethodSpec 到 YAML 的导出规则。
- [x] 从 PaperCard 和 ReproductionPlan 生成 MethodSpec。
- [x] 保留数据集、模型模块、攻击/防御、训练和评估字段。
- [x] 将不确定信息写入 `missing_details`。
- [x] 增加 `method_spec.yaml` 下载接口。
- [x] 在 Streamlit UI 中预览和下载 `method_spec.yaml`。

### 4. PaperCard 质量评估与审查

- [x] 增加 PaperCard completeness、citation coverage 和 suspicious values 质量报告。
- [x] 支持可选 golden JSON 对比并输出字段级 precision/recall。
- [x] 在 Streamlit UI 中展示 PaperCard 质量面板。
- [x] 在 Streamlit UI 中支持人工编辑并保存 reviewed PaperCard。
- [x] 后续 comparison、reproduction plan 和 method_spec 优先使用 reviewed PaperCard。

## Phase 3：实验落地辅助

目标：基于已审查的 MethodSpec 生成可读、可修改、可运行前检查的实验骨架。

### 1. 模板驱动代码骨架生成

- [ ] 设计异构图/GNN 实验项目模板。
- [ ] 基于 MethodSpec 填充 configs、models、scripts、attacks。
- [ ] 生成 `README_reproduce.md`。
- [ ] 生成项目内 `TODO.md`，列出必须人工确认项。
- [ ] 禁止直接生成不可审查的完整复现代码。

### 2. GraphRAG 联动

- [ ] 设计可选 GraphRAG adapter。
- [ ] 支持调用外部 GraphRAG evidence search。
- [ ] 保持本项目与 GraphRAG 松耦合。
- [ ] 对 GraphRAG 返回证据统一转换为 Citation。

### 3. 实验日志分析

- [ ] 定义实验日志输入格式。
- [ ] 提取训练曲线、错误栈、指标表。
- [ ] 对比论文报告结果和本地实验结果。
- [ ] 生成下一步 debug 建议。

## 当前阶段限制

- [x] 不实现复杂多 Agent 系统。
- [x] 不实现自动完整论文复现。
- [x] 不从论文文本直接生成不可控完整代码。
- [x] 不在 Phase 1 强耦合既有 GraphRAG 项目。
