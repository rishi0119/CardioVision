"""Train and export the CardioVision Cardio Train Gradient Boosting model."""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "cardio_train.csv"
RESULT_DIR = PROJECT_ROOT / "result"
MODEL_PATH = RESULT_DIR / "best_gb_model.joblib"
SCALER_PATH = RESULT_DIR / "best_gb_scaler.joblib"
FEATURE_NAMES = ["age_years", "sex", "chol", "glucose/fbs", "MAP", "smoke"]
TARGET = "cardio"


def main() -> None:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Cardio Train dataset not found: {DATA_PATH}")

    cardio = pd.read_csv(DATA_PATH, sep=";")
    valid_bp = cardio["ap_hi"].between(50, 240, inclusive="both") & cardio[
        "ap_lo"
    ].between(30, 150, inclusive="both")
    cardio = cardio.loc[valid_bp].copy()

    training_features = pd.DataFrame(
        {
            "age_years": (cardio["age"] / 365.25).astype(int),
            "sex": (cardio["gender"] == 2).astype(int),
            "chol": cardio["cholesterol"],
            "glucose/fbs": cardio["gluc"],
            "MAP": cardio["ap_lo"] + (cardio["ap_hi"] - cardio["ap_lo"]) / 3,
            "smoke": cardio["smoke"],
        },
        index=cardio.index,
    )[FEATURE_NAMES]
    target = cardio[TARGET].astype(int)

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(training_features)
    model = GradientBoostingClassifier(random_state=42)
    model.fit(scaled_features, target)

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    print(f"Training rows after blood-pressure filtering: {len(cardio):,}")
    print(f"Feature order: {FEATURE_NAMES}")
    print(f"Model saved to: {MODEL_PATH}")
    print(f"Scaler saved to: {SCALER_PATH}")


if __name__ == "__main__":
    main()
