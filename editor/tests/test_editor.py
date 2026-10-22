"""에디터 핵심 로직 테스트. 렌더링 테스트는 로컬 helm 과 저장소의 차트를 사용한다."""
import os
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

os.environ.setdefault("CHART_DIR", str(Path(__file__).resolve().parents[2]))

from app import deployer, status  # noqa: E402
from app.schemas import CatalogIn, WorkshopIn  # noqa: E402

CLUSTER = {"domain": "apps.example.com", "apiUrl": "https://api.example.com:6443"}
STATE = {
    "catalog": {
        "inference": {"repoUrl": "https://github.com/a/inference.git", "repoRef": "main",
                      "startPath": "content", "title": "Inference", "tabs": [], "attributes": {}},
        "agentops": {"repoUrl": "https://github.com/a/agentops.git", "repoRef": "v1",
                     "startPath": "content", "title": "AgentOps",
                     "tabs": [{"name": "MLflow", "url": "https://mlflow.{{ .domain }}/", "external": True}],
                     "attributes": {"demo-ns": "demo-{{ .user }}"}},
    },
    "workshops": {},
}
WORKSHOP = {"title": "BC카드 핸즈온", "contents": ["agentops", "inference"], "userStart": 3, "userCount": 2}


def test_build_values_keeps_workshop_order_and_user_range():
    values = deployer.build_values(STATE, WORKSHOP, "deploy", CLUSTER)

    assert values["contents"]["agentops"]["order"] < values["contents"]["inference"]["order"]
    assert values["users"] == {"prefix": "user", "start": 3, "count": 2}
    assert values["namespaceLabels"] == {deployer.ROLE_LABEL: "deploy"}
    assert values["site"]["title"] == "BC카드 핸즈온"


def test_build_values_preview_targets_single_preview_user():
    values = deployer.build_values(STATE, WORKSHOP, "preview", CLUSTER)

    assert values["users"] == {"prefix": "preview", "start": 1, "count": 1}


def test_build_values_rejects_unknown_content():
    with pytest.raises(ValueError, match="카탈로그에 없는"):
        deployer.build_values(STATE, {**WORKSHOP, "contents": ["missing"]}, "deploy", CLUSTER)


@pytest.mark.skipif(shutil.which("helm") is None, reason="helm 이 필요합니다")
def test_render_produces_labeled_namespaces_per_user():
    manifests = deployer.render(deployer.build_values(STATE, WORKSHOP, "deploy", CLUSTER))

    assert deployer._namespaces_in(manifests) == {"showroom-user3", "showroom-user4"}
    assert "showroom.editor/role: deploy" in manifests
    assert "agentops https://github.com/a/agentops.git v1 content" in manifests
    assert "https://mlflow.apps.example.com/" in manifests
    assert "demo-ns: demo-user3" in manifests


def _pod(init_statuses, ready=False):
    return {"metadata": {"name": "p", "namespace": "n", "creationTimestamp": "t"},
            "status": {"initContainerStatuses": init_statuses,
                       "containerStatuses": [{"ready": ready}]}}


@pytest.mark.parametrize("init_statuses, ready, expected", [
    ([{"name": "clone", "state": {"running": {}}}], False, "building"),
    ([{"name": "clone", "state": {"terminated": {"exitCode": 0}}},
      {"name": "build", "state": {"terminated": {"exitCode": 1}}}], False, "failed"),
    ([{"name": "clone", "state": {"waiting": {"reason": "CrashLoopBackOff"}}}], False, "failed"),
    ([{"name": "clone", "state": {"terminated": {"exitCode": 0}}},
      {"name": "build", "state": {"terminated": {"exitCode": 0}}}], True, "ready"),
    ([{"name": "clone", "state": {"terminated": {"exitCode": 0}}},
      {"name": "build", "state": {"terminated": {"exitCode": 0}}}], False, "starting"),
])
def test_pod_phase(init_statuses, ready, expected):
    phase, _ = status._pod_phase(_pod(init_statuses, ready))

    assert phase == expected


