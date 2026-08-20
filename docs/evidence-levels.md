# Evidence levels

DeficitLens uses explicit evidence states so a polished interface cannot silently upgrade a
claim.

| State | What exists | What may be said |
|---|---|---|
| `observed_benchmark` | Registered data, held-out predictions, uncertainty, and hashed outputs | Report the named benchmark population, protocol, metric, and interval |
| `observed_external_audit` | Independent cohort for the measured device endpoint | Report raw-device agreement; model transfer only if its full feature contract is present |
| `private_local_workflow` | Code and synthetic demo for user-owned data | Describe functionality and privacy defaults; do not claim real users or outcomes |
| `modeled_scenario` | Arithmetic outputs under enumerated assumptions | Compare sensitivity; do not call it a forecast, causal effect, or recommendation |
| external validation | Independent data that satisfy the model's inputs, endpoint, and protocol contract | Not currently available for the correction model |
| adoption or impact | Verifiable use records and an appropriate evaluation design | Not currently available |

[`evidence/external-evidence.json`](../evidence/external-evidence.json) records external counts,
including zeros. The release score covers only maintainer-controllable evidence and engineering
gates. It does not award points for unobserved reviews, users, stars, adoption, or impact.
The same ledger is included in installed wheels and available through `deficitlens evidence
--json`; the resource-sync gate prevents the checkout and package copies from drifting.
