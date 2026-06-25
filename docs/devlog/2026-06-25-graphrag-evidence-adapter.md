# GraphRAG Evidence Adapter

Date: 2026-06-25

## Summary

Added a thin evidence-provider boundary for single-paper QA.

The QA flow now asks an `EvidenceProvider` for `Citation` objects, then composes an answer
from those citations. This keeps Paper2GNNLab-Agent focused on agent workflow, UI, and
reproduction planning while leaving advanced GraphRAG retrieval to an external project.

## Providers

- `LocalChunkEvidenceProvider`: ranks persisted local chunks and extracts citation evidence.
- `GraphRagEvidenceProvider`: calls an external HTTP service and normalizes returned evidence
  to the local `Citation` schema.

## Configuration

Default local mode:

```powershell
P2GL_EVIDENCE_PROVIDER=local
```

Optional GraphRAG mode:

```powershell
P2GL_EVIDENCE_PROVIDER=graphrag
P2GL_GRAPHRAG_BASE_URL=http://127.0.0.1:9000
P2GL_GRAPHRAG_ENDPOINT=/qa/ask
P2GL_GRAPHRAG_TIMEOUT_SECONDS=30
```

The adapter posts:

```json
{
  "paper_id": "paper_xxx",
  "question": "What datasets are used?",
  "top_k": 6
}
```

It accepts evidence lists from response keys such as `citations`, `evidence`, `results`, or
`items`. Each evidence item may include `paper_id`, `chunk_id`, `page`, `section`, and one of
`evidence_text`, `text`, `content`, `snippet`, or `quote`.

If the external service is unavailable or returns no usable evidence, QA automatically falls
back to local chunk retrieval.
