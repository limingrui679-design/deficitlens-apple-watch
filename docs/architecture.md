# Architecture and extension points

Data adapters return normalized pandas frames plus immutable `DatasetEvidence`. Models know
nothing about file formats. Evaluation consumes a feature-contract frame. Reporting consumes
only evaluation outputs. This separation makes it possible to add a new device or criterion set
without rewriting validation logic.

The public case catalog sits above these layers: it maps a user decision to datasets, methods,
outputs, capabilities, evidence state, and a claim boundary. It contains no school-specific or
audience-specific labels. The report renders only validated catalog entries. A separate external-
evidence ledger prevents internal release checks from being counted as review, adoption, or
impact.

## Add a dataset

1. register version, URL, license, access, expected hash, and analytical role;
2. implement an adapter that raises on missing required columns or unit ambiguity;
3. return `DatasetEvidence` with row/participant/activity counts and exclusion notes;
4. add unit and checksum tests;
5. state whether it supports development, transfer validation, or only independent auditing.

If an independent dataset lacks any required input, endpoint, or protocol element, add or update a
transportability gate. Do not silently skip model predictions while leaving transfer language
ambiguous.

## Add a model

Add its constructor to `models/ensemble.py`, preserve deterministic seeds, and ensure all
preprocessing lives inside the pipeline. Stack weights must still be learned from participant-
grouped out-of-fold predictions. A model is not promoted because it is novel; it must improve an
outer-fold or decision-relevant metric without breaking uncertainty/subgroup behavior.

## Add an Apple Health field

Whitelist the HealthKit type, define unit semantics, add a privacy review, and test duplicate,
timezone, source-filter, entity-expansion, and malformed-value behavior. Do not write raw rows from
the public CLI. An expert row writer must require explicit sensitive-output acknowledgement.
