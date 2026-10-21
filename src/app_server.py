"""Flask API and static frontend for the CardioVision academic demo."""

from __future__ import annotations

import math
import os
import secrets
from datetime import timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_user, logout_user
from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from models import PredictionHistory, User, db


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTANCE_DIR = PROJECT_ROOT / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
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
database_url = os.environ.get("CARDIOVISION_DATABASE_URL")
if not database_url:
    database_url = f"sqlite:///{(INSTANCE_DIR / 'cardiovision.db').as_posix()}"

secret_key = os.environ.get("SECRET_KEY")
if os.environ.get("RENDER", "").lower() == "true" and not secret_key:
    raise RuntimeError("Set the SECRET_KEY environment variable in Render before starting CardioVision.")

app.config.update(
    SECRET_KEY=secret_key or secrets.token_hex(32),
    SQLALCHEMY_DATABASE_URI=database_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("RENDER", "").lower() == "true",
)
db.init_app(app)
login_manager = LoginManager(app)
csrf = CSRFProtect(app)


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    try:
        return db.session.get(User, int(user_id))
    except ValueError:
        return None


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify({"error": "authentication_required"}), 401
    return redirect(url_for("index"))


@app.errorhandler(CSRFError)
def handle_csrf_error(error: CSRFError):
    if request.path.startswith("/api/"):
        return jsonify({"error": "csrf_failed", "message": error.description}), 400
    return error.description, 400


with app.app_context():
    db.create_all()


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


def clinical_analysis(values: dict[str, float], map_value: float, tier: str) -> dict[str, Any]:
    if map_value > 110:
        map_status = "markedly_elevated"
    elif map_value > 100:
        map_status = "elevated"
    elif map_value < 70:
        map_status = "below_reference"
    else:
        map_status = "within_reference"

    cholesterol_status = {1: "normal", 2: "elevated", 3: "high"}[int(values["chol"])]
    glucose_status = {1: "normal", 2: "elevated", 3: "high"}[int(values["glucose"])]
    factor_assessments: list[dict[str, Any]] = [
        {
            "code": "blood_pressure",
            "assessment_code": map_status,
            "sys_bp": int(values["sysBP"]),
            "dia_bp": int(values["diaBP"]),
            "map_value": round(map_value, 1),
        },
        {
            "code": "age",
            "assessment_code": "over_50" if values["age_years"] > 50 else "50_or_under",
            "value": int(values["age_years"]),
        },
        {"code": "cholesterol", "assessment_code": cholesterol_status},
        {"code": "glucose", "assessment_code": glucose_status},
        {
            "code": "smoking",
            "assessment_code": "current" if values["smoke"] == 1 else "not_smoking",
        },
    ]

    if map_status in {"markedly_elevated", "elevated", "below_reference"}:
        primary_driver = factor_assessments[0]
    elif cholesterol_status != "normal":
        primary_driver = factor_assessments[2]
    elif values["age_years"] > 50:
        primary_driver = factor_assessments[1]
    else:
        primary_driver = factor_assessments[0]

    if values["sysBP"] >= 180 or values["diaBP"] >= 120:
        recommendation_code = "urgent_pressure"
    else:
        recommendation_code = f"tier_{tier.lower()}"
    recommendation_codes = [recommendation_code]
    if map_status in {"markedly_elevated", "elevated", "below_reference"}:
        recommendation_codes.append("review_pressure")
    if values["chol"] > 1:
        recommendation_codes.append("review_cholesterol")
    if values["glucose"] > 1:
        recommendation_codes.append("review_glucose")
    if values["smoke"] == 1:
        recommendation_codes.append("smoking_support")

    recommendations = {
        "urgent_pressure": "Seek prompt professional assessment for the markedly elevated blood-pressure reading.",
        "tier_critical": "Discuss this model estimate promptly with a qualified healthcare professional; it is not a diagnosis.",
        "tier_high": "Arrange timely clinical review of cardiovascular risk factors and monitoring.",
        "tier_moderate": "Review preventive health goals and arrange regular follow-up with a healthcare professional.",
        "tier_low": "Continue routine preventive care and periodic monitoring.",
        "review_pressure": "Repeat blood-pressure readings under appropriate conditions and review them with a clinician.",
        "review_cholesterol": "Discuss cholesterol assessment and management with a healthcare professional.",
        "review_glucose": "Discuss glucose assessment and any needed follow-up with a healthcare professional.",
        "smoking_support": "If you smoke, ask a healthcare professional about evidence-based support to quit.",
    }
    summary_code = f"patient_summary_{tier.lower()}"
    patient_explanation = [
        f"The app places this result in the {tier} category.",
        (
            f"Your blood pressure is {int(values['sysBP'])}/{int(values['diaBP'])} mmHg. "
            f"The average of these readings is {map_value:.1f} mmHg."
        ),
        "The app compares all your answers together. It cannot tell that one answer caused this result.",
    ]
    if map_status in {"markedly_elevated", "elevated"}:
        patient_explanation.append(
            "This average reading is above the usual range shown in the app and is worth discussing with a health professional."
        )
    elif map_status == "below_reference":
        patient_explanation.append(
            "This average reading is below the usual range shown in the app; discuss it with a health professional if you have symptoms or concerns."
        )
    elif tier in {"Low", "Moderate"}:
        patient_explanation.append(
            "Your blood pressure reading is within the usual range shown here."
        )
    cholesterol_explanations = {
        "normal": "The cholesterol category you selected is below 200 mg/dL.",
        "elevated": "The cholesterol category you selected is 200–239 mg/dL.",
        "high": "The cholesterol category you selected is 240 mg/dL or higher.",
    }
    patient_explanation.append(
        cholesterol_explanations[cholesterol_status]
        + " This is a selected range, not a measured lab result."
    )
    if values["age_years"] > 50:
        patient_explanation.append(
            f"Your age ({int(values['age_years'])}) is also included in the estimate."
        )
    glucose_explanations = {
        "normal": "The fasting glucose range you selected is below 100 mg/dL (normal range).",
        "elevated": "The fasting glucose range you selected is 100–125 mg/dL (prediabetes range).",
        "high": "The fasting glucose range you selected is at or above 126 mg/dL (diabetes range).",
    }
    patient_explanation.append(
        glucose_explanations[glucose_status]
        + " This is a selected category, not a measured lab result or a diagnosis; a healthcare professional can interpret an actual fasting glucose test."
    )
    if values["smoke"] == 1:
        patient_explanation.append("You also indicated that you currently smoke.")
    patient_explanation_text = " ".join(patient_explanation)
    return {
        "primary_driver": primary_driver,
        "contributing_factors": factor_assessments,
        "patient_explanation": patient_explanation_text,
        "patient_explanation_code": summary_code,
        "model_explanation": "This is an estimate from the answers you entered, not a diagnosis. The app cannot identify one exact cause for an individual result.",
        "recommendation_code": recommendation_code,
        "recommendation_codes": recommendation_codes,
        "actionable_recommendation": " ".join(recommendations[code] for code in recommendation_codes),
    }


