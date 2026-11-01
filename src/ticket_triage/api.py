import hashlib
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import joblib
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ticket_triage.store import connect, initialize


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=5, max_length=4000)

    @field_validator("text")
    @classmethod
    def meaningful_text(cls, value: str):
        if sum(character.isalpha() for character in value) < 3:
            raise ValueError("O chamado deve conter ao menos três letras")
        return value


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    correct_label: Literal["acesso", "cancelamento", "cobranca", "erro_tecnico"]


def create_app(model_path: Path | None = None, db_path: Path | None = None) -> FastAPI:
    model_path = Path(model_path or os.getenv("TICKET_MODEL_PATH", "var/model.joblib"))
    db_path = Path(db_path or os.getenv("TICKET_DB_PATH", "var/history.sqlite3"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialize(db_path)
        app.state.model = joblib.load(model_path) if model_path.is_file() else None
        yield

    app = FastAPI(title="Ticket Triage", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    def health():
        ready = app.state.model is not None
        return JSONResponse({"status": "ok" if ready else "model_missing"}, status_code=200 if ready else 503)

    @app.post("/predict")
    def predict(payload: PredictRequest):
        bundle = app.state.model
        if bundle is None:
            raise HTTPException(503, "Treine o modelo antes de iniciar a API")
        pipeline = bundle["pipeline"]
        scores = pipeline.predict_proba([payload.text])[0]
        labels = pipeline.classes_
        best = int(scores.argmax())
        identifier = str(uuid.uuid4())
        with connect(db_path) as connection:
            connection.execute(
                "INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?)",
                (identifier, datetime.now(timezone.utc).isoformat(), hashlib.sha256(payload.text.encode()).hexdigest(),
                 str(labels[best]), float(scores[best]), bundle["model_version"]),
            )
        return {"prediction_id": identifier, "label": str(labels[best]), "score": float(scores[best]),
                "scores": {str(label): float(score) for label, score in zip(labels, scores)},
                "model_version": bundle["model_version"],
                "score_note": "Score do classificador não calibrado; não representa garantia de acerto."}

    @app.get("/predictions")
    def predictions(limit: int = Query(default=20, ge=1, le=100)):
        with connect(db_path) as connection:
            rows = connection.execute("""
                SELECT p.*, f.correct_label FROM predictions p
                LEFT JOIN feedback f ON f.prediction_id=p.id ORDER BY p.created_at DESC LIMIT ?
            """, (limit,)).fetchall()
        return {"items": [dict(row) for row in rows]}

    @app.put("/predictions/{prediction_id}/feedback")
    def feedback(prediction_id: str, payload: FeedbackRequest):
        with connect(db_path) as connection:
            if connection.execute("SELECT 1 FROM predictions WHERE id=?", (prediction_id,)).fetchone() is None:
                raise HTTPException(404, "Predição não encontrada")
            connection.execute("""
                INSERT INTO feedback VALUES (?, ?, ?)
                ON CONFLICT(prediction_id) DO UPDATE SET correct_label=excluded.correct_label, updated_at=excluded.updated_at
            """, (prediction_id, payload.correct_label, datetime.now(timezone.utc).isoformat()))
        return {"prediction_id": prediction_id, "correct_label": payload.correct_label}

    return app


app = create_app()

