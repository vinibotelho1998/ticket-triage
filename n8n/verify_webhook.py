"""Teste HTTP real: n8n publicado -> API -> resposta, sem mocks ou dependências extras."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def post(url: str, payload: dict) -> tuple[int, dict]:
    request = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        response = urlopen(request, timeout=30)
    except HTTPError as error:
        response = error
    with response:
        body = json.loads(response.read().decode())
        if not isinstance(body, dict):
            raise AssertionError(f"Esperado objeto JSON, recebido {body!r}")
        return response.status, body


def verify(base_url: str) -> list[dict]:
    url = base_url.rstrip("/") + "/webhook/ticket-triage"
    results = []
    status, body = post(url, {"text": "Minha senha foi recusada e não consigo fazer login"})
    assert status == 200, (status, body)
    assert body["label"] == "acesso", body
    assert body["prediction_id"] and body["model_version"], body
    assert 0 <= body["score"] <= 1 and abs(sum(body["scores"].values()) - 1) < 1e-6, body
    assert "não calibrado" in body["score_note"], body
    results.append({"case": "prediction", "status": status, "label": body["label"], "model_version": body["model_version"]})

    for name, payload in (("empty_text", {"text": ""}), ("unexpected_field", {"text": "Preciso recuperar minha senha", "admin": True})):
        status, body = post(url, payload)
        assert status == 422 and isinstance(body.get("detail"), list), (status, body)
        results.append({"case": name, "status": status, "validation_errors": len(body["detail"])})
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5678")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "base_url": args.base_url,
              "workflow_id": "portfolioTicket1", "transport": "real HTTP; no mocks", "cases": verify(args.base_url)}
    report["status"] = "passed"
    content = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(content, encoding="utf-8")
    print(content)

