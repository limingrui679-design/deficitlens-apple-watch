# Methodology

## Estimand

The primary estimand is the error of an Apple Watch-informed estimate of **active energy rate**
(kcal/min) for a participant unseen during all model fitting and calibration. It is not total
daily energy expenditure and not energy balance.

For participant \(i\), second \(t\), WEEE reports mass-normalized oxygen uptake
\(VO_{2,it}\). With body mass \(w_i\) and a fixed oxygen caloric equivalent \(c=5\) kcal/L:

\[
  EE^{total}_{it} = VO_{2,it}\,w_i\,c / 1000.
\]

The criterion active rate subtracts estimated resting expenditure:

\[
  EE^{active}_{it} = \max(EE^{total}_{it} - RMR_i/1440, 0).
\]

`RMR` uses Mifflin–St Jeor because no directly measured resting value is supplied. Both the
fixed oxygen equivalent and estimated RMR are sensitivity-bearing assumptions.

## Alignment and features

WEEE's central Apple HealthAutoExport JSON contains active-energy increments in kJ and sparse
heart-rate values. Energy is converted using 1 kcal = 4.184 kJ and summed inside 30-second
windows. Missing energy increments are interpreted as zero increments; the observed fraction
is retained as a feature. Heart rate is nearest-time matched within 15 seconds, never filled
with zero, and summarized by mean, standard deviation, range, slope, age-predicted maximum
fraction, and missingness.

Demographics, body composition, workout activity, and signal-quality features are added. The
primary feature set does not use criterion VO₂, Wahoo reference heart rate, protocol MET, or
protocol speed. It also does not use experimental intensity labels: `cycle_low/cycle_high` map
to `cycling`, `run_low/run_high` map to `running`, and sit/stand map to `rest`, matching context
that can be derived from `HKWorkout` or the absence of a workout. Protocol MET appears only as a
labeled non-deployable comparator.

The primary analysis uses non-overlapping 30-second windows. A 5-second stride is generated only
as a data-density sensitivity count. It does not change the unit of independent evidence: the
participant remains the split and bootstrap cluster.

## Timestamp quality control

Protocol phases must be strictly chronological. A missing or non-monotonic phase marker causes
that phase and later phases to be excluded rather than repaired by guesswork. This rule captures
the known P14 post-rest anomaly. Every exclusion reason is stored in dataset evidence.

## Nested validation

For each of 17 outer folds:

1. one participant is the untouched outer test set;
2. a deterministic random subset of the remaining participants is held out for conformal
   calibration;
3. the remaining development participants enter four-fold `GroupKFold` cross-fitting;
4. every base learner produces out-of-fold development predictions;
5. a convex stack minimizes OOF squared error subject to \(w_j\ge0\) and \(\sum_j w_j=1\);
6. base models refit on all development participants;
7. calibration residuals set global and, where adequately supported, activity-specific radii;
8. the outer participant is predicted once.

No window from the outer participant or conformal participants influences fitted model
parameters or stack weights. This design is more conservative than random window splitting and
prevents adjacent-sample leakage.

## Learners and baselines

- `apple_raw`: Watch active energy, unchanged;
- `cohort_affine`: training-only intercept/slope correction of Apple energy;
- `protocol_met_baseline`: transparent protocol-informed physiology comparator, not deployable;
- ridge: scaled linear shrinkage after median/most-frequent imputation;
- Extra Trees: nonlinear interactions with leaf regularization;
- histogram gradient boosting: smooth nonlinear alternative with L2 regularization;
- convex stack: OOF-learned non-negative combination of the three learners.

All predictions are floored at zero. Hyperparameters are fixed before the outer evaluation; no
outer participant is used for model selection.

## Conformal uncertainty

For absolute calibration residuals \(s_1,\dots,s_n\), the compact window-level radius uses ordered rank
\(\lceil(n+1)(1-\alpha)\rceil\), capped at \(n\). At \(\alpha=0.1\), the target is 90% marginal
coverage under exchangeability. An activity-family-specific radius is used only with at least 25
calibration windows; otherwise the global radius is used. The family is the same deployable
`rest/cycling/running` context, not the experimental low/high intensity label.

