# Reproducibility protocol

1. Create a clean Python 3.10–3.12 environment.
2. Install `python -m pip install -e ".[dev]"`. To reproduce the exact Python 3.12 evidence
   environment, use `python -m pip install -c requirements/verified-py312.txt -e ".[dev]"`.
3. Download registered sources with `deficitlens fetch`; do not rename files.
4. Confirm checksums against `data/registry.yml`.
5. Run the benchmark command from the README with `configs/default.yml` unchanged.
6. Compare all hashes in `artifacts/verified/run_manifest.json`.
7. Run `make verify`; inspect `artifacts/verification/verification.json`.
8. Run `python scripts/score_project.py`; a score of 100 means every evidence/engineering gate
   passed, not that model predictions are perfect.

Determinism is controlled by seed `20260820`. Extra Trees is single-process to avoid backend-
specific ordering and warnings. Numerical results can still differ at the final decimal across
BLAS/platform versions; the manifest records Python, NumPy, pandas, scikit-learn, and platform.

The primary 30-second windows do not overlap. The high-resolution 5-second-stride frame is
reported as a density sensitivity only. Never treat its overlapping rows as independent sample
size.
