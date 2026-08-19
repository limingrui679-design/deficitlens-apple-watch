# Artifacts

Generated benchmark reports, predictions, and quality evidence are written here.

- `verified/` is the small, public, derived evidence snapshot: report, figures, aggregate tables,
  outer-fold predictions, diagnostics, and a hash manifest. It contains no raw source files.
- `verification/` contains executed lint, type, test, coverage, build, and CLI evidence.
- `quality-score.json` and `quality-history.jsonl` contain the 100-point gate and iteration trail.

Raw datasets and private Apple Health exports never belong in this directory or Git history.
