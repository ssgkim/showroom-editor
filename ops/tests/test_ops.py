"""Ops Hub 점검 엔진·정의 파서 테스트. 클러스터 조회는 Context 캐시를 미리 채워 대신한다."""
import pytest

from app import checks, preflight
from app.schemas import DefinitionError, parse_definition

VALID_DEFINITION = """
about: {summary: 관찰성 실습, duration: 90m}
requirements:
  - name: OpenShift AI
    check: {type: operator, package: rhods-operator, minVersion: "3.5"}
  - name: MaaS
    check: {type: http, url: "https://maas.{{ .domain }}/"}
    severity: recommended
checkpoints:
  - module: 2
    name: 데모 앱
    check: {type: resource, kind: Deployment, namespace: "demo-{{ .user }}", name: planner-backend, ready: true}
"""


def _csv(name: str, version: str, phase: str = "Succeeded") -> dict:
    return {"metadata": {"name": name}, "spec": {"version": version}, "status": {"phase": phase}}


def _node(name: str, cpu: str, memory: str, gpu: str | None = None, taints: list | None = None) -> dict:
    allocatable = {"cpu": cpu, "memory": memory, **({"nvidia.com/gpu": gpu} if gpu else {})}
    return {"metadata": {"name": name}, "spec": {"taints": taints or []}, "status": {"allocatable": allocatable}}


def _ctx(**cache) -> checks.Context:
    return checks.Context(domain="apps.example.com", _cache=dict(cache))


# ── 정의 파서 ──────────────────────────────────────────
def test_parse_definition_accepts_valid_file():
    definition = parse_definition(VALID_DEFINITION)

    assert definition.requirements[0].check.type == "operator"
    assert definition.requirements[1].severity == "recommended"
    assert definition.checkpoints[0].check.model_dump()["namespace"] == "demo-{{ .user }}"


@pytest.mark.parametrize("text, message", [
    ("requirements: [{name: x, check: {type: shell, cmd: 'rm -rf /'}}]", "check.type"),
    ("requirements: [{name: x, check: {type: http, url: 'https://{{ .Files }}'}}]", "자리표시자"),
    ("requirements: [{name: x", "YAML"),
    ("- just a list", "최상위"),
])
def test_parse_definition_rejects_unsafe_or_broken_input(text, message):
    with pytest.raises(DefinitionError, match=message):
        parse_definition(text)


# ── 유틸 ──────────────────────────────────────────
def test_version_and_quantity_parsing():
    assert checks.version_tuple("v1.17.1") == (1, 17, 1)
    assert checks.version_tuple("3.5.2") >= checks.version_tuple("3.5")
    assert checks.parse_quantity("1500m", checks.CPU_UNITS) == 1.5
    assert checks.parse_quantity("2Gi", checks.MEMORY_UNITS) == 2 * 2**30


def test_context_render_replaces_only_known_placeholders():
    ctx = checks.Context(domain="apps.x.com", user="user3")

    assert ctx.render({"url": "https://a.{{ .domain }}/{{ .user }}", "n": [1, "{{ .user }}"]}) == \
        {"url": "https://a.apps.x.com/user3", "n": [1, "user3"]}


# ── 점검 유형 ──────────────────────────────────────────
def test_operator_passes_with_minimum_version():
    ctx = _ctx(csvs=[_csv("rhods-operator.3.5.2", "3.5.2")])

    assert checks.check_operator({"package": "rhods-operator", "minVersion": "3.5"}, ctx) == (True, "3.5.2 설치됨")


def test_operator_fails_below_minimum_version():
    ctx = _ctx(csvs=[_csv("rhods-operator.3.4.0", "3.4.0")])

    passed, observed = checks.check_operator({"package": "rhods-operator", "minVersion": "3.5"}, ctx)

    assert not passed and "필요: 3.5" in observed


def test_operator_reports_stuck_subscription():
    sub = {"spec": {"name": "web-terminal"}, "status": {"conditions": [
        {"type": "BundleUnpackFailed", "status": "True", "reason": "BundleUnpackFailed"}]}}
    ctx = _ctx(csvs=[], subs=[sub])

    passed, observed = checks.check_operator({"package": "web-terminal"}, ctx)

    assert not passed and "BundleUnpackFailed" in observed


def test_gpu_nodes_counts_allocatable_gpus():
    ctx = _ctx(nodes=[_node("a", "16", "64Gi", gpu="2"), _node("b", "16", "64Gi")])

    assert checks.check_gpu_nodes({"min": 1}, ctx)[0] is True
    assert checks.check_gpu_nodes({"min": 2}, ctx)[0] is False


