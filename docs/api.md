# MVP API 设计

本文定义 Phase 1 需要的 FastAPI 接口。接口围绕单篇 GNN 论文的上传、解析、文本清洗、chunk/citation 持久化、结构化论文卡片和带引用问答展开。

## 1. 基础约定

- Base URL: `/api/v1`
- 请求/响应使用 JSON，文件上传使用 `multipart/form-data`。
- 所有返回论文内容结论的接口必须包含 citations 或明确说明缺少证据。

统一错误：

```json
{
  "error": {
    "code": "paper_not_found",
    "message": "Paper not found.",
    "details": {}
  }
}
```

## 2. Health Check

### `GET /api/v1/health`

用途：检查服务是否可用。

响应：

```json
{
  "status": "ok",
  "service": "paper2gnnlab-agent",
  "env": "development",
  "version": "0.1.0"
}
```

## 3. 上传论文

### `POST /api/v1/papers`

用途：上传 PDF，计算 `file_hash`，如已存在则复用已有 paper。

请求：

- Content-Type: `multipart/form-data`
- 字段：
  - `file`: PDF 文件

响应：

```json
{
  "paper_id": "paper_a1b2c3d4",
  "file_hash": "sha256...",
  "filename": "gnn_paper.pdf",
  "status": "uploaded",
  "reused": false,
  "next_actions": ["parse"]
}
```

行为：

- 若 hash 已存在，返回已有 `paper_id`，`reused=true`。
- 若 hash 不存在，保存 PDF 并创建 metadata。
- 此接口不阻塞到 paper card 生成完成。

## 4. 获取论文状态

### `GET /api/v1/papers/{paper_id}`

用途：查询论文 metadata、处理状态和本地 artifact 状态。

响应：

```json
{
  "paper_id": "paper_a1b2c3d4",
  "file_hash": "sha256...",
  "filename": "gnn_paper.pdf",
  "title": "Example GNN Paper",
  "authors": ["A. Researcher"],
  "year": 2026,
  "venue": "ICLR",
  "status": "cleaned",
  "created_at": "2026-06-11T10:00:00+08:00",
  "updated_at": "2026-06-11T10:10:00+08:00",
  "artifacts": {
    "parsed": true,
    "cleaned": true,
    "chunks": false,
    "paper_card": false,
    "method_spec": false
  }
}
```

## 5. 触发 PDF 解析

### `POST /api/v1/papers/{paper_id}/parse`

用途：触发 PDF page-level text 解析，并在解析成功后自动执行文本清洗与章节识别。

请求：

```json
{
  "force": false
}
```

响应：

```json
{
  "paper_id": "paper_a1b2c3d4",
  "status": "cleaned",
  "pages_count": 12,
  "reused": false
}
```

行为：

- `force=false` 且已有 parsed artifact 时直接复用。
- `force=true` 时重新解析并覆盖 parsed/cleaned artifacts。
- 解析输出保存到 `data/parsed/{paper_id}.json`。
- 清洗输出保存到 `data/cleaned/{paper_id}.json`。
- 解析失败时 `Paper.status` 置为 `failed`，并记录 `error_message`。

## 6. 清洗文本与章节识别

### `POST /api/v1/papers/{paper_id}/clean`

用途：基于已解析的 page-level text 执行规则化文本清洗和章节识别。

请求：

```json
{
  "force": false
}
```

响应：

```json
{
  "paper_id": "paper_a1b2c3d4",
  "status": "cleaned",
  "paragraphs_count": 42,
  "sections": ["abstract", "introduction", "method", "experiments"],
  "reused": false
}
```

行为：

- 读取 `data/parsed/{paper_id}.json`。
- 输出 `data/cleaned/{paper_id}.json`。
- 识别常见 GNN 论文章节，如 `abstract`、`introduction`、`method`、`experiments`、`results`、`conclusion`。
- 过滤页码、页眉页脚、出版声明、arXiv 标记、参考文献条目等低价值文本。
- 若 `force=false` 且 cleaned artifact 已存在，则直接复用。
- 若论文尚未解析，返回 `409`。

## 7. 获取 Chunks

### `POST /api/v1/papers/{paper_id}/chunks`

用途：基于 cleaned paragraphs 生成 citation-ready chunks，并保存 JSONL 与 SQLite metadata。

请求：

```json
{
  "force": false,
  "max_chars": 1800
}
```

