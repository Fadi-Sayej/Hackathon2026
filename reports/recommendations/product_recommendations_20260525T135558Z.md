# Product Recommendation Readiness

- Generated at: 2026-05-25T13:55:58.963983+00:00
- Status: readiness_only
- Real recommendations were not generated.

## Missing prerequisites

- missing matching parquet

## Required inputs

- Real YomYom POS silver tables with non-sample `_source_file` metadata
- Competitor product signals parquet
- Matching output that links internal products to competitor signals

## Recommendation guardrails

- No recommendation is emitted from one signal only
- Evidence must include at least two independent inputs
- Planogram recommendations are intentionally out of scope here
