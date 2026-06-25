# AGENTS.md

## Project goal

Build Paper2GNNLab-Agent, a research agent for GNN paper reading and experiment reproduction planning.

The project focuses on:
- GNN-specific paper card generation
- citations-based paper QA
- multi-paper comparison
- reproduction checklist generation
- method_spec.yaml generation
- template-based experiment project scaffolding

## MVP priority

Do not implement everything at once. Follow this order:

1. Paper upload and file_hash reuse
2. PDF parsing and text cleaning
3. Chunk storage with citation metadata
4. GNN-specific paper card generation
5. Single-paper QA with citations
6. Streamlit demo UI
7. Multi-paper comparison
8. Reproduction checklist
9. method_spec.yaml generation
10. Template-based code scaffold generation

## Coding rules

- Use Python.
- Use FastAPI for backend APIs.
- Use Streamlit for MVP frontend.
- Use SQLite for metadata storage.
- Use local file storage for PDFs, parsed chunks, cards, specs, and generated projects.
- Use Pydantic schemas for structured data.
- Keep modules small and testable.
- Do not hard-code API keys.
- Use .env for model API settings.
- Do not claim unsupported functionality in README.

## Important distinction

This project is not a generic paper reader.

It should be vertical to graph neural network research by extracting:
- task_type
- graph_type
- datasets
- node_types
- edge_types
- model_modules
- losses
- attacks
- defenses
- metrics
- baselines
- reproduction difficulty
- missing implementation details

## Output requirements

Generated answers should include citations when based on paper content.

Each citation should include:
- paper_id
- chunk_id
- page
- section
- evidence text

## Completion reports and commit commands

After every task that changes code, documentation, tests, configuration, or project artifacts, provide a concise completion report before ending the turn.

The report should include:
- what changed
- which files were touched
- what validation was run, or why validation was not run
- any remaining risks or follow-up work

Also provide a suggested git commit command. Prefer a bilingual, multi-message commit format, for example:

```bash
git commit -m "docs: update neighbor-mean KNN results / 更新邻居均值KNN实验结果" \
  -m "English: Add 5-seed ACM neighbor-mean KNN results, analysis, and updated DVCL feature-view recommendation." \
  -m "中文：补充 ACM 5-seed 邻居均值 KNN 实验结果、分析总结，并更新 DVCL 特征视图推荐配置。"
```

When there are unrelated uncommitted changes in the worktree, make the suggested command narrow, such as `git add AGENTS.md`, so unrelated work is not accidentally included.

## Avoid

- Do not build a complex multi-agent system in the MVP.
- Do not implement automatic full paper reproduction.
- Do not generate uncontrolled code directly from paper text.
- Do not couple tightly with the existing GraphRAG project in the first stage.
