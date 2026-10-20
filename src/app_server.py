"""Flask API and static frontend for the CardioVision academic demo."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from flask import Flask, jsonify, render_template, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "result" / "best_gb_model.joblib"
SCALER_PATH = PROJECT_ROOT / "result" / "best_gb_scaler.joblib"
FEATURE_NAMES = ["age_years", "sex", "chol", "glucose/fbs", "MAP", "smoke"]
INPUT_RANGES = {
    "age_years": (20, 100),
    "sex": (0, 1),
    "sysBP": (90, 200),
    "diaBP": (60, 130),
    "chol": (1, 3),
    "glucose": (1, 3),
    "smoke": (0, 1),
}

app = Flask(
    __name__,
    template_folder=str(Path(__file__).resolve().parent / "templates"),
    static_folder=str(Path(__file__).resolve().parent / "static"),
)


def load_model_artifacts() -> tuple[Any, Any]:
    """Load the exported model and scaler, or raise a clear startup error."""
    missing = [path for path in (MODEL_PATH, SCALER_PATH) if not path.is_file()]
    if missing:
        missing_paths = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(
            f"Required model artifact(s) missing: {missing_paths}. "
            "From the project root run: python src/export_model.py"
        )
    return joblib.load(MODEL_PATH), joblib.load(SCALER_PATH)


MODEL, SCALER = load_model_artifacts()


def validate_payload(payload: Any) -> tuple[dict[str, float] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object."

    values: dict[str, float] = {}
    for name, (minimum, maximum) in INPUT_RANGES.items():
        if name not in payload:
            return None, f"Missing required field: {name}."
        value = payload[name]
        if isinstance(value, bool):
            return None, f"{name} must be a number, not a boolean."
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None, f"{name} must be a number."
        if not math.isfinite(number):
            return None, f"{name} must be finite."
        if not minimum <= number <= maximum:
            return None, f"{name} must be between {minimum} and {maximum}."
        if not number.is_integer():
            return None, f"{name} must be an integer value."
        values[name] = number

    if values["diaBP"] >= values["sysBP"]:
        return None, "Diastolic pressure must be lower than systolic pressure."
    return values, None


def risk_category(probability: float) -> tuple[str, str]:
    if probability < 0.10:
        return "Low", "Continue routine preventive care and monitoring."
    if probability < 0.20:
        return "Moderate", "Review the overall risk profile with a healthcare professional."
    if probability <= 0.30:
        return "High", "Consider timely clinical review of cardiovascular risk factors."
    return "Critical", "Prompt professional assessment is appropriate; this estimate is not a diagnosis."


def clinical_advice(map_value: float, systolic: float, diastolic: float, tier: str) -> str:
    if systolic >= 180 or diastolic >= 120:
        return "Blood pressure is markedly elevated; seek prompt professional assessment."
    if tier == "Critical":
        return "Discuss this risk estimate promptly with a qualified healthcare professional."
    if map_value > 100:
        return "Monitor blood pressure closely and discuss the reading with a healthcare professional."
    if map_value < 70:
        return "MAP is on the lower side; interpret with symptoms and seek clinical advice if concerned."
    if tier == "High":
        return "Consider timely clinical review and ongoing monitoring of cardiovascular risk factors."
    if tier == "Moderate":
        return "Review preventive health goals and maintain regular follow-up."
    return "Continue routine preventive care and periodic blood-pressure monitoring."


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/predict")
def predict():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json."}), 415
    values, error = validate_payload(request.get_json(silent=True))
    if error:
        return jsonify({"error": error}), 400

    assert values is not None
    map_value = values["diaBP"] + (values["sysBP"] - values["diaBP"]) / 3.0
    feature_row = pd.DataFrame(
        [
            {
                "age_years": values["age_years"],
                "sex": values["sex"],
                "chol": values["chol"],
                "glucose/fbs": values["glucose"],
                "MAP": map_value,
                "smoke": values["smoke"],
            }
        ],
        columns=FEATURE_NAMES,
    )
    scaled_features = SCALER.transform(feature_row)
    probability = float(MODEL.predict_proba(scaled_features)[0, 1])
    tier, tier_description = risk_category(probability)
    advice = clinical_advice(map_value, values["sysBP"], values["diaBP"], tier)
    return jsonify(
        {
            "probability": probability,
            "probability_percent": round(probability * 100, 2),
            "risk_tier": tier,
            "tier_description": tier_description,
            "map_value": round(map_value, 1),
            "clinical_advice": advice,
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
