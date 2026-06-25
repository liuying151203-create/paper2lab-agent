# Paper2GNNLab-Agent 设计文档

## 1. 系统定位

Paper2GNNLab-Agent 是面向图神经网络论文阅读与实验复现规划的科研 Agent。MVP 不做通用论文阅读器，也不直接生成不可控的完整复现代码，而是围绕 GNN 论文中的任务、图结构、数据集、模型模块、攻击/防御、指标和复现缺口建立可追溯的结构化工作流。

核心目标：

- 上传论文后基于 `file_hash` 去重与复用已有解析结果。
- 解析 PDF，清洗低价值文本，并保留页码、章节、chunk_id 等 citation 元数据。
- 生成 GNN-specific paper card。
- 支持单篇论文问答，回答必须带可追溯 citations。
- 为后续多论文对比、复现 checklist、`method_spec.yaml` 和模板代码骨架生成打基础。

## 2. 推荐目录结构

```text
paper2lab-agent/
  AGENTS.md
  README.md
  TODO.md
  docs/
    design.md
    schema.md
    api.md
  src/
    paper2gnnlab_agent/
      api/
      core/
      models/
      parsers/
      services/
      storage/
      ui/
  tests/
    unit/
    integration/
  data/
    papers/
    parsed/
    cleaned/
    chunks/
    cards/
    specs/
    generated_projects/
  templates/
    experiment_project/
```

目录说明：

- `src/paper2gnnlab_agent/api/`：FastAPI 路由、依赖注入和请求/响应模型组合。
- `src/paper2gnnlab_agent/core/`：配置、异常、日志、任务状态、模型客户端抽象。
- `src/paper2gnnlab_agent/models/`：Pydantic schema 和领域对象。
- `src/paper2gnnlab_agent/parsers/`：PDF 解析、章节识别、文本清洗、chunk 切分。
- `src/paper2gnnlab_agent/services/`：上传处理、论文卡片生成、QA、对比、复现计划等业务编排。
- `src/paper2gnnlab_agent/storage/`：SQLite metadata repository 与本地文件存储封装。
- `src/paper2gnnlab_agent/ui/`：Streamlit MVP demo。
- `data/`：本地运行时数据目录，后续应通过 `.gitignore` 避免提交真实论文和生成产物。
- `templates/experiment_project/`：Phase 3 使用的可审查实验项目模板。

## 3. 架构分层

### 3.1 API 层

API 层只负责协议转换、文件上传、参数校验和调用 service，不直接处理 PDF、LLM prompt 或数据库细节。

MVP API 能力：

- 上传论文。
- 查询论文状态。
- 查询 chunk 和 citation 元数据。
- 生成/读取 GNN 论文卡片。
- 对单篇论文提问并返回带 citations 的答案。

### 3.2 Service 层

Service 层负责工作流编排：

- `PaperIngestionService`：计算 hash、复用已有 paper、保存原始 PDF、触发解析。
- `PdfParsingService`：调用 PDF parser，输出页面文本和基础章节线索。
- `TextCleaningService`：过滤参考文献噪声、页眉页脚、重复断行、公式残片等。
- `ChunkingService`：按章节、页码和 token 预算切分 chunk，生成可引用 evidence。
- `PaperCardService`：面向 GNN schema 抽取结构化 paper card。
- `PaperQAService`：检索相关 chunk，生成带 citations 的单篇论文回答。

### 3.3 Storage 层

MVP 使用 SQLite 存 metadata，使用本地文件系统存大文本和生成产物。

SQLite 适合保存：

- paper metadata：`paper_id`、`file_hash`、文件路径、处理状态。
- chunk metadata：`chunk_id`、`paper_id`、页码、章节、文本路径。
- artifact metadata：paper card、method spec、QA 记录、生成时间。

本地文件适合保存：

- 原始 PDF。
- 解析后的 page text。
- 清洗后的 paragraph text。
- 清洗后的 chunk JSONL。
- paper card JSON。
- method spec YAML。
- 生成项目骨架。

### 3.4 Model/LLM 层

