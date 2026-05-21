"""Phase 2 — taxonomy proposal."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from livedocs.agent import AgentError
from livedocs.bootstrap.state import GuidanceText, Scan
from livedocs.bootstrap.taxonomy import propose_taxonomy


def _make_scan(tmp_path: Path, *, routes, i18n, models) -> Scan:
    cache = tmp_path / ".livedocs" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "routes.json").write_text(json.dumps(routes))
    (cache / "i18n.json").write_text(json.dumps(i18n))
    (cache / "models.json").write_text(json.dumps(models))
    return Scan(
        routes_path=str(cache / "routes.json"),
        i18n_path=str(cache / "i18n.json"),
        models_path=str(cache / "models.json"),
    )


def test_propose_taxonomy_happy_path(tmp_path, mock_agent):
    scan = _make_scan(
        tmp_path,
        routes=[{"path": "/billing", "file": "src/pages/billing.vue", "name": "billing"}],
        i18n=[{"key": "menu.billing", "values_by_lang": {"pt-BR": "Cobrança"}}],
        models=[{"name": "Invoice", "kind": "prisma", "fields": ["id", "amount"]}],
    )
    guidance = GuidanceText(text="SaaS de billing B2B.")

    canned = {
        "capabilities": [
            {"slug": "cobranca", "title": "Cobrança",
             "summary": "Faturas e cobrança recorrente",
             "code_anchors": ["src/billing/**"]},
            {"slug": "usuarios", "title": "Usuários",
             "summary": "Gestão de contas", "code_anchors": ["src/users/**"]},
        ],
        "journeys": [
            {"slug": "primeira-fatura", "title": "Primeira fatura",
             "summary": "Do cadastro à primeira fatura",
             "capability_refs": ["cobranca", "usuarios"]},
        ],
    }
    mock_agent.set_response("propor-taxonomia", canned)

    tax = propose_taxonomy(scan, guidance, tmp_path, lang="pt-BR")
    assert len(tax.capabilities) == 2
    assert tax.capabilities[0].slug == "cobranca"
    assert len(tax.journeys) == 1


def test_propose_taxonomy_agent_error_propagates(tmp_path, mock_agent):
    scan = _make_scan(tmp_path, routes=[], i18n=[], models=[])
    guidance = GuidanceText(text="")
    # No matcher registered → MockAgent returns is_error=True
    with pytest.raises(AgentError):
        propose_taxonomy(scan, guidance, tmp_path, lang="pt-BR")


def test_propose_taxonomy_invalid_json_raises(tmp_path, mock_agent):
    scan = _make_scan(tmp_path, routes=[], i18n=[], models=[])
    guidance = GuidanceText(text="")
    mock_agent.set_response("propor-taxonomia", {"capabilities": "not a list"})
    with pytest.raises(AgentError):
        propose_taxonomy(scan, guidance, tmp_path, lang="pt-BR")
