# Schema 设计

本文定义 MVP 到 Phase 3 需要的核心 Pydantic/JSON schema。字段命名优先服务 GNN 论文阅读与实验复现，不做通用论文库抽象。

## 1. 通用约定

- `paper_id`：系统生成的稳定 ID，建议格式 `paper_{short_hash}`。
- `chunk_id`：系统生成的稳定 ID，建议格式 `chunk_{paper_short_hash}_{index}`。
- `file_hash`：PDF 文件内容的 SHA-256。
- 时间字段使用 ISO 8601 字符串。
- 枚举字段在早期允许字符串扩展，避免过早封闭 GNN 研究类型。
- 所有从论文内容生成的结构化字段都应能关联到 `Citation[]`。

## 2. Paper

```python
class Paper(BaseModel):
    paper_id: str
    file_hash: str
    filename: str
    title: str | None = None
    authors: list[str] = []
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    source_path: str
    status: Literal[
        "uploaded",
        "parsing",
        "parsed",
        "cleaned",
        "chunked",
        "card_ready",
        "failed",
    ]
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None
```

JSON example：

```json
{
  "paper_id": "paper_a1b2c3d4",
  "file_hash": "sha256...",
  "filename": "gnn_robustness.pdf",
  "title": "Example GNN Robustness Paper",
  "authors": ["A. Researcher"],
  "year": 2026,
  "venue": "ICLR",
  "abstract": "This paper studies...",
  "source_path": "data/papers/paper_a1b2c3d4.pdf",
  "status": "card_ready",
  "created_at": "2026-06-11T10:00:00+08:00",
  "updated_at": "2026-06-11T10:10:00+08:00",
  "error_message": null
}
```

## 3. Chunk

```python
class Chunk(BaseModel):
    chunk_id: str
    paper_id: str
    index: int
    page_start: int
    page_end: int
    section: str | None = None
    text: str
    evidence_text: str
    token_count: int | None = None
    source_offsets: list[SourceOffset] = []
    citation: Citation
    created_at: datetime

class SourceOffset(BaseModel):
    page: int
    char_start: int | None = None
    char_end: int | None = None
```

说明：

- `section` 应保留论文原始章节名；无法识别时可用 `unknown`。
- `text` 是清洗后文本，不应包含大量参考文献噪声。
- `source_offsets` 用于后续更精确 evidence 定位。

Implementation notes:

- `evidence_text` is the short citation snippet shown in answers and cards.
- `citation` keeps the required `paper_id`, `chunk_id`, `page`, `section`, and evidence text.
- Full chunk text is stored in `data/chunks/{paper_id}.jsonl`; SQLite stores metadata for lookup.

## 4. Citation

```python
class Citation(BaseModel):
    paper_id: str
    chunk_id: str
    page: int | None = None
    section: str | None = None
    evidence_text: str
```

约束：

- `evidence_text` 应是短证据片段，不是整段长 chunk。
- QA、paper card、comparison、reproduction plan 中凡是基于论文事实的结论都应引用 `Citation`。

## 5. GNNEntity

```python
class CitedValue(BaseModel):
    value: str
    citations: list[Citation] = []
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
```

用于 task、dataset、metric、baseline 等字段，避免没有证据的裸字符串。

## 6. PaperCard

```python
class PaperCard(BaseModel):
    paper_id: str
    title: CitedValue | None = None
    problem: CitedValue | None = None
    task_type: list[CitedValue] = []
    graph_type: list[CitedValue] = []
    datasets: list[CitedValue] = []
    node_types: list[CitedValue] = []
    edge_types: list[CitedValue] = []
    model_modules: list[CitedValue] = []
    losses: list[CitedValue] = []
    attacks: list[CitedValue] = []
    defenses: list[CitedValue] = []
    metrics: list[CitedValue] = []
    baselines: list[CitedValue] = []
    training_setup: list[CitedValue] = []
    evaluation_protocol: list[CitedValue] = []
    main_results: list[CitedValue] = []
    limitations: list[CitedValue] = []
    reproduction_difficulty: ReproductionDifficulty
    missing_implementation_details: list[CitedValue] = []
    generated_at: datetime

class ReproductionDifficulty(BaseModel):
    level: Literal["low", "medium", "high", "unknown"]
    reasons: list[CitedValue] = []
```

字段说明：

