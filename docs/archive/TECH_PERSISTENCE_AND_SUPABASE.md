> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Retained for history. Describes modules that no longer exist, or designs superseded
> on 2026-09-08 by the System Design. Do not act on it.
>
> **Canonical sources:** [`docs/README.md`](../README.md)

---

# SmartShelf AI Persistence And Supabase Path

Sprint C5 adds a persistence abstraction with a localStorage adapter. No Supabase project or backend is required yet.

> **Update (2026-08-07, B-2): a Firestore adapter now exists behind this same interface.**
> The pilot went with **Firestore, not Supabase**. `persistence.js` selects the adapter at load:
> `firestoreAdapter` when the `VITE_FIREBASE_*` client config is present, otherwise
> `localStorageAdapter` (unchanged default). See "Firestore adapter (B-2)" below. The Supabase
> notes further down are kept as a possible future path but are not the implemented one.

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

## Firestore adapter (B-2) — the implemented remote path

`src/lib/persistence/firestoreAdapter.js` implements the same six functions and is **local-first**,
because the interface is synchronous and `App.jsx` reads it inline at mount while Firestore is async:

- **Reads** are served synchronously from the localStorage mirror — instant, and correct offline.
- **Writes** go write-through to localStorage (returning exactly what the local adapter returns, so
  callers never change) and are then mirrored to Firestore in the background.
- On load and every reconnect it **hydrates and reconciles both ways** (last-write-wins on
  `updatedAt`), which also performs the **first-load migration** of existing localStorage data.
- Offline writes are queued by Firestore's own IndexedDB cache and flush on reconnect; the
  localStorage mirror guarantees the UI never loses a decision regardless.

Supporting pieces (all B-track owned): `src/firebase.js` (client init, anonymous sign-in, offline
cache, `isFirebaseConfigured()`), `firestore.rules` (auth-required, scoped to `stores/{storeId}`),
and a non-breaking `subscribeToPersistence()` export so a UI can refresh after a cloud sync.

Data model: `stores/{VITE_STORE_ID}/approvedOrders/*` and
`stores/{VITE_STORE_ID}/recommendationDecisions/*`.

**Activation:** set `VITE_FIREBASE_*` + `VITE_STORE_ID`, enable Anonymous sign-in, and deploy
`firestore.rules`. Until then persistence stays on localStorage automatically.

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
