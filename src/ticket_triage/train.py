"""Treinamento: separa cenários antes de ajustar o vocabulário TF-IDF."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import joblib
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ticket_triage import LABELS


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not {"id", "scenario_id", "text", "label", "source"}.issubset(rows[0]):
        raise ValueError("CSV deve conter id, scenario_id, text, label e source")
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("IDs duplicados")
    if len({row["text"].strip().casefold() for row in rows}) != len(rows):
        raise ValueError("Textos duplicados podem contaminar a avaliação")
    scenarios = {}
    for row in rows:
        if row["label"] not in LABELS or not row["text"].strip() or not row["scenario_id"]:
            raise ValueError("Exemplo inválido")
        previous = scenarios.setdefault(row["scenario_id"], row["label"])
        if previous != row["label"]:
            raise ValueError("Mesmo cenário com rótulos diferentes")
    if set(scenarios.values()) != set(LABELS):
        raise ValueError("O dataset deve conter todas as quatro classes")
    return rows


def split_rows(rows: list[dict], seed: int = 42):
    groups = {row["scenario_id"]: row["label"] for row in rows}
    group_ids = sorted(groups)
    train_groups, test_groups = train_test_split(
        group_ids, test_size=0.25, random_state=seed,
        stratify=[groups[group] for group in group_ids],
    )
    train_set, test_set = set(train_groups), set(test_groups)
    return (
        [row for row in rows if row["scenario_id"] in train_set],
        [row for row in rows if row["scenario_id"] in test_set],
    )


def train(data: Path, output: Path, report_path: Path, seed: int = 42) -> dict:
    rows = read_rows(data)
    train_rows, test_rows = split_rows(rows, seed)
    x_train, y_train = [r["text"] for r in train_rows], [r["label"] for r in train_rows]
    x_test, y_test = [r["text"] for r in test_rows], [r["label"] for r in test_rows]
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode", max_features=10000)),
        ("classifier", LogisticRegression(C=3.0, max_iter=2000, class_weight="balanced", random_state=seed)),
    ])
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    baseline = DummyClassifier(strategy="most_frequent").fit([[0]] * len(y_train), y_train)
    baseline_predictions = baseline.predict([[0]] * len(y_test))
    data_hash = hashlib.sha256(data.read_bytes()).hexdigest()
    version = hashlib.sha256(f"tfidf-logreg-v1:{seed}:{data_hash}:{sklearn.__version__}".encode()).hexdigest()[:16]
    report = {
        "model_version": version, "dataset_sha256": data_hash, "seed": seed,
        "sklearn_version": sklearn.__version__, "data_source": "100% sintético; cenários escritos no gerador",
        "split": "75/25 estratificado por scenario_id; TF-IDF ajustado somente no treino",
        "train_examples": len(train_rows), "test_examples": len(test_rows),
        "train_scenarios": sorted({r["scenario_id"] for r in train_rows}),
        "test_scenarios": sorted({r["scenario_id"] for r in test_rows}),
        "labels": list(LABELS), "macro_f1": f1_score(y_test, predictions, average="macro", zero_division=0),
        "baseline_macro_f1": f1_score(y_test, baseline_predictions, average="macro", zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=LABELS).tolist(),
        "classification_report": classification_report(y_test, predictions, labels=LABELS, output_dict=True, zero_division=0),
        "errors": [{"id": row["id"], "text": row["text"], "expected": actual, "predicted": str(predicted)}
                   for row, actual, predicted in zip(test_rows, y_test, predictions) if actual != predicted],
        "limitation": "Holdout sintético pequeno e próximo do gerador; não estima desempenho em clientes reais. Scores não calibrados.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipeline, "model_version": version, "labels": list(LABELS)}, output)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/tickets.csv"))
    parser.add_argument("--output", type=Path, default=Path("var/model.joblib"))
    parser.add_argument("--report", type=Path, default=Path("reports/evaluation.json"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = train(args.data, args.output, args.report, args.seed)
    print(json.dumps({key: result[key] for key in ("macro_f1", "baseline_macro_f1", "model_version")}, indent=2))