def test_capacity_subtracts_requests_and_skips_tainted_nodes():
    nodes = [_node("w1", "4", "8Gi"), _node("m1", "8", "32Gi", taints=[{"effect": "NoSchedule"}])]
    pods = [{"spec": {"nodeName": "w1", "containers": [{"resources": {"requests": {"cpu": "3", "memory": "4Gi"}}}]}}]
    ctx = _ctx(nodes=nodes, pods=pods)

    assert checks.check_capacity({"users": 10, "cpuPerUser": "100m", "memoryPerUser": "256Mi"}, ctx)[0] is True
    assert checks.check_capacity({"users": 20, "cpuPerUser": "100m", "memoryPerUser": "256Mi"}, ctx)[0] is False


@pytest.mark.parametrize("obj, ready", [
    ({"kind": "Deployment", "status": {"availableReplicas": 1}}, True),
    ({"kind": "Deployment", "status": {"replicas": 1, "availableReplicas": 0}}, False),
    ({"kind": "Pod", "status": {"conditions": [{"type": "Ready", "status": "True"}]}}, True),
])
def test_is_ready(obj, ready):
    assert checks._is_ready(obj) is ready


def test_unknown_check_type_is_an_error():
    with pytest.raises(checks.CheckError):
        checks.run("shell", {}, _ctx())


# ── 사전 점검 조립 ──────────────────────────────────────────
@pytest.mark.parametrize("severity, expected", [("required", "fail"), ("recommended", "warn")])
def test_failed_requirement_status_follows_severity(monkeypatch, severity, expected):
    monkeypatch.setattr(checks, "run", lambda *_: (False, "없음"))

    result = preflight._run_check("agentops", "GPU", {"type": "gpuNodes"}, _ctx(), severity, "노드 추가")

    assert result["status"] == expected and result["fix"] == "노드 추가"


def test_check_error_becomes_error_status(monkeypatch):
    def boom(*_):
        raise checks.CheckError("권한 없음")
    monkeypatch.setattr(checks, "run", boom)

    assert preflight._run_check("x", "y", {"type": "http"}, _ctx(), "required", "")["status"] == "error"


def test_markdown_report_escapes_pipes():
    report = {"title": "T", "at": "now", "contents": ["a"], "users": ["user1", "user2"],
              "summary": {"pass": 0, "warn": 0, "fail": 1, "error": 0}, "definitions": [],
              "results": [{"scope": "common", "name": "a|b", "status": "fail", "observed": "x", "fix": "y"}]}

    markdown = preflight.to_markdown(report, "apps.example.com")

    assert "a\\|b" in markdown and "❌" in markdown and "user1 ~ user2" in markdown


def test_operator_query_skips_olm_copied_csvs(monkeypatch):
    calls = []
    monkeypatch.setattr(checks, "oc_json", lambda args, **_: calls.append(args) or {"items": []})
    monkeypatch.setattr(checks, "_subscription_hint", lambda *_: "없음")

    checks.check_operator({"package": "web-terminal"}, _ctx())

    assert "!olm.copiedFrom" in calls[0]


def test_links_point_to_editor_route(monkeypatch):
    from fastapi.testclient import TestClient

    from app import kube, main

    calls = []
    monkeypatch.setattr(kube, "oc", lambda args, **_: calls.append(args) or "editor.apps.example.com")

    response = TestClient(main.create_app()).get("/api/links")

    assert response.json() == {"editor": "https://editor.apps.example.com"}
    assert calls[0][:5] == ["get", "route", "showroom-editor", "-n", "showroom-editor"]


# ── 자리표시자 · 갤러리 · 진행 현황 ──────────────────────────────────────────
def test_context_renders_user_number_placeholders():
    ctx = checks.Context(domain="d", user="user3")

    assert ctx.render("user-{{ .userNumber2 }}/{{ .userNumber }}/{{ .user }}") == "user-03/3/user3"


def test_definition_accepts_user_number_placeholder():
    text = "checkpoints: [{module: 2, name: p, check: {type: resource, kind: Namespace, name: 'user-{{ .userNumber2 }}'}}]"

    assert parse_definition(text).checkpoints[0].check.model_dump()["name"] == "user-{{ .userNumber2 }}"


def _state():
    return {
        "catalog": {"agentops": {"repoUrl": "https://g/a.git", "repoRef": "main", "title": "AgentOps"},
                    "inference": {"repoUrl": "https://g/i.git", "repoRef": "main", "title": "Inference"}},
        "workshops": {"ws": {"title": "W", "contents": ["agentops"], "userStart": 1, "userCount": 2}},
        "deploy": {"workshop": "ws"}, "preview": None,
    }


DEFINITION_WITH_CHECKPOINTS = """
about: {summary: s, duration: 90m}
requirements: [{name: r, check: {type: gpuNodes}, severity: recommended}]
checkpoints:
  - {module: 2, name: 백엔드, check: {type: resource, kind: Deployment, namespace: "demo-{{ .user }}", name: b, ready: true}}
"""


