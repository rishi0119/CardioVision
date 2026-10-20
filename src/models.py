"""SQLAlchemy models for CardioVision user accounts and prediction history."""

from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    predictions = db.relationship(
        "PredictionHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="PredictionHistory.created_at.desc()",
    )


class PredictionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    age = db.Column(db.Integer, nullable=False)
    sex = db.Column(db.Integer, nullable=False)
    sys_bp = db.Column(db.Integer, nullable=False)
    dia_bp = db.Column(db.Integer, nullable=False)
    map_val = db.Column(db.Float, nullable=False)
    chol = db.Column(db.Integer, nullable=False)
    glucose = db.Column(db.Integer, nullable=False)
    smoke = db.Column(db.Integer, nullable=False)
    risk_probability = db.Column(db.Float, nullable=False)
    risk_tier = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="predictions")
