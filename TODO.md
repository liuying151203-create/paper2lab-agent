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
- [ ] 识别基础章节信息。
- [ ] 清洗页眉页脚、页码、参考文献噪声和重复断行。
- [ ] 保留页码、章节和来源位置。

### 4. Chunk 与 citation 持久化

- [ ] 设计 chunk 切分策略。
- [ ] 生成稳定 `chunk_id`。
- [ ] 保存 chunk JSONL 到 `data/chunks/`。
- [ ] 写入 chunk metadata 到 SQLite。
- [ ] 定义 citation evidence 截取策略。

### 5. GNN-specific Paper Card

- [x] 实现 Pydantic schema。
- [ ] 设计结构化抽取 prompt。
- [ ] 抽取 `task_type`、`graph_type`、`datasets`、`node_types`、`edge_types`。
- [ ] 抽取 `model_modules`、`losses`、`attacks`、`defenses`。
- [ ] 抽取 `metrics`、`baselines`、`main_results`。
- [ ] 评估 `reproduction_difficulty`。
- [ ] 输出 `missing_implementation_details`。
- [ ] 保证关键字段带 citations。

### 6. 单篇论文 QA

- [ ] 实现单篇 chunk 检索。
- [ ] 实现 QA prompt。
- [ ] 回答中返回 citations。
- [ ] evidence 不足时返回 unsupported claims。
- [ ] 增加 QA API 和 Streamlit UI。

### 7. 验证

- [ ] 准备最小样例 PDF。
- [ ] 增加上传和 hash 复用测试。
- [ ] 增加 chunk/citation schema 测试。
- [ ] 增加 paper card 字段完整性测试。
- [ ] 增加 QA citation 行为测试。

## Phase 2：多论文分析与复现规划

目标：在单篇结构化结果稳定后，支持多论文对比和复现计划生成。

### 1. 多论文对比

- [ ] 基于 PaperCard 设计 comparison service。
- [ ] 支持按 `task_type`、`graph_type`、`datasets`、`metrics` 对比。
- [ ] 支持按 `attacks`、`defenses`、`baselines` 对比。
- [ ] 输出横向对比表和 summary。
- [ ] 保留每个结论的 citations。

### 2. 复现 checklist

- [ ] 基于 PaperCard 生成 ReproductionPlan。
- [ ] 拆分环境、数据、模型、训练、评估、消融实验。
- [ ] 标记 missing details 和人工确认项。
- [ ] 为高风险复现步骤给出原因和 citations。

### 3. method_spec.yaml

- [ ] 定义 MethodSpec 到 YAML 的导出规则。
- [ ] 从 PaperCard 和 chunks 生成 MethodSpec。
- [ ] 保留数据集、模型模块、攻击/防御、训练和评估字段。
- [ ] 将不确定信息写入 `missing_details`。
- [ ] 增加 `method_spec.yaml` 下载接口。

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

- [ ] 不实现复杂多 Agent 系统。
- [ ] 不实现自动完整论文复现。
- [ ] 不从论文文本直接生成不可控完整代码。
- [ ] 不在 Phase 1 强耦合既有 GraphRAG 项目。
