# SmartShelf Data Workspace

This folder is the local-first workspace for SmartShelf datasets.

## Purpose

- Keep raw downloads outside the React app.
- Separate application demo data from analytics data.
- Prepare a clean handoff path for future RAG processing.

## Folder layout

```txt
data/
  raw/
    huggingface/
    kaggle/
  processed/
    demo/
    analytics/
    rag/
  exports/
    sample-app-data/
```

## Current Sprint 1 decisions

- Primary MVP source: `anirudhchauhan/retail-store-inventory-forecasting-dataset`
- Backup MVP source: `andrexibiza/grocery-sales-dataset`
- Secondary analytics and RAG source: `Dingdong-Inc/FreshRetailNet-50K`
- Backend storage: deferred
- Supabase: later, only when vector search or persistent backend needs are real
- Firebase: not required for the current scope

## Important rule

Do not mix `processed/demo` and `processed/rag`.

- `processed/demo` is for the app experience.
- `processed/rag` is for summaries, chunks, and future retrieval work.
