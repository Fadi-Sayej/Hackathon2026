> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Retained for history. Describes modules that no longer exist, or designs superseded
> on 2026-09-08 by the System Design. Do not act on it.
>
> **Canonical sources:** [`docs/README.md`](../README.md)

---

# SmartShelf AI RAG Readiness

Sprint C4 creates a local JSONL knowledge corpus for future retrieval-augmented generation.

## What Exists

The corpus builder is:

```txt
scripts/build-rag-corpus.mjs
```

It generates:

```txt
data/processed/rag/products.jsonl
data/processed/rag/category-playbooks.jsonl
data/processed/rag/planogram-rules.jsonl
data/processed/rag/reorder-rules.jsonl
data/processed/rag/market-context-templates.jsonl
data/processed/rag/README.md
```

## Chunk Schema

Every JSONL line includes:

```js
{
  id: string,
  source: string,
  type: string,
  category: string,
  text: string,
  tags: string[],
  metadata: object
}
```

## Chunk Types

- `product`
- `category_playbook`
- `planogram_rule`
- `reorder_rule`
- `market_context_template`

## Current Data Sources

- Product chunks use normalized demo products via `loadDemoStoreData()`.
- Category playbooks summarize current demo category movement.
- Planogram and reorder chunks encode existing SmartShelf operating rules.
- Market context templates describe weather, weekend, holiday, and local event signals.

## Future Embedding Path

A later sprint can:

1. Read JSONL files from `data/processed/rag/`.
2. Embed the `text` field.
3. Store vectors with metadata filters.
4. Retrieve by product, category, rule type, or market-signal tag.
5. Pass retrieved chunks into a safe LLM explanation adapter.

## Not Included

- No vector database.
- No embeddings.
- No LLM calls.
- No Gemini wiring.
- No paid APIs.