响应：

```json
{
  "paper_id": "paper_a1b2c3d4",
  "status": "chunked",
  "chunks_count": 128,
  "reused": false
}
```

行为：

- 读取 `data/cleaned/{paper_id}.json`。
- 输出 `data/chunks/{paper_id}.jsonl`。
- 每个 chunk 生成稳定 `chunk_id`。
- 每个 chunk 带 `paper_id`、`chunk_id`、页码、章节、`evidence_text` citation metadata。
- SQLite 保存 chunk metadata，完整 chunk text 保留在 JSONL 文件中。
- 若论文尚未清洗，返回 `409`。

### `GET /api/v1/papers/{paper_id}/chunks`

用途：查看论文 chunks 和 citation 元数据，用于调试与 UI 展示。

Query：

- `section`：可选，按章节过滤。
- `page`：可选，按页过滤。
- `limit`：默认 `50`。
- `offset`：默认 `0`。

响应：

```json
{
  "paper_id": "paper_a1b2c3d4",
  "total": 128,
  "items": [
    {
      "chunk_id": "chunk_a1b2c3d4_0001",
      "paper_id": "paper_a1b2c3d4",
      "index": 1,
      "page_start": 2,
      "page_end": 3,
      "section": "Method",
      "text": "The proposed GNN module...",
      "evidence_text": "The proposed GNN module...",
      "token_count": 512,
      "citation": {
        "paper_id": "paper_a1b2c3d4",
        "chunk_id": "chunk_a1b2c3d4_0001",
        "page": 2,
        "section": "Method",
        "evidence_text": "The proposed GNN module..."
      }
    }
  ]
}
```

## 8. 生成或获取 Paper Card

### `POST /api/v1/papers/{paper_id}/card`

用途：基于 chunks 生成 GNN-specific paper card。

请求：

```json
{
  "force": false
}
```

响应：

```json
{
  "paper_id": "paper_a1b2c3d4",
  "status": "card_ready",
  "reused": false,
  "card": {
    "paper_id": "paper_a1b2c3d4",
    "task_type": [
      {
        "value": "node classification",
        "confidence": "high",
        "citations": [
          {
            "paper_id": "paper_a1b2c3d4",
            "chunk_id": "chunk_a1b2c3d4_0012",
            "page": 4,
            "section": "Experiments",
            "evidence_text": "..."
          }
        ]
      }
    ],
    "reproduction_difficulty": {
      "level": "unknown",
      "reasons": []
    },
    "missing_implementation_details": [],
    "generated_at": "2026-06-11T10:10:00+08:00"
  }
}
```

行为：

- 默认使用规则版抽取器，从 chunks 中抽取 GNN 垂直字段并附带 citations。
- 若配置 `P2GL_MODEL_PROVIDER`、`P2GL_MODEL_NAME`、`P2GL_API_KEY`，则使用可选 LLM structured extractor 生成 PaperCard JSON。
- LLM 输出必须通过 `PaperCard` Pydantic schema 校验，且 citations 必须对应当前论文已有 chunks。
- LLM 调用失败或 JSON 校验失败时自动回退规则版抽取器。
- 输出保存到 `data/cards/{paper_id}.json`。
- 生成成功后 `Paper.status` 更新为 `card_ready`。
- 若 `force=false` 且 card artifact 已存在，则直接复用。
- 若论文尚未 chunk，返回 `409`。

### `GET /api/v1/papers/{paper_id}/card`

用途：读取已生成的 paper card。

行为：

- 若不存在，返回 `404 card_not_ready`。
- 不在 GET 中隐式触发 LLM 生成，避免不可预期成本。

## 9. 单篇论文问答

### `POST /api/v1/papers/{paper_id}/qa`

用途：围绕单篇论文提问，返回带 citations 的回答。

请求：

```json
{
  "question": "What datasets and baselines are used in this GNN paper?",
  "top_k": 6
}
```

响应：

```json
{
  "paper_id": "paper_a1b2c3d4",
  "question": "What datasets and baselines are used in this GNN paper?",
  "answer": "The paper evaluates on ...",
  "citations": [
    {
      "paper_id": "paper_a1b2c3d4",
      "chunk_id": "chunk_a1b2c3d4_0042",
      "page": 7,
      "section": "Experiments",
      "evidence_text": "..."
    }
  ],
  "unsupported_claims": []
}
```