- `task_type` 示例：node classification、link prediction、graph classification、recommendation、robustness evaluation。
- `graph_type` 示例：homogeneous graph、heterogeneous graph、dynamic graph、knowledge graph、bipartite graph。
- `attacks` 和 `defenses` 面向 GNN 鲁棒性论文，普通 GNN 论文可以为空。
- `missing_implementation_details` 是复现价值最高的字段之一，必须保留不确定性。

## 7. MethodSpec

`MethodSpec` 最终导出为 `method_spec.yaml`，用于 Phase 3 的模板驱动实验骨架生成。

```python
class MethodSpec(BaseModel):
    paper_id: str
    task_type: list[str]
    graph_type: list[str]
    datasets: list[DatasetSpec]
    node_types: list[str] = []
    edge_types: list[str] = []
    model_modules: list[ModelModuleSpec]
    losses: list[str] = []
    attacks: list[AttackSpec] = []
    defenses: list[DefenseSpec] = []
    metrics: list[str] = []
    baselines: list[str] = []
    training: TrainingSpec | None = None
    evaluation: EvaluationSpec | None = None
    missing_details: list[str] = []
    citations: list[Citation] = []

class DatasetSpec(BaseModel):
    name: str
    split: str | None = None
    preprocessing: list[str] = []
    citations: list[Citation] = []

class ModelModuleSpec(BaseModel):
    name: str
    role: str | None = None
    inputs: list[str] = []
    outputs: list[str] = []
    citations: list[Citation] = []

class AttackSpec(BaseModel):
    name: str
    threat_model: str | None = None
    perturbation_budget: str | None = None
    target: str | None = None
    citations: list[Citation] = []

class DefenseSpec(BaseModel):
    name: str
    strategy: str | None = None
    citations: list[Citation] = []

class TrainingSpec(BaseModel):
    optimizer: str | None = None
    learning_rate: str | None = None
    epochs: str | None = None
    batch_size: str | None = None
    hardware: str | None = None
    citations: list[Citation] = []

class EvaluationSpec(BaseModel):
    protocol: str | None = None
    metrics: list[str] = []
    ablations: list[str] = []
    citations: list[Citation] = []
```

## 8. ReproductionPlan

```python
class ReproductionPlan(BaseModel):
    paper_id: str
    objective: str
    environment: list[ChecklistItem] = []
    data_preparation: list[ChecklistItem] = []
    model_implementation: list[ChecklistItem] = []
    attack_or_defense_setup: list[ChecklistItem] = []
    training_pipeline: list[ChecklistItem] = []
    evaluation: list[ChecklistItem] = []
    ablation_studies: list[ChecklistItem] = []
    risks: list[ChecklistItem] = []
    missing_details: list[ChecklistItem] = []
    estimated_difficulty: Literal["low", "medium", "high", "unknown"]
    generated_at: datetime

class ChecklistItem(BaseModel):
    item: str
    status: Literal["todo", "blocked", "needs_manual_check"] = "todo"
    rationale: str | None = None
    citations: list[Citation] = []
```

## 9. QA Schema

```python
class PaperQARequest(BaseModel):
    question: str
    top_k: int = 6

class PaperQAResponse(BaseModel):
    paper_id: str
    question: str
    answer: str
    citations: list[Citation]
    unsupported_claims: list[str] = []
```

约束：

- `paper_id` 来自 `POST /api/v1/papers/{paper_id}/qa` 路径参数，不放在请求体里。
- `answer` 中不能包含没有 evidence 支撑的确定性论文事实。
- evidence 不足时，写入 `unsupported_claims`，并在回答中说明无法从当前论文内容确认。

## 10. Comparison Schema

```python
class PaperComparisonRequest(BaseModel):
    paper_ids: list[str]
    dimensions: list[str] = [
        "task_type",
        "graph_type",
        "datasets",
        "model_modules",
        "attacks",
        "defenses",
        "metrics",
        "baselines",
        "reproduction_difficulty",
    ]

class PaperComparisonRow(BaseModel):
    paper_id: str
    values: dict[str, list[CitedValue]]

class PaperComparisonResponse(BaseModel):
    dimensions: list[str]
    rows: list[PaperComparisonRow]
    summary: str
    citations: list[Citation]
```

Comparison 属于 Phase 2，不进入 MVP 第一批实现。
