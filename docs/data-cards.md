# Data cards

## WEEE

- **Role:** primary model development and participant-held-out evaluation.
- **Version:** Zenodo record 6420886, published 2022.
- **Participants:** 17.
- **Apple device:** Apple Watch Series 6.
- **Criterion:** VO₂ from indirect calorimetry; VCO₂ is not present in the released average files.
- **Activities:** sitting, standing, two cycling intensities, two running intensities.
- **Granularity used:** second-level criterion and Watch energy; 30-second analysis windows.
- **License:** CC BY 4.0.
- **Integrity:** `md5:23e411c566f1c734e74e23fa76bd1ab0`, 651,557,047 bytes.
- **Known issue handled:** participant P14 has a non-monotonic post-rest protocol marker; the
  affected and later phases are excluded without imputation.
- **Limits:** controlled protocol, small cohort, Series 6, estimated active criterion.
- **Source:** <https://doi.org/10.5281/zenodo.6420886>.

## Apple Watch PAEE 2026

- **Role:** independent raw-device agreement and body-composition subgroup audit.
- **Participants:** 58 enrolled; 55 Apple values; 53 paired Apple–COSMED values; 52 in the
  paper-mirrored primary paired analysis after participant ID 58's global exclusion.
- **Population:** Hispanic adults; Fitzpatrick types represented in the released workbook are
  reported, not extrapolated.
- **Apple device:** Apple Watch Series 8.
- **Criterion:** COSMED K5 session energy.
- **Protocol:** mixed-intensity recumbent cycling.
- **License:** CC BY 4.0 as stated with the OSF project/article materials.
- **Integrity:** `sha256:7a9efa3df497f49d2fbace434f0e2a4987b61208933465de03560f255970a717`.
- **Limits:** session totals only; cannot execute WEEE feature model transfer.
- **Sources:** <https://osf.io/e745u/> and <https://doi.org/10.1371/journal.pone.0353261>.

## BigIdeasLab_STEP (optional, not used)

- **Role:** potential future Apple Watch 4 heart-rate/skin-tone validation.
- **Participants:** 53.
- **Access:** restricted; a PhysioNet account and signed data-use agreement are required.
- **License:** PhysioNet Restricted Health Data License 1.5.0.
- **Reason excluded from this release:** DeficitLens does not bypass access controls or imply that
  inaccessible files were validated.
- **Source:** <https://physionet.org/content/bigideaslab-step-hr-smartwatch/1.0/>.

## User Apple Health export

- **Role:** local descriptive audit only.
- **Ownership:** private user health data.
- **Committed:** never by default; `export.xml`, `.zip`, and raw normalized rows are gitignored.
- **Default output:** daily/workout aggregates, sensitivity scenarios, and a self-contained local
  report without exact timestamps, record IDs, source strings, or device identifiers.
- **Deletion:** the user controls input and output paths; DeficitLens does not upload them.