模型调用通过抽象接口隔离，配置从 `.env` 读取，不硬编码 API key。MVP 中所有生成型输出必须能追溯到 chunk evidence，尤其是 QA 和 paper card 中的关键结论。

可替换组件：

- 结构化抽取模型。
- embedding 模型。
- QA 生成模型。
- reranker。

### 3.5 Streamlit UI 层

Streamlit 只作为 MVP demo，不承担核心业务逻辑。UI 通过 FastAPI 调用后端接口：

- 上传 PDF。
- 展示 paper card。
- 查看 chunk/citation。
- 单篇论文问答。

## 4. 核心工作流

### 4.1 论文上传与 hash 复用

1. 用户上传 PDF。
2. 系统计算 `sha256 file_hash`。
3. 查询 SQLite 是否存在相同 hash。
4. 若存在并已完成解析，返回已有 `paper_id` 和 artifact 状态。
5. 若不存在，创建 paper 记录，保存 PDF 到 `data/papers/{paper_id}.pdf`。
6. 进入解析工作流。

### 4.2 PDF 解析与文本清洗

1. PDF parser 输出 page-level text。
2. 章节识别器尝试识别 abstract、introduction、method、experiments、results、appendix、references。
3. 清洗器删除或标记低价值文本：
   - 页眉页脚。
   - 页码。
   - 参考文献条目。
   - 重复版权声明。
   - 明显断裂的表格残片。
4. 保留每段文本的页码、章节和来源位置。

### 4.3 Chunk 与 citation 持久化

1. 按章节边界优先切分。
2. 在 token 上限内合并相邻段落。
3. 每个 chunk 记录：
   - `paper_id`
   - `chunk_id`
   - `page_start`
   - `page_end`
   - `section`
   - `text`
   - `evidence_span`
4. chunk 文本保存为 JSONL，metadata 写入 SQLite。

### 4.4 GNN-specific Paper Card 生成

系统从 chunks 中抽取并归一化：

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
- `main_results`
- `reproduction_difficulty`
- `missing_implementation_details`

每个关键字段应尽量附带 citations，无法从论文中确认的字段标记为 `unknown` 或写入 `missing_implementation_details`，不能凭空补齐。

### 4.4.1 PaperCard 质量评估与人工审查

PaperCard 生成后进入审查环节。系统提供轻量质量报告，帮助用户判断抽取结果是否足够进入复现规划：

- completeness：核心复现字段是否齐全，包括任务、图类型、数据集、模型模块、指标和 baseline。
- citation coverage：抽取值是否有 citation evidence。
- suspicious values：标记来自 `related_work`、`unknown` 或无 citation 的低置信值。
- golden comparison：如果存在 `data/eval/{paper_id}.golden.json`，计算字段级 precision/recall。

用户可以在 UI 中人工编辑 PaperCard 字段并保存 reviewed artifact。Reviewed PaperCard 与自动生成结果分开保存，后续多论文对比、复现 checklist 和 `method_spec.yaml` 优先使用 reviewed 版本。

### 4.5 单篇论文 QA

1. 用户提交 `paper_id` 和问题。
2. 系统在该论文 chunks 内检索相关 evidence。
3. QA 模型基于 evidence 生成回答。
4. 返回 answer 和 citations。
5. 如果 evidence 不足，明确返回无法确认的部分，并给出已检索到的相关依据。

## 5. Phase 边界

### Phase 1

只实现单篇论文闭环：

- 上传、hash 去重、PDF 解析、文本清洗。
- chunk/citation 持久化。
- GNN 论文卡片。
- 单篇 QA。

### Phase 2

在单篇结构化能力稳定后扩展：

- 多论文横向对比。
- 复现 checklist。
- `method_spec.yaml`。

### Phase 3

进入实验落地辅助：

- 模板驱动代码骨架生成。
- 可选 GraphRAG 联动。
- 实验日志分析。

## 6. 设计约束

- 不构建复杂多 Agent 系统。
- 不宣称自动完整复现。
- 不直接从论文文本生成不可审查的完整实验代码。
- 第一阶段不与既有 GraphRAG 项目强耦合。
- 所有基于论文内容的回答必须带 citations。