Repeated windows violate ordinary row exchangeability for the intended new-person use case.
Therefore the **primary cluster-robust interval** first takes the maximum residual within each
calibration participant (and within participant/activity for Mondrian slices), then applies the
same finite-sample conformal rank across participant scores. Activity radii require at least
three calibration participants. This is deliberately wider and targets an unseen participant,
while the compact window interval is retained as a diagnostic. Both coverages and widths are
reported. Small calibration cohorts still mean the nominal rate is a target, not a guarantee for
every subgroup.

## Inference and subgroup analysis

MAE, RMSE, bias, median absolute error, R², Lin's concordance, Bland–Altman limits, and fixed
absolute-error thresholds are reported. MAPE excludes target rates below 0.5 kcal/min and reports
the retained count. Confidence intervals for MAE and bias use 1,000 participant-cluster bootstrap
replicates.

Subgroup tables cover sex, body-fat band, BMI band, and activity. Cells with fewer than three
participants are marked low-support. The project reports disparity gaps and ratios; it does not
perform underpowered null-hypothesis fairness declarations.

## External audit

The 2026 dataset supplies Apple Watch Series 8 and COSMED K5 session totals for a mixed-intensity
recumbent-cycle protocol. It lacks the WEEE feature grid, so it is used to audit raw Watch error,
not to claim model transfer. The primary analysis mirrors the paper code's participant-wide ID 58
exclusion. An all-paired sensitivity analysis restores that participant and reports the change.
MAE and mean-bias intervals use 1,000 participant bootstrap replicates. A machine-readable
transportability gate compares required model inputs, endpoint granularity, and protocol. Because
the external workbook lacks the WEEE heart-rate/window feature contract, the gate returns
`blocked_model_transfer` while still allowing the raw-device agreement audit.

## Decision-impact scenarios

Participant mean rate error across cycling/running windows (never sit/stand windows) is multiplied
by 30, 45, or 60 exercise minutes per active day, 3, 5, or 7 active days per week, and 4/8/12
weeks. Division by 7,000, 7,700, or 9,000 kcal/kg produces a sensitivity grid instead of
privileging one conversion constant. The table preserves participant count and median/10th/90th
percentiles for each model and assumption cell. It intentionally omits intake error, thermic
effect, adaptive thermogenesis, water/glycogen, adherence, and behavior. Therefore it is not a
weight forecast.

## Optional adaptive personalization

`KalmanBiasCalibrator` models slowly drifting Apple-minus-criterion bias. It can predict between
updates, but state updates require an actual paired criterion observation. This prevents the
common circular error of calibrating a wearable against weight change that is itself affected by
unknown intake and fluid shifts.

### How much can the mix of people change a model comparison?

For each held-out participant, take the raw watch MAE minus the corrected model MAE on exactly the same windows. Start with equal weight for each person. A total variation (TV) budget of 0.25 permits redistributing up to one quarter of the probability mass across the observed participants. To find the worst attainable mean gain, move mass from the largest gain to the smallest until the budget runs out. Reversing the order gives the best attainable gain. The same piecewise linear path gives the minimum mass needed to tie the raw watch; an empty tie field means every observed mixture favors the same side.

The archived WEEE predictions (811 windows, 17 people; SHA-256 `e5fa5c9014cd59eed859a47b63cd9a856a617f5ae8060f47a60c5cdfcece9cd1`) give an equal-person ensemble gain of **0.5533 kcal/min**. At TV 0.25, the attainable gain spans **0.2053 to 0.9306 kcal/min**. Breaking even requires moving about 45.29% of the mass. The affine comparator starts at −0.0054 kcal/min and can tie with just 0.29% of the mass moved. This sensitivity analysis conditions on the observed participant errors and excludes sampling uncertainty and new device populations.

The standard WEEE benchmark exports these fields in `tables/model_metrics.csv`. To audit the archived predictions separately:

```python
import pandas as pd
from deficitlens.evaluation.mixture import participant_mix_sensitivity

rows = pd.read_csv("artifacts/verified/tables/loso_predictions.csv")
print(participant_mix_sensitivity(rows.y_true, rows.ensemble, rows.apple_raw, rows.participant_id))
```
