# Validation protocol and release claims

## Required evidence

- exact input checksums match the registry;
- WEEE yields all 17 participants and all six expected activity classes;
- the P14 timestamp anomaly is present in the evidence notes;
- every WEEE participant appears exactly once as the outer test participant;
- development, conformal calibration, and outer test participant sets are disjoint per fold;
- every prediction row is finite and non-negative;
- interval lower bounds are non-negative and upper bounds are not below lower bounds;
- primary cluster-robust and compact row-level interval coverage are reported separately;
- model metrics include raw Apple, affine, protocol-MET, and ensemble comparators;
- bootstrap resamples participant clusters;
- external audit reports primary and restored-outlier sensitivity results separately;
- subgroup cells expose support warnings;
- report and tables match their hashes in the run manifest.

## Release language

Allowed: “In this participant-held-out WEEE benchmark, model X had Y MAE with a participant-
clustered interval.”

Not allowed: “DeficitLens knows your true calories,” “the algorithm guarantees 90% coverage for
you,” or “the Series 8 external cohort validates the WEEE model.”

## Status

The current numerical snapshot and executed checks live under `artifacts/verified/` and
`artifacts/verification/`. See `docs/iteration-log.md` for defects found and fixed before the
release score reached 100.

### Verified 2026-08-20 snapshot

- 811 non-overlapping windows; 17 outer test participants; 4,544 overlapping density-sensitivity
  windows.
- Raw Apple MAE 1.651 kcal/min (participant-clustered 95% CI 1.366–1.945).
- Ensemble MAE 1.082 kcal/min (95% CI 0.875–1.305), a 34.5% reduction.
- Primary participant-cluster interval: 96.42% coverage, 5.194 kcal/min mean width.
- Compact row interval: 84.59% coverage, 3.926 kcal/min mean width; diagnostic only.
- Independent Series 8 raw-device audit: 52 primary pairs, 33.63 kcal MAE, +21.60 kcal bias.
- Restoring the paper-wide excluded participant increases external MAE to 36.34 kcal.

Activity coverage ranges from 89.2% to 100.0%; therefore the 96.4% overall result is not described
as a guarantee for every activity.
