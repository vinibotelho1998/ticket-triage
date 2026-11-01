import csv

import joblib
import pytest
from fastapi.testclient import TestClient

from ticket_triage.api import create_app
from ticket_triage.generate import generate
from ticket_triage.train import read_rows, split_rows, train


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    root = tmp_path_factory.mktemp("triage")
    data, model, report = root / "tickets.csv", root / "model.joblib", root / "evaluation.json"
    generate(data)
    metrics = train(data, model, report)
    return root, data, model, metrics


def test_split_separates_entire_scenarios(trained):
    _, data, _, metrics = trained
    training, holdout = split_rows(read_rows(data))
    assert {row["scenario_id"] for row in training}.isdisjoint(row["scenario_id"] for row in holdout)
    assert {row["label"] for row in holdout} == {row["label"] for row in training}
    assert sum(map(sum, metrics["confusion_matrix"])) == len(holdout)
    assert metrics["macro_f1"] > metrics["baseline_macro_f1"]


def test_vectorizer_does_not_fit_test_only_words(trained):
    root, data, _, _ = trained
    rows = read_rows(data)
    _, holdout = split_rows(rows)
    heldout_groups = {row["scenario_id"] for row in holdout}
    for row in rows:
        if row["scenario_id"] in heldout_groups:
            row["text"] += " unseenholdouttoken"
    changed = root / "changed.csv"
    with changed.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    train(changed, root / "changed.joblib", root / "changed.json")
    vocabulary = joblib.load(root / "changed.joblib")["pipeline"].named_steps["tfidf"].vocabulary_
    assert "unseenholdouttoken" not in vocabulary


def test_generator_is_reproducible(tmp_path):
    generate(tmp_path / "a.csv")
    generate(tmp_path / "b.csv")
    assert (tmp_path / "a.csv").read_bytes() == (tmp_path / "b.csv").read_bytes()


def test_prediction_feedback_and_minimal_history(trained, tmp_path):
    _, _, model, _ = trained
    with TestClient(create_app(model, tmp_path / "history.db")) as client:
        assert client.get("/health").status_code == 200
        response = client.post("/predict", json={"text": "Minha senha foi recusada e não consigo fazer login"})
        assert response.status_code == 200
        result = response.json()
        assert result["label"] == "acesso"
        assert sum(result["scores"].values()) == pytest.approx(1)
        assert "não calibrado" in result["score_note"]
        endpoint = f"/predictions/{result['prediction_id']}/feedback"
        assert client.put(endpoint, json={"correct_label": "erro_tecnico"}).status_code == 200
        assert client.put(endpoint, json={"correct_label": "acesso"}).status_code == 200
        history = client.get("/predictions").json()["items"]
        assert len(history) == 1
        assert history[0]["correct_label"] == "acesso"
        assert "text" not in history[0]
        assert client.put("/predictions/unknown/feedback", json={"correct_label": "acesso"}).status_code == 404


@pytest.mark.parametrize("payload", [{"text": "   "}, {"text": "123456"}, {"text": "a" * 4001}, {"text": "senha ruim", "admin": True}])
def test_invalid_inputs_are_rejected(trained, tmp_path, payload):
    with TestClient(create_app(trained[2], tmp_path / "history.db")) as client:
        assert client.post("/predict", json=payload).status_code == 422


def test_missing_model_is_not_ready(tmp_path):
    with TestClient(create_app(tmp_path / "missing.joblib", tmp_path / "history.db")) as client:
        assert client.get("/health").status_code == 503
        assert client.post("/predict", json={"text": "Não consigo fazer login"}).status_code == 503