@app.get("/")
def index():
    return render_template("index.html")


def api_payload() -> dict[str, Any] | None:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else None


def public_user(user: User) -> dict[str, Any]:
    return {"id": user.id, "username": user.username, "email": user.email}


@app.post("/api/register")
def register():
    payload = api_payload()
    if payload is None:
        return jsonify({"error": "Request body must be a JSON object."}), 400

    username = payload.get("username")
    email = payload.get("email")
    password = payload.get("password")
    if not all(isinstance(value, str) for value in (username, email, password)):
        return jsonify({"error": "Username, email, and password are required."}), 400

    username = username.strip()
    email = email.strip().lower()
    if not 2 <= len(username) <= 80:
        return jsonify({"error": "Username must be between 2 and 80 characters."}), 400
    if len(email) > 254 or "@" not in email or any(character.isspace() for character in email):
        return jsonify({"error": "Enter a valid email address."}), 400
    if not 8 <= len(password) <= 128:
        return jsonify({"error": "Password must be between 8 and 128 characters."}), 400

    existing_user = db.session.execute(
        select(User).where((User.username == username) | (User.email == email))
    ).scalar_one_or_none()
    if existing_user:
        return jsonify({"error": "Username or email is already registered."}), 409

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({"user": public_user(user)}), 201


@app.post("/api/login")
def login():
    payload = api_payload()
    if payload is None:
        return jsonify({"error": "Request body must be a JSON object."}), 400
    email = payload.get("email")
    password = payload.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"error": "Email and password are required."}), 400

    user = db.session.execute(
        select(User).where(User.email == email.strip().lower())
    ).scalar_one_or_none()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password."}), 401
    login_user(user)
    return jsonify({"user": public_user(user)})


@app.post("/api/logout")
def logout():
    logout_user()
    return jsonify({"authenticated": False})


@app.get("/api/user")
def get_current_user():
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False})
    return jsonify({"authenticated": True, "user": public_user(current_user)})


@app.get("/api/history")
def get_history():
    if not current_user.is_authenticated:
        return jsonify({"error": "authentication_required"}), 401
    records = db.session.execute(
        select(PredictionHistory)
        .where(PredictionHistory.user_id == current_user.id)
        .order_by(PredictionHistory.created_at.desc())
        .limit(100)
    ).scalars()
    return jsonify(
        {
            "history": [
                {
                    "id": record.id,
                    "age": record.age,
                    "sex": record.sex,
                    "sys_bp": record.sys_bp,
                    "dia_bp": record.dia_bp,
                    "map_val": record.map_val,
                    "chol": record.chol,
                    "glucose": record.glucose,
                    "smoke": record.smoke,
                    "risk_tier": record.risk_tier,
                    "created_at": (
                        record.created_at.replace(tzinfo=timezone.utc)
                        if record.created_at.tzinfo is None
                        else record.created_at
                    )
                    .isoformat()
                    .replace("+00:00", "Z"),
                }
                for record in records
            ]
        }
    )


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
    analysis = clinical_analysis(values, map_value, tier)
    if current_user.is_authenticated:
        db.session.add(
            PredictionHistory(
                user_id=current_user.id,
                age=int(values["age_years"]),
                sex=int(values["sex"]),
                sys_bp=int(values["sysBP"]),
                dia_bp=int(values["diaBP"]),
                map_val=map_value,
                chol=int(values["chol"]),
                glucose=int(values["glucose"]),
                smoke=int(values["smoke"]),
                risk_probability=probability,
                risk_tier=tier,
            )
        )
        db.session.commit()
    return jsonify(
        {
            "risk_tier": tier,
            "tier_description": tier_description,
            "map_value": round(map_value, 1),
            **analysis,
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
