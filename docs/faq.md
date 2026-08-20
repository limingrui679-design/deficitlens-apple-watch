# Frequently asked questions

## Does DeficitLens know my true calorie deficit?

No. It audits measurement error under named protocols and produces sensitivity scenarios. Food
intake, absorption, resting expenditure, adaptation, fluid change, and adherence are not observed.

## Does the Series 8 cohort validate the correction model?

No. It validates a raw-device agreement analysis. The cohort lacks the WEEE feature contract, so
the machine-readable transfer gate blocks a correction-model validation claim.

## Is a 90% conformal interval a personal guarantee?

No. It is an empirical target under exchangeability assumptions. The primary interval treats the
participant as the dependence cluster and still has limited calibration support.

## Does the personal CLI upload Apple Health data?

No network call is made by the parser or report renderer. The default output contains aggregates,
not exact timestamps or normalized rows. Users still need to protect the output directory.

## Why is the project marked Beta?

Internal release gates and public-data evidence are strong, but the correction model lacks a
feature-compatible external cohort and the project has no verified public repository, independent
review, usability study, adoption, or impact evidence.
