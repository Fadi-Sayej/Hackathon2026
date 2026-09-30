# POS snapshot durability (B-6)

## Why this exists

The POS export is an inventory snapshot with **no sales history**. Sales velocity is reconstructed
entirely from the **stock delta between two POS snapshots** (see `src/snapshots/velocity.py` and
`compare_pos_snapshots.py`). That makes the snapshot series the single most valuable dataset in the
pilot — and it needs to be **continuous and durable**, not living on one laptop that a reformat
would wipe.

Snapshots are written by the import pipeline to:

```
data/internal/snapshots/<timestamp>/
  ├─ products.parquet     # silver POS products at import time
  ├─ inventory.parquet    # silver POS inventory (when present)
  └─ meta.json            # { snapshot_ts, imported_at }
```

## Decision — commit snapshots to git (Fadi's option 1)

Of the three options in `nagham.md` B-6, we took the first: **a `.gitignore` exception** so the
snapshot subtree is committed to the repo. It is credential-free, needs no running service, and the
snapshots are tiny (~KB each — the whole tree is ~20 KB today).

The exception lives at the **end** of `.gitignore` (it must stay last so it overrides both the
`data/internal/snapshots/` and the global `*.parquet` ignores above it):

```gitignore
!data/internal/snapshots/
!data/internal/snapshots/**
```

Verified with `git check-ignore` / `git add -n`: snapshot `*.parquet` and `meta.json` are now
committable, while every other `*.parquet` (e.g. `data/internal/silver_pos/`) stays ignored.

> ⚠️ **Privacy:** this puts a real store's inventory data in git. **Keep the repository private.**

## How the series accumulates (the daily step)

Git is the shared store, so the "Malik imports on his laptop, Fadi runs the pipeline on his" split
no longer fragments the history — whoever runs an import commits the snapshot, and git merges the
continuous series. Add this to the daily flow after a POS import:

```bash
python3 scripts/import_pos.py            # the export configs/store.yaml names; writes a new snapshot
git add data/internal/snapshots
git commit -m "data: POS snapshot <date>"
git push
```

To keep it simple, either designate **one machine** that owns ingestion, or agree that anyone who
imports also commits + pushes the snapshot the same day.

## Current state

The 5 existing snapshots hold only `meta.json` (they predate a POS import that produced parquet).
After the next real import, `archive_current_silver()` writes `products.parquet` and it will be
picked up by the exception and committed. No action needed beyond the daily step above.

## Upgrade path (option 2, later)

Once B-2 (Firestore) is activated, snapshots can additionally be mirrored to Firestore / object
storage for off-repo redundancy. That's a nice-to-have, not required for durability — git already
gives us a backed-up, continuous series. **Coordinate with Fadi** before adding it so ingestion
isn't written twice.
