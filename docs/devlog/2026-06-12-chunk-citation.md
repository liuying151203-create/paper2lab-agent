# 2026-06-12：Chunk/Citation 持久化

## 背景

文本清洗与章节识别完成后，系统已经能得到 `data/cleaned/{paper_id}.json`。本次继续实现从 cleaned paragraphs 到 citation-ready chunks 的持久化，为后续 paper card 和单篇 QA 提供可检索证据单元。

## 完成内容

- 新增 `TextChunker`，按 cleaned paragraph 顺序生成 chunks。
- chunk 切分规则：
  - 优先不跨 section。
  - 在 `max_chars` 预算内合并同章节相邻段落。
  - 超过预算或章节变化时开启新 chunk。
- 新增稳定 `chunk_id`，格式为 `chunk_{paper_short_hash}_{index}`。
- `Chunk` schema 增加 `evidence_text` 和 `citation`。
- 新增 `ChunkRepository`，将 chunk metadata 写入 SQLite。
- 完整 chunk text 保存到 `data/chunks/{paper_id}.jsonl`。
- 新增 `POST /api/v1/papers/{paper_id}/chunks`。
- 新增 `GET /api/v1/papers/{paper_id}/chunks`。
- `Paper.status` 在 chunk 生成后更新为 `chunked`。

## 验证

```powershell
.\.venv\Scripts\python.exe -m ruff check . --no-cache
.\.venv\Scripts\python.exe -m pytest --basetemp .tmp/pytest -p no:cacheprovider
```

## 后续

下一步进入 GNN-specific Paper Card：

- 基于 chunks 抽取 GNN 论文结构化字段。
- 先实现规则/占位版 paper card service。
- 再接 LLM structured extraction。
- 增加 `POST /api/v1/papers/{paper_id}/card` 和 `GET /api/v1/papers/{paper_id}/card`。