def test_pod_phase_reports_step_code_not_text():
    building = _pod([{"name": "clone", "state": {"running": {}}}])
    failed = _pod([{"name": "clone", "state": {"terminated": {"exitCode": 0}}},
                   {"name": "build", "state": {"terminated": {"exitCode": 1}}}])

    assert status._pod_phase(building) == ("building", "clone")
    assert status._pod_phase(failed) == ("failed", "build")


def test_pod_phase_without_pod_is_pending():
    assert status._pod_phase(None)[0] == "pending"


def test_user_sort_key_orders_numerically():
    names = ["showroom-user10", "showroom-user2", "showroom-user1"]

    assert sorted(names, key=status._user_sort_key) == ["showroom-user1", "showroom-user2", "showroom-user10"]


@pytest.mark.parametrize("payload", [
    {"name": "home", "repoUrl": "https://github.com/a/b.git"},
    {"name": "Bad_Name", "repoUrl": "https://github.com/a/b.git"},
    {"name": "ok", "repoUrl": "git@github.com:a/b.git"},
    {"name": "ok", "repoUrl": "https://github.com/a/b.git", "attributes": {"bad key": "x"}},
])
def test_catalog_rejects_invalid_input(payload):
    with pytest.raises(ValidationError):
        CatalogIn(**payload)


def test_workshop_requires_content():
    with pytest.raises(ValidationError):
        WorkshopIn(title="t", contents=[])


def test_tab_and_attributes_accept_allowed_placeholders():
    item = CatalogIn(
        name="agentops", repoUrl="https://github.com/a/b.git",
        tabs=[{"name": "MLflow", "url": "https://mlflow-server.{{ .domain }}/"}],
        attributes={"demo-ns": "demo-{{ .user }}", "login": "oc login {{ .apiUrl }}"},
    )

    assert item.tabs[0].url == "https://mlflow-server.{{ .domain }}/"


@pytest.mark.parametrize("payload", [
    {"tabs": [{"name": "x", "url": "https://{{ .Files.Get \"x\" }}/"}]},
    {"attributes": {"a": "{{ include \"x\" . }}"}},
    {"attributes": {"a": "{{ .domain"}},
])
def test_catalog_rejects_template_injection(payload):
    with pytest.raises(ValidationError):
        CatalogIn(name="ok", repoUrl="https://github.com/a/b.git", **payload)


def test_routes_receive_path_parameters(monkeypatch):
    from fastapi.testclient import TestClient

    from app import main, store

    saved = {}
    state = {**STATE, "workshops": {}, "preview": None, "deploy": None}
    monkeypatch.setattr(store, "load", lambda: state)
    monkeypatch.setattr(store, "update", lambda change: saved.update(change(state)) or saved)
    client = TestClient(main.create_app())

    response = client.put("/api/workshops/bccard-2026-11", json=WORKSHOP)

    assert response.status_code == 200, response.text
    assert "bccard-2026-11" in saved["workshops"]
    assert client.put("/api/workshops/Bad_Id", json=WORKSHOP).status_code == 422
    assert client.delete("/api/roles/other").status_code == 422


def test_route_url_returns_none_when_other_app_is_missing(monkeypatch):
    from app import kube

    def missing(*_args, **_kwargs):
        raise kube.KubeError('routes.route.openshift.io "workshop-ops" not found')
    monkeypatch.setattr(kube, "oc", missing)

    assert kube.route_url("workshop-ops", "workshop-ops") is None


def test_links_point_to_ops_hub_route(monkeypatch):
    from fastapi.testclient import TestClient

    from app import kube, main

    calls = []
    monkeypatch.setattr(kube, "oc", lambda args, **_: calls.append(args) or "ops.apps.example.com")

    response = TestClient(main.create_app()).get("/api/links")

    assert response.json() == {"opsHub": "https://ops.apps.example.com"}
    assert calls[0][:5] == ["get", "route", "workshop-ops", "-n", "workshop-ops"]
