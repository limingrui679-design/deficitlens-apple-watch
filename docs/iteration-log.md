# Self-audit iteration log

The score measures release evidence and engineering completeness, not predictive accuracy. The
machine-readable history is `artifacts/quality-history.jsonl`; failed and superseded iterations
remain visible.

| Iteration | Score | Evidence found | Remediation |
|---|---:|---|---|
| 1 — first real-data benchmark | 71/100 | 811 primary windows, 17-fold predictions, 52-person external audit; compact nominal-90% interval covered only 82.24%; old manifest hash and release checks incomplete | Reject row exchangeability for the primary interval; add participant-cluster calibration, normalize subgroup labels, complete docs/tests |
| 2 — cluster/taxonomy repair | 77/100 | Cluster interval covered 91.12%; `Female ` / `Male ` whitespace split removed; 23 tests and 90%+ coverage developed | Persist formal lint/type/test/build/CLI verification; fix privacy scan false positive on tool cache DBs |
| 3 — release candidate | 100/100 (provisional) | Six original release commands passed | Reopen the audit and add an installed-wheel test, because building a wheel does not prove its bundled resources work |
| 4 — adversarial package audit | 98/100 | Wheel built, but first isolation strategy lacked runtime dependencies; the new build gate failed | Install the wheel into an isolated target while using the verified runtime dependencies; assert imports resolve from the wheel target; run bundled registry and demo |
| 5 — first release candidate | 100/100 (superseded) | Lint, formatting, strict typing, 23 tests, 90.54% branch-aware coverage, CLI demo, wheel/sdist build, and installed-wheel smoke passed | Reopen the scientific audit instead of treating an engineering score as scientific completion |
| 6 — deployability audit | 96/100 | Experimental low/high protocol labels were present in the feature contract, and exercise scenarios included rest windows; the committed artifact no longer matched the repaired contract | Collapse inputs to deployable activity families, restrict scenarios to exercise windows, and rerun every real-data prediction |
| 7 — deployable-context release | **100/100** | The new 17-fold artifact contains `activity_family`; raw Apple MAE is 1.651 and ensemble MAE is 1.082 kcal/min; all release gates pass again | Release-ready under rubric v2, with the score explicitly limited to evidence and engineering completeness |

## Scientific comparison

| Metric | Initial compact interval | Final participant-cluster interval |
|---|---:|---:|
| Empirical coverage | 84.59% | **96.42%** |
| Nominal target | 90% | 90% |
| Mean width | 3.926 kcal/min | 5.194 kcal/min |
| Coverage change | — | +11.84 percentage points |
| Width cost | — | +32.30% |

The final deployability repair changed the point model as expected: raw Apple MAE remained 1.651,
while the outer-fold ensemble moved from the superseded 1.074 to 1.082 kcal/min after detailed
experimental intensity labels were removed. The final reduction relative to raw Apple is 34.5%.
The small performance cost is retained rather than hiding information unavailable in real Apple
Health deployment.

## Defects retained as lessons

- Window-level split conformal under-covered because repeated within-person windows are not the
  exchangeable unit for a new-person claim.
- Source category whitespace created fake fairness groups despite correct numeric analysis.
- UTC conversion before daily grouping moved an early-morning HealthKit record to the previous
  date; local calendar dates are now preserved.
- Parallel Extra Trees triggered backend warnings and unacceptable runtime; deterministic
  single-process fitting cut the verified run to about 153 seconds.
- A successful wheel build did not establish installed behavior. The final verifier imports from
  the installed wheel target and exercises bundled data/config resources.
- A privacy scanner initially treated `.mypy_cache/cache.db` as user health data. Cache directories
  are now excluded explicitly while real archives, databases, and `export.xml` remain forbidden.
- A final feature-contract audit found that experimental low/high intensity labels were not
  available from HealthKit. They were collapsed to deployable `rest/cycling/running` families,
  and every real-data metric was rerun instead of carrying forward an optimistic snapshot.
- Fat-loss scenarios initially averaged rest and exercise errors before multiplying by daily
  exercise minutes. The final pipeline restricts this propagation to cycling/running windows.
