# Case paths

The same analytics system is exposed through four complementary, machine-readable paths. Their
purpose is to show different decisions and failure boundaries, not to relabel one benchmark four
times.

| Case | Primary decision | Evidence state | Distinct capability |
|---|---|---|---|
| Series 6 criterion benchmark | Is a correction supported for an unseen participant in this protocol? | Observed benchmark | Leakage-safe model validation and clustered inference |
| Series 8 device-agreement audit | Does raw device energy agree with a criterion system in another cohort? | Observed external audit | Agreement, subgroup support, and transfer refusal |
| Local Apple Health audit | What can be summarized without uploading or writing row-level records? | Private local workflow | Privacy-preserving health-data engineering |
| Exercise-energy sensitivity | When could persistent error change a planning calculation? | Modeled scenario | Multi-assumption decision analysis |

Run `deficitlens cases` or `deficitlens cases --json` to inspect the validated catalog. The source
of truth is [`cases/catalog.yml`](../cases/catalog.yml); the release gate checks that the wheel copy
is identical and every referenced output exists after the verified pipeline runs.
