# Contributing

DeficitLens accepts narrowly scoped, testable contributions. A public contribution workflow is
not active until the repository is published; this file defines the review contract in advance.

## Before changing code

Open an issue before a large change once an issue tracker exists. Describe the decision problem,
affected evidence layer, expected failure behavior, and how the change will be verified. Never
commit Apple Health exports, credentials, private correspondence, raw third-party datasets, or
files whose redistribution rights are unclear.

New datasets must add provenance, access conditions, license, expected checksum, analytical role,
exclusions, and a data card. New models must preserve participant-grouped splits, compare against
the raw Apple value, and state whether any feature is available at intended use time. A transfer
claim requires the complete feature and endpoint contract in an independent cohort.

## Local workflow

1. Create a focused branch and a clean Python 3.10–3.12 environment.
2. Install `python -m pip install -e ".[dev]"`.
3. Add tests that fail before the change and cover relevant error paths.
4. Run `make lint typecheck coverage build verify`.
5. Inspect generated HTML, the safety report, and every changed numerical claim.
6. Update the model card, case catalog, changelog, and evidence ledger when their contracts change.

Commits should be small enough to review and should not rewrite unrelated history. Generated
numerical evidence must come from the registered pipeline and retain its manifest hashes.
Screenshots, notebook state, and a successful command alone are not validation evidence.

## Review checklist

- Inputs and licenses are registered; no private or raw source data is committed.
- Train, calibration, and test participants remain disjoint.
- Claims name the population, device, protocol, metric, and uncertainty where applicable.
- Failure modes are explicit and unsupported transfer is blocked.
- User-facing output is keyboard-readable, self-contained, and understandable without source code.
- Documentation links and wheel resources work from a fresh archive.

Contributions are licensed under Apache-2.0. Dataset terms remain separate.
