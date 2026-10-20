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
                    "risk_probability": record.risk_probability,
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
    advice = clinical_advice(map_value, values["sysBP"], values["diaBP"], tier)
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