行为：

- 只在指定 `paper_id` 的 chunks 内检索。
- 默认使用轻量词项检索和 extractive answer。
- 若配置 `P2GL_MODEL_PROVIDER`、`P2GL_MODEL_NAME`、`P2GL_API_KEY`，则使用可选 LLM answer composer 将检索到的 evidence 写成简洁回答。
- LLM composer 只能使用检索到的 citation evidence，不应使用无 citation 的论文事实。
- LLM 调用失败时自动回退到 extractive answer。
- 如果找不到足够证据，返回说明性回答并填充 `unsupported_claims`。
- 若论文尚未 chunk，返回 `409`。

## 10. 多论文对比

### `POST /api/v1/comparisons`

用途：基于已生成的 GNN PaperCard 做多论文横向对比。

请求：

```json
{
  "paper_ids": ["paper_a1b2c3d4", "paper_e5f6g7h8"],
  "dimensions": ["task_type", "datasets", "model_modules", "metrics", "baselines"]
}
```

响应：

```json
{
  "dimensions": ["task_type", "datasets", "model_modules", "metrics", "baselines"],
  "rows": [
    {
      "paper_id": "paper_a1b2c3d4",
      "values": {
        "datasets": [
          {
            "value": "Cora",
            "confidence": "medium",
            "citations": [
              {
                "paper_id": "paper_a1b2c3d4",
                "chunk_id": "chunk_a1b2c3d4_0003",
                "page": 3,
                "section": "experiments",
                "evidence_text": "..."
              }
            ]
          }
        ]
      }
    }
  ],
  "summary": "Compared 2 papers across 5 dimensions. Shared datasets: Cora.",
  "citations": []
}
```

行为：

- 只读取 `data/cards/{paper_id}.json`。
- 不隐式触发 parse、chunk 或 PaperCard 生成。
- 若任一 paper 不存在，返回 `404`。
- 若任一 paper 尚未生成 PaperCard，返回 `409`。
- 不支持的 dimensions 会被忽略；若全部无效，则使用默认对比维度。

## 11. 复现 Checklist

### `POST /api/v1/papers/{paper_id}/reproduction-plan`

用途：基于已生成的 GNN PaperCard 生成复现 checklist，输出 `ReproductionPlan`。

请求：
```json
{
  "force": false
}
```

响应：
```json
{
  "paper_id": "paper_a1b2c3d4",
  "status": "reproduction_plan_ready",
  "reused": false,
  "plan": {
    "paper_id": "paper_a1b2c3d4",
    "objective": "Reproduce Example GNN Paper for node classification on Cora.",
    "environment": [
      {
        "item": "Create a Python environment with PyTorch and a graph learning stack such as PyG or DGL.",
        "status": "needs_manual_check",
        "rationale": "PaperCard does not encode exact package versions...",
        "citations": []
      }
    ],
    "data_preparation": [],
    "model_implementation": [],
    "attack_or_defense_setup": [],
    "training_pipeline": [],
    "evaluation": [],
    "ablation_studies": [],
    "risks": [],
    "missing_details": [],
    "estimated_difficulty": "medium",
    "generated_at": "2026-06-12T10:10:00Z"
  }
}
```

行为：
- 只读取 `data/cards/{paper_id}.json`，不隐式触发 PDF 解析、chunk 或 PaperCard 生成。
- 输出保存到 `data/specs/{paper_id}.reproduction_plan.json`。
- `force=false` 且 reproduction plan 已存在时直接复用，返回 `reused=true`。
- 若 paper 不存在，返回 `404`。
- 若 PaperCard 尚未生成，返回 `409`。
- checklist 按 GNN 复现流程拆分为环境、数据准备、模型实现、攻击/防御设置、训练、评估、消融、风险和缺失实现细节。
- 基于论文内容的 checklist item 必须保留 citations；论文未明确给出的实现细节标记为 `needs_manual_check` 或 `blocked`。

## 12. Phase 2 预留接口

- `POST /api/v1/papers/{paper_id}/method-spec`：生成 `method_spec.yaml`。

## 13. Phase 3 预留接口

- `POST /api/v1/method-specs/{spec_id}/scaffold`：基于模板生成实验项目骨架。
- `POST /api/v1/graphrag/search`：可选 GraphRAG 联动检索。
- `POST /api/v1/experiment-logs/analyze`：实验日志分析。
