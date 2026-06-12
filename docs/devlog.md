# 开发日志

## 2026-06-12：文本清洗与章节识别

### 背景

Phase 1 已完成论文上传、hash 去重、PDF page-level text 解析。本次继续打通 parsed text 到 cleaned paragraphs 的步骤，为后续 chunk/citation 持久化做准备。

### 完成内容

- 新增 `data/cleaned/` 作为清洗后文本 artifact 目录。
- 新增 `CleanedParagraph`、`CleanedPaper`、`CleanPaperRequest`、`CleanPaperResponse` schema。
- 新增规则版 `TextCleaner`：
  - 识别 `abstract`、`introduction`、`method`、`experiments`、`results`、`discussion`、`conclusion`、`references` 等常见章节。
  - 过滤页码、页眉页脚、出版声明、arXiv 标记、参考文献条目等低价值文本。
  - 输出带 `page`、`section`、`text` 的 paragraph-level artifact。
- `parse_pdf` 成功后自动触发清洗，状态更新为 `cleaned`。
- 新增 `POST /api/v1/papers/{paper_id}/clean`，支持 `force=false` 复用已有 cleaned artifact。
- `GET /api/v1/papers/{paper_id}` 的 artifacts 增加 `parsed` 和 `cleaned` 标志。
- 更新 `docs/api.md` 和 `docs/design.md`。
- 更新 `TODO.md`，标记文本清洗与章节识别完成。

### 验证

```powershell
.\.venv\Scripts\python.exe -m ruff check . --no-cache
.\.venv\Scripts\python.exe -m pytest --basetemp .tmp/pytest -p no:cacheprovider
```

### 后续

下一步进入 chunk/citation 持久化：

- 从 `data/cleaned/{paper_id}.json` 读取 paragraphs。
- 按 section 和长度预算切分 chunk。
- 生成稳定 `chunk_id`。
- 保存 `data/chunks/{paper_id}.jsonl`。
- SQLite 记录 chunk metadata。
- 增加 `GET /api/v1/papers/{paper_id}/chunks`。
