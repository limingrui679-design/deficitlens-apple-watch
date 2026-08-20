"""Machine-enforced gate for claims about cross-cohort model transfer."""

from __future__ import annotations

from collections.abc import Collection

from deficitlens.schemas import APPLE_ONLY_NUMERIC_FEATURES, CATEGORICAL_FEATURES


def build_transferability_gate(available_columns: Collection[str]) -> dict[str, object]:
    """Return a transparent pass/block decision for WEEE-model transfer.

    The Series 8 cohort contains paired session totals but not the 30-second Watch/heart-rate
    feature grid used by the WEEE model. The gate converts that limitation from prose into a
    machine-readable failed requirement, so a report cannot silently promote the external
    raw-device audit into external validation of the correction model.
    """

    required_features = [*APPLE_ONLY_NUMERIC_FEATURES, *CATEGORICAL_FEATURES]
    available = sorted(set(available_columns))
    missing_features = sorted(set(required_features) - set(available))
    checks = [
        {
            "check_id": "independent_participants",
            "passed": True,
            "evidence": "The Series 8 participants are independent of the WEEE cohort.",
        },
        {
            "check_id": "feature_contract_complete",
            "passed": not missing_features,
            "evidence": f"{len(missing_features)} required model features are unavailable.",
        },
        {
            "check_id": "endpoint_granularity_aligned",
            "passed": False,
            "evidence": "External data contain session totals; the model predicts 30-second rates.",
        },
        {
            "check_id": "protocol_domain_aligned",
            "passed": False,
            "evidence": "External testing is mixed-intensity recumbent cycling, not the full WEEE protocol.",
        },
    ]
    passed = all(bool(check["passed"]) for check in checks)
    return {
        "schema_version": 1,
        "status": "eligible_for_model_transfer" if passed else "blocked_model_transfer",
        "passed": passed,
        "source_model_cohort": "weee_series6",
        "target_audit_cohort": "apple_watch_paee_2026_series8",
        "required_feature_contract": required_features,
        "available_external_columns": available,
        "missing_required_features": missing_features,
        "checks": checks,
        "allowed_claim": "Independent raw-device agreement audit against COSMED K5.",
        "prohibited_claim": "External validation or deployment calibration of the WEEE-trained ensemble.",
        "next_evidence_required": (
            "An independent cohort with the full time-aligned Watch feature contract, criterion "
            "active-energy rate, protocol metadata, and participant-level evaluation."
        ),
    }
