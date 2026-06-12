# 2026-06-12 可选 LLM PaperCard 结构化抽取

## 背景

规则版 PaperCard 能跑通端到端链路，但在真实 GNN 论文上容易表现为关键词列表，难以抽取复杂方法、训练设置、复现缺口和表述不固定的字段。本次加入可选 LLM structured extractor，让 PaperCard 可以从 chunks evidence 中生成更像科研阅读卡片的结构化 JSON。

## 完成内容

- 新增 `PaperCardExtractor` 协议。
- 新增 `LlmPaperCardExtractor`。
- Prompt 输入包含：
  - chunk_id
  - page
  - section
  - citation JSON
  - chunk text
- Prompt 要求输出 `PaperCard` JSON，不输出 markdown。
- LLM 输出会经过：
  - JSON object 提取。
  - `PaperCard` Pydantic 校验。
  - 当前 paper_id 覆盖。
  - 缺省字段补齐。
  - unknown chunk citation 过滤。
- 若 LLM 调用失败、JSON 解析失败或 schema 校验失败，自动回退 `RuleBasedPaperCardExtractor`。
- FastAPI 和 Streamlit 都通过 `.env` 模型配置启用该能力。

## 配置方式

```text
P2GL_MODEL_PROVIDER=openai
P2GL_MODEL_NAME=your-model-name
P2GL_MODEL_BASE_URL=https://api.openai.com/v1
P2GL_API_KEY=your-api-key
```

也支持 `P2GL_MODEL_PROVIDER=openai_compatible` 指向本地或第三方兼容服务。

## 当前限制

- 当前 PaperCard LLM extractor 仍基于前若干 chunks，不做全局长文档 map-reduce。
- citations 只校验 `chunk_id` 属于当前论文，暂不做 evidence_text 与原文逐字一致性校验。
- 表格提取质量仍取决于 PDF text parser 是否能提取表格内容。

## 验证

- 增加 fake LLM PaperCard 单测，验证结构化 JSON 能通过 schema 并保留 citations。
- 增加 invalid JSON 回退测试，验证 LLM 失败时仍能得到规则版 PaperCard。
