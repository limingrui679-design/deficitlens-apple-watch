# Model card: DeficitLens Apple Watch calibrator

## Intended use

Research, portfolio demonstration, wearable-measurement auditing, and hypothesis generation about
Apple Watch active-energy error during structured activity. The model may help decide whether a
raw wearable field is precise enough for an aggregate planning use case.

## Out-of-scope use

- clinical diagnosis, treatment, eating-disorder management, or medication decisions;
- prescribing an individual's calorie intake or target weight;
- claiming exact calorie burn, total daily energy expenditure, or energy balance;
- deployment to children, pregnancy, disease populations, or activities absent from validation;
- using the WEEE model as validated for Series 8 solely because a separate Series 8 raw-device
  audit is included;
- inferring protected-trait fairness not measured in the relevant dataset.

## Inputs and output

Inputs are Apple active-energy rate, Watch heart-rate distribution/quality features, deployable
activity family (`rest`, `cycling`, or `running`), age, sex category required by the source RMR
equation, weight, height, BMI, body-fat percentage, and estimated RMR. Output is active kcal/min
plus a cluster-robust split-conformal
interval targeting 90% coverage for held-out-participant windows. A narrower row-calibrated
interval is diagnostic only because repeated windows are not independent.

The low/high experimental intensity label, protocol MET, and protocol speed are not model inputs.
The external 2026 audit does not receive model predictions.

## Training and evaluation

Training uses WEEE with 17 participants. Every reported model prediction comes from an outer
leave-one-subject-out fold. Within each outer fold, participant-disjoint development and
conformal-calibration sets are created. Stack weights are learned from inner group-cross-fitted
predictions.

See the verified report for current numerical results and `fold_diagnostics.json` for every
split, stack weight, calibration radius, and sample count.

## Ethical and fairness considerations

Wearable sensor error can differ with physiology, body composition, motion, fit, firmware, and
skin tone. WEEE does not include Fitzpatrick skin tone, so no WEEE skin-tone claim is made. The
2026 cohort's raw Series 8 errors are sliced by released skin-type/body-composition fields and
kept separate from model performance. Small cells are flagged rather than silently pooled.

Binary source sex fields are used only because Mifflin–St Jeor requires one of two constants;
this is a limitation of the equation and source data, not a claim about gender identity.

## Failure modes

- sparse Watch heart rate causes imputation and wider epistemic uncertainty not fully captured by
  split conformal intervals;
- unseen workouts, device generations, firmware, tattoos, poor fit, or motion artifacts may shift
  the error distribution;
- active-energy increments can be delayed or batched by HealthKit;
- criterion alignment inherits the fixed oxygen-equivalent and estimated-RMR assumptions;
- conformal marginal coverage can under-cover a specific participant or small subgroup;
- participant-level calibration data are expensive and may not resemble everyday workouts.

## Monitoring and retirement

Any downstream deployment should log device/OS versions, missingness, activity mix, interval
coverage when criterion sessions are available, and subgroup support. Revalidate after major
watchOS/device changes. Retire the model if participant-clustered MAE or interval coverage crosses
predeclared thresholds; this repository does not set clinical thresholds.
