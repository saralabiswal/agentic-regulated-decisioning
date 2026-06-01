# Author: Sarala Biswal
"""Deterministic mock records shared by MCP servers."""

from __future__ import annotations

from typing import Any

FIXTURES: dict[str, dict[str, dict[str, Any]]] = {
    "insurance": {
        "ins_cp_ca_001": {
            "core": {
                "entity_id": "ins_cp_ca_001",
                "case_type": "commercial_property",
                "case_value": 4_200_000,
                "tiv": 4_200_000,
                "construction_type": "masonry",
                "year_built": 1987,
                "occupancy": "office",
                "protection_class": 3,
            },
            "history": {
                "losses": [{"amount": 12_000}, {"amount": 8_500}],
                "frequency_5y": 2,
                "severity_trend": "stable",
            },
            "external": {
                "bureau_rating": "B+",
                "cat_zone": 3,
                "appetite": {
                    "PREFERRED": 5_000_000,
                    "STANDARD": 2_000_000,
                    "SUBSTANDARD": 1_000_000,
                },
            },
        },
        "ins_cp_tx_002": {
            "core": {
                "entity_id": "ins_cp_tx_002",
                "case_type": "commercial_property",
                "case_value": 8_500_000,
                "tiv": 8_500_000,
                "construction_type": "metal_frame",
                "year_built": 2003,
                "occupancy": "warehouse",
                "protection_class": 7,
                "credit_score": 710,
            },
            "history": {
                "losses": [{"amount": 950_000}],
                "frequency_5y": 1,
                "severity_trend": "large_fire",
            },
            "external": {
                "bureau_rating": "C",
                "cat_zone": 4,
                "appetite": {
                    "PREFERRED": 5_000_000,
                    "STANDARD": 2_000_000,
                    "SUBSTANDARD": 1_000_000,
                },
            },
        },
        "ins_pa_ca_003": {
            "core": {
                "entity_id": "ins_pa_ca_003",
                "case_type": "personal_auto",
                "case_value": 38_000,
                "vehicle_year": 2022,
                "licensed_years": 3,
                "violations": 0,
            },
            "history": {"losses": [], "frequency_5y": 0, "severity_trend": "none"},
            "external": {
                "bureau_rating": "A",
                "cat_zone": 1,
                "appetite": {
                    "PREFERRED": 5_000_000,
                    "STANDARD": 2_000_000,
                    "SUBSTANDARD": 1_000_000,
                },
            },
        },
    },
    "lending": {
        "lend_auto_tx_001": {
            "core": {
                "entity_id": "lend_auto_tx_001",
                "case_type": "auto_loan",
                "case_value": 42_000,
                "income": 85_000,
                "dti": 0.28,
            },
            "history": {"payments": "clean"},
            "external": {"bureau_score": 748},
        },
        "lend_mort_ny_002": {
            "core": {
                "entity_id": "lend_mort_ny_002",
                "case_type": "mortgage",
                "case_value": 640_000,
                "income": 145_000,
                "dti": 0.42,
                "employment": "self_employed",
            },
            "history": {"payments": "thin_file"},
            "external": {"bureau_score": 690},
        },
        "lend_pl_fl_003": {
            "core": {
                "entity_id": "lend_pl_fl_003",
                "case_type": "personal_loan",
                "case_value": 12_000,
                "income": 62_000,
                "thin_file": True,
            },
            "history": {"payments": "on_time"},
            "external": {"bureau_score": 704},
        },
    },
    "healthcare": {
        "hc_mri_ca_001": {
            "core": {
                "entity_id": "hc_mri_ca_001",
                "case_type": "prior_auth",
                "case_value": 2800,
                "procedure": "MRI lumbar",
                "conservative_treatment": True,
            },
            "history": {"prior_auths": []},
            "external": {"criteria_met": True, "criteria": "ClinicalCriteriaEngine"},
        },
        "hc_ref_tx_002": {
            "core": {
                "entity_id": "hc_ref_tx_002",
                "case_type": "specialty_referral",
                "case_value": 900,
                "complexity": "multi_system",
                "notes_complete": False,
            },
            "history": {"prior_auths": ["specialist"]},
            "external": {"criteria_met": False, "missing": "clinical_notes"},
        },
        "hc_surg_ny_003": {
            "core": {
                "entity_id": "hc_surg_ny_003",
                "case_type": "elective_surgery",
                "case_value": 38000,
                "procedure": "knee replacement",
                "cpt": "27447",
            },
            "history": {"prior_auths": []},
            "external": {"criteria_met": True, "criteria": "ClinicalCriteriaEngine"},
        },
    },
    "wealth": {
        "wealth_eq_ca_001": {
            "core": {
                "entity_id": "wealth_eq_ca_001",
                "case_type": "suitability_check",
                "case_value": 500_000,
                "age": 45,
                "risk_profile": "moderate",
                "horizon_years": 20,
            },
            "history": {"transactions": "diversified"},
            "external": {"product_risk": "moderate"},
        },
        "wealth_opt_fl_002": {
            "core": {
                "entity_id": "wealth_opt_fl_002",
                "case_type": "options_authorization",
                "case_value": 200_000,
                "age": 68,
                "risk_profile": "conservative",
                "account_type": "retirement",
            },
            "history": {"transactions": "limited"},
            "external": {"product_risk": "high"},
        },
        "wealth_ann_tx_003": {
            "core": {
                "entity_id": "wealth_ann_tx_003",
                "case_type": "annuity_recommendation",
                "case_value": 300_000,
                "age": 55,
                "objective": "guaranteed_income",
            },
            "history": {"transactions": "income_focus"},
            "external": {"product_risk": "low"},
        },
    },
}


def get_fixture(domain: str, entity_id: str) -> dict[str, Any]:
    """Return deterministic fixture data for a domain entity."""
    return FIXTURES[domain][entity_id]