def test_gallery_lists_catalog_with_definition_workshops_and_readiness(monkeypatch):
    from app import definitions, gallery

    monkeypatch.setattr(definitions, "_fetch_repo_file", lambda *_: None)
    report = {"workshop": "ws", "at": "2026-10-22T10:00:00", "contents": ["agentops"],
              "results": [{"scope": "agentops", "status": "warn"}, {"scope": "common", "status": "fail"}]}

    cards = gallery.build(_state(), {"agentops": DEFINITION_WITH_CHECKPOINTS}, {"ws": report})

    agentops = cards[0]
    assert agentops["name"] == "agentops" and agentops["source"] == "override"
    assert agentops["about"]["duration"] == "90m"
    assert agentops["requirements"] == [{"name": "r", "severity": "recommended"}]
    assert agentops["workshops"] == [{"id": "ws", "title": "W", "deployed": True}]
    assert agentops["readiness"]["verdict"] == "caution"  # common 실패는 콘텐츠 판정에 넣지 않는다
    assert cards[1]["readiness"] is None and cards[1]["workshops"] == []


def test_progress_builds_user_by_checkpoint_matrix(monkeypatch):
    from app import progress

    monkeypatch.setattr(progress, "editor_state", _state)
    monkeypatch.setattr(progress, "load_overrides", lambda: {"agentops": DEFINITION_WITH_CHECKPOINTS})
    monkeypatch.setattr(progress, "showroom_status", lambda users: {u: "ready" for u in users})
    monkeypatch.setattr(progress, "_batch_resource_column", lambda *_: None)
    seen = []

    def fake_run(check_type, params, ctx):
        seen.append(ctx.render(params["namespace"]))
        return ctx.user == "user1", "Ready" if ctx.user == "user1" else "없음"
    monkeypatch.setattr(checks, "run", fake_run)

    result = progress.run("ws", "apps.example.com")

    assert sorted(seen) == ["demo-user1", "demo-user2"]
    assert [c["id"] for c in result["columns"]] == ["agentops:0"] and "check" not in result["columns"][0]
    assert result["rows"][0]["cells"]["agentops:0"] == {"s": "done", "o": "Ready"}
    assert result["rows"][1]["done"] == 0 and result["totals"] == {"agentops:0": 1}


def test_showroom_status_reads_all_namespaces_once(monkeypatch):
    from app import progress

    items = [{"metadata": {"namespace": "showroom-user1"}, "status": {"availableReplicas": 1}},
             {"metadata": {"namespace": "showroom-user2"}, "status": {}}]
    calls = []
    monkeypatch.setattr(progress, "oc_json", lambda args: calls.append(args) or {"items": items})

    assert progress.showroom_status(["user1", "user2", "user3"]) == {"user1": "ready", "user2": "starting", "user3": "missing"}
    assert len(calls) == 1


def test_batched_resource_column_queries_once_and_matches_each_user(monkeypatch):
    from app import progress

    column = {"id": "a:0", "check": {"type": "resource", "kind": "Deployment", "namespace": "demo-{{ .user }}",
                                      "name": "planner-backend", "ready": True}}
    items = [{"kind": "Deployment", "metadata": {"name": "planner-backend", "namespace": "demo-user1"},
              "status": {"availableReplicas": 1}},
             {"kind": "Deployment", "metadata": {"name": "planner-backend", "namespace": "demo-user2"},
              "status": {"replicas": 1, "availableReplicas": 0}}]
    calls = []
    monkeypatch.setattr(progress, "oc_json", lambda args: calls.append(args) or {"items": items})

    cells = progress._batch_resource_column(column, ["user1", "user2", "user3"], "d")

    assert calls == [["get", "Deployment", "-A", "--field-selector", "metadata.name=planner-backend"]]
    assert [cells[u]["s"] for u in ("user1", "user2", "user3")] == ["done", "todo", "todo"]
    assert cells["user3"]["o"] == "Deployment/planner-backend (demo-user3) 없음"


def test_batched_column_reports_missing_resource_type_once(monkeypatch):
    from app import progress
    from app.kube import KubeError

    def missing(args):
        raise KubeError('the server doesn\'t have a resource type "llminferenceservices"')
    monkeypatch.setattr(progress, "oc_json", missing)
    column = {"id": "i:1", "check": {"type": "resource", "kind": "llminferenceservices", "namespace": "user-{{ .userNumber2 }}"}}

    cells = progress._batch_resource_column(column, ["user1"], "d")

    assert cells["user1"]["s"] == "error"


def test_batched_cluster_scoped_namespace_uses_user_number(monkeypatch):
    from app import progress

    items = [{"kind": "Namespace", "metadata": {"name": "user-03"}}]
    monkeypatch.setattr(progress, "oc_json", lambda args: {"items": items})
    column = {"id": "i:0", "check": {"type": "resource", "kind": "Namespace", "name": "user-{{ .userNumber2 }}"}}

    cells = progress._batch_resource_column(column, ["user3", "user4"], "d")

    assert cells["user3"]["s"] == "done" and cells["user4"]["s"] == "todo"
