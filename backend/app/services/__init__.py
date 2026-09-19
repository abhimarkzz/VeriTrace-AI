"""
Services module for VeriTrace AI.
"""

from app.services.calibration import (
    CalibrationParams,
    CalibrationRegistry,
    calibrate_probabilities,
    calibration_registry,
    compute_brier_score,
    compute_ece,
    fit_temperature,
)
from app.services.confidence import (
    ConfidenceTier,
    calculate_confidence_breakdown,
    determine_confidence_tier,
    generate_confidence_explanation,
)
from app.services.decision_engine import (
    DecisionEngine,
    DecisionInput,
    DecisionOutput,
    decision_engine,
    fuse_decision,
)

__all__ = [
    "CalibrationParams",
    "CalibrationRegistry",
    "calibrate_probabilities",
    "calibration_registry",
    "compute_brier_score",
    "compute_ece",
    "fit_temperature",
    "ConfidenceTier",
    "calculate_confidence_breakdown",
    "determine_confidence_tier",
    "generate_confidence_explanation",
    "DecisionEngine",
    "DecisionInput",
    "DecisionOutput",
    "decision_engine",
    "fuse_decision",
]
