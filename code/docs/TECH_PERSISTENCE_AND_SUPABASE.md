# SmartShelf AI Persistence And Supabase Path

Sprint C5 adds a persistence abstraction with a localStorage adapter. No Supabase project or backend is required yet.

## Runtime Interface

`src/lib/persistence/persistence.js` exports:

```js
saveApprovedOrder(order)
listApprovedOrders()
saveRecommendationDecision(decision)
loadRecommendationDecisions()
loadStoreProducts(storeId)
resetDemoState()
```

The current implementation delegates to:

```txt
src/lib/persistence/localStorageAdapter.js
```

## What Is Persisted Locally

The localStorage adapter stores:

- Approved recommendation decisions.
- Edited recommendation quantities.
- Rejected recommendation ids.
- Approved order snapshots.

The app reconstructs visible approved orders from the recommendation decision state so refresh can preserve the manager workflow.

## Demo Reset

When persisted decisions exist, the sidebar shows `Reset demo state`. This clears localStorage demo state and returns the app to the dashboard.

## localStorage Key

```txt
smartshelf.demoState.v1
```

## Future Supabase Tables

A later backend sprint can map the same persistence interface to Supabase tables:

- `stores`
- `products`
- `inventory_snapshots`
- `sales_history`
- `recommendations`
- `approved_orders`
- `rag_documents`
- `rag_chunks`
- `embeddings`

## Suggested Table Responsibilities

- `stores`: tenant/store profile and location metadata.
- `products`: normalized product master data.
- `inventory_snapshots`: stock, shelf quantity, capacity, returns, damages by timestamp.
- `sales_history`: product sales by day or transaction window.
- `recommendations`: generated recommendation records and status.
- `approved_orders`: purchase-order drafts approved by a manager.
- `rag_documents`: source documents for retrieval.
- `rag_chunks`: chunk text and metadata generated from RAG corpus scripts.
- `embeddings`: vector records linked to `rag_chunks`.

## Not Included In C5

- No Supabase dependency.
- No remote database.
- No authentication.
- No multi-store tenancy enforcement.
- No schema migrations.
