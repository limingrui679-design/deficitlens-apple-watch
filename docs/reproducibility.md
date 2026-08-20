# Reproducibility protocol

1. Create a clean Python 3.10–3.12 environment.
2. Install `python -m pip install -e ".[dev]"`. To reproduce the exact Python 3.12 evidence
   environment, use `python -m pip install -c requirements/verified-py312.txt -e ".[dev]"`.
3. Download registered sources with `deficitlens fetch`; do not rename files.
4. Confirm checksums against `data/registry.yml`.
5. Run the benchmark command from the README with `configs/default.yml` unchanged.
6. Compare all hashes in `artifacts/verified/run_manifest.json`.
7. Run `make verify`; inspect `artifacts/verification/verification.json`, including dependency,
   repository-safety, HTML, documentation, archive, and installed-wheel checks.
8. Run `python scripts/score_project.py`; a score of 100 means every maintainer-controllable
   evidence/engineering gate passed, not that predictions are perfect or external validation,
   adoption, and impact exist.
9. Create an archive from the exact commit, extract into a temporary directory, install the wheel,
   and repeat the smoke and safety checks before publishing.

Determinism is controlled by seed `20260820`. Extra Trees is single-process to avoid backend-
specific ordering and warnings. Numerical results can still differ at the final decimal across
BLAS/platform versions; the manifest records Python, NumPy, pandas, scikit-learn, and platform.

The primary 30-second windows do not overlap. The high-resolution 5-second-stride frame is
reported as a density sensitivity only. Never treat its overlapping rows as independent sample
size.

The source archive does not include raw public inputs. A fresh reproducer must obtain them from
the registered sources and verify checksums. A matching output hash is strong provenance evidence;
it is not evidence that a new person independently reproduced the project unless that run is
documented by the external party.
