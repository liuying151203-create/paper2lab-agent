# MVP API 设计

本文定义 Phase 1 需要的 FastAPI 接口。接口围绕单篇 GNN 论文的上传、解析、chunk/citation 持久化、结构化论文卡片和带引用问答展开。

## 1. 基础约定

- Base URL：`/api/v1`
- 请求/响应使用 JSON，文件上传使用 `multipart/form-data`。
- 错误响应使用统一结构。
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
  "service": "paper2gnnlab-agent"
}
```

## 3. 上传论文

### `POST /api/v1/papers`

用途：上传 PDF，计算 `file_hash`，如已存在则复用已有 paper。

请求：

- Content-Type：`multipart/form-data`
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
- 此接口不应阻塞到完整 paper card 生成完成；可返回后由后续解析接口或后台任务推进。

## 4. 获取论文状态

### `GET /api/v1/papers/{paper_id}`

用途：查询论文 metadata 和处理状态。

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
  "status": "card_ready",
  "created_at": "2026-06-11T10:00:00+08:00",
  "updated_at": "2026-06-11T10:10:00+08:00",
  "artifacts": {
    "chunks": true,
    "paper_card": true,
    "method_spec": false
  }
}
```

## 5. 触发解析

### `POST /api/v1/papers/{paper_id}/parse`

用途：触发 PDF 解析、文本清洗和 chunk 持久化。

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
  "status": "chunked",
  "chunks_count": 128,
  "reused": false
}
```

行为：

- `force=false` 且已有 chunks 时直接复用。
- `force=true` 时重新解析并覆盖该论文的 parsed/chunk artifacts。
- 解析失败时 `Paper.status` 置为 `failed`，并记录 `error_message`。

## 6. 获取 Chunks

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
      "token_count": 512
    }
  ]
}
```

## 7. 生成或获取 Paper Card

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
    "graph_type": [],
    "datasets": [],
    "model_modules": [],
    "losses": [],
    "attacks": [],
    "defenses": [],
    "metrics": [],
    "baselines": [],
    "reproduction_difficulty": {
      "level": "unknown",
      "reasons": []
    },
    "missing_implementation_details": [],
    "generated_at": "2026-06-11T10:10:00+08:00"
  }
}
```

### `GET /api/v1/papers/{paper_id}/card`

用途：读取已生成的 paper card。

行为：

- 若不存在，返回 `404 card_not_ready`。
- 不在 GET 中隐式触发 LLM 生成，避免不可预期成本。

## 8. 单篇论文问答

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
- 回答不能使用无 citation 的论文事实。
- 如果找不到足够证据，返回部分回答并填充 `unsupported_claims`。

## 9. Phase 2 预留接口

以下接口不进入 Phase 1 实现，只保留方向：

- `POST /api/v1/comparisons`：多论文横向对比。
- `POST /api/v1/papers/{paper_id}/reproduction-plan`：生成复现 checklist。
- `POST /api/v1/papers/{paper_id}/method-spec`：生成 `method_spec.yaml`。

## 10. Phase 3 预留接口

以下接口不进入 Phase 1/2 实现：

- `POST /api/v1/method-specs/{spec_id}/scaffold`：基于模板生成实验项目骨架。
- `POST /api/v1/graphrag/search`：可选 GraphRAG 联动检索。
- `POST /api/v1/experiment-logs/analyze`：实验日志分析。
