# Paper2GNNLab-Agent

Paper2GNNLab-Agent is a GNN-focused research assistant for paper reading and experiment reproduction planning. It is not a generic paper reader: its schemas and workflows are organized around graph neural network papers, citation-backed evidence, and conservative reproduction planning.

## Current Status

The current codebase implements the Phase 1 and Phase 2 MVP workflow:

1. Upload a PDF and reuse existing artifacts by SHA-256 `file_hash`.
2. Parse PDF pages with `pypdf`.
3. Clean low-value text such as page furniture and reference noise.
4. Split cleaned paragraphs into citation-ready chunks with `paper_id`, `chunk_id`, page, section, and evidence text.
5. Generate a GNN-specific `PaperCard` with rule-based extraction and optional LLM structured extraction.
6. Answer single-paper questions using local chunk evidence or an optional GraphRAG evidence adapter, and return citations.
7. Compare multiple generated `PaperCard` artifacts across GNN dimensions.
8. Generate a reproduction checklist from a `PaperCard`.
9. Export `method_spec.yaml` from `PaperCard` and optional reproduction-plan artifacts.
10. Use a Streamlit demo UI for upload, processing, QA, comparison, reproduction plan, and method-spec preview.

The default mode is local and conservative: no API key is required, and unsupported paper facts should not be invented. Optional OpenAI-compatible LLM calls can be enabled through `.env`.

## Not Implemented Yet

The following items are planned for Phase 3 and should not be treated as current functionality:

- Template-driven experiment project scaffolding from `method_spec.yaml`.
- Generated `README_reproduce.md`, experiment `TODO.md`, model stubs, configs, scripts, or attack modules.
- Embedding/vector search and reranking.
- Experiment log analysis and debug recommendations.
- Automatic full paper reproduction.

## GNN-Specific Extraction Targets

The project focuses on extracting and citing fields that matter for GNN reproduction:

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
- `reproduction_difficulty`
- `missing_implementation_details`

Generated answers and structured outputs should include citations when they are based on paper content. A citation includes `paper_id`, `chunk_id`, page, section, and evidence text.

## Project Layout

```text
src/paper2gnnlab_agent/
  api/        FastAPI app, routes, and dependencies
  core/       Settings loaded from .env
  models/     Pydantic schemas
  parsers/    PDF parsing, text cleaning, chunking
  services/   Ingestion, card extraction, QA, comparison, reproduction, method spec
  storage/    SQLite and local path helpers
  ui/         Streamlit MVP demo

docs/         Design, API, schema, and devlog notes
tests/        Unit and integration tests
data/         Local runtime artifacts, ignored except .gitkeep files
templates/    Reserved for Phase 3 experiment-project templates
```

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn paper2gnnlab_agent.api.app:create_app --factory --reload
```

In another terminal, run the Streamlit demo:

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\paper2gnnlab_agent\ui\app.py
```

Copy `.env.example` to `.env` only when you need custom storage paths, optional LLM settings, or optional GraphRAG evidence retrieval. Do not commit real API keys.

Optional GraphRAG evidence retrieval is configured through `.env`. The external service should accept `paper_id`, `question`, and `top_k`, and return evidence in a `citations`, `evidence`, `results`, or `items` list. Returned items are normalized to the local `Citation` schema. If the external service fails or returns no evidence, QA falls back to local chunk retrieval.

```powershell
P2GL_EVIDENCE_PROVIDER=graphrag
P2GL_GRAPHRAG_BASE_URL=http://127.0.0.1:9000
P2GL_GRAPHRAG_ENDPOINT=/qa/ask
P2GL_GRAPHRAG_TIMEOUT_SECONDS=30
```

## Useful Commands

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest --basetemp .tmp/pytest -p no:cacheprovider
.\.venv\Scripts\python.exe scripts\smoke_e2e.py
```
