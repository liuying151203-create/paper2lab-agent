# 2026-06-12 Streamlit MVP UI

## 背景

Phase 1 的后端链路已经覆盖上传、解析/清洗、chunk/citation、GNN PaperCard 和单篇 QA。本次实现 Streamlit MVP UI，让每做完一个功能后都能在本地界面实际测试。

## 完成内容

- 将 `src/paper2gnnlab_agent/ui/app.py` 从占位壳改为单页工作台。
- 支持上传 GNN 论文 PDF。
- 支持展示最近处理的论文并选择当前 paper。
- 支持触发：
  - parse and clean
  - generate chunks
  - generate PaperCard
- 支持展示 artifact readiness：
  - parsed
  - cleaned
  - chunks
  - paper_card
- 支持展示 GNN PaperCard 字段和 citation evidence。
- 支持单篇论文 QA，展示 answer、unsupported claims 和 citations。
- UI 直接复用 `PaperIngestionService`，避免 MVP 阶段必须同时启动 FastAPI 和 Streamlit 两个进程。
- `PaperRepository` 新增 `list_recent()`，用于 UI 刷新后重新选择已有论文。

## 当前策略

- UI 是本地实验工作台，不做权限、队列和多人协作。
- QA 仍使用当前的 extractive chunk QA，不调用外部 LLM。
- PaperCard 仍使用规则版抽取器，复杂表格和隐式信息后续再接 LLM 结构化抽取。

## 启动方式

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\paper2gnnlab_agent\ui\app.py
```

## 下一步

- 准备一个最小样例 PDF，用于端到端 UI 冒烟测试。
- 之后进入 Phase 2：多论文对比。
