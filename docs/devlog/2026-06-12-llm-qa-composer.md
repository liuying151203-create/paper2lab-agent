# 2026-06-12 可选 LLM QA Composer

## 背景

Streamlit MVP UI 跑通后，QA 的答案仍然偏像 chunks，因为上一版只做 extractive answer。为了让单篇问答更接近科研 Agent 的阅读体验，本次加入可选 LLM answer composer。

## 完成内容

- 新增 `services/llm.py`。
- 新增 `OpenAICompatibleChatClient`，用于调用 OpenAI-compatible `/chat/completions` 接口。
- 新增 `AnswerComposer` 抽象。
- 保留 `ExtractiveAnswerComposer` 作为默认离线模式。
- 新增 `LlmAnswerComposer`：
  - 输入只包含检索到的 citation evidence。
  - prompt 要求只基于 evidence 回答。
  - 回答中使用 `[1]`、`[2]` 形式指向 evidence。
  - LLM 调用失败时自动回退 extractive answer。
- `FastAPI` 和 `Streamlit` 共用 `.env` 模型配置。
- UI 侧展示当前模式：
  - `extractive QA`
  - `LLM QA on`

## 配置方式

复制 `.env.example` 为 `.env`，填写：

```text
P2GL_MODEL_PROVIDER=openai
P2GL_MODEL_NAME=your-model-name
P2GL_MODEL_BASE_URL=https://api.openai.com/v1
P2GL_API_KEY=your-api-key
```

若使用本地或第三方 OpenAI-compatible 服务，可将 `P2GL_MODEL_PROVIDER` 设为 `openai_compatible`，并填写对应 `P2GL_MODEL_BASE_URL`。

## 当前限制

- 当前只增强 QA 的答案组织，不改变检索策略。
- PaperCard 仍使用规则版抽取器；下一步再实现 LLM structured extractor。
- 当前客户端优先兼容 `/chat/completions`，后续可以增加 Responses API 客户端。

## 验证

- 新增 fake LLM client 单测，验证 LLM composer 会被调用。
- 保持无模型配置时的 extractive QA 行为。
