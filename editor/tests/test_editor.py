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


# ── 행사별 페이지 수정 ──────────────────────────────────────────
@pytest.mark.parametrize("path", [
    "content/modules/ROOT/pages/index.adoc",
    "content/modules/ROOT/partials/vars.adoc",
])
def test_page_path_accepts_adoc_under_start_path(path):
    from app import repofiles

    assert repofiles.check_page_path(path, "content") == path


@pytest.mark.parametrize("path", [
    "content/../secret.adoc", "/etc/passwd.adoc", "other/modules/x.adoc",
    "content/modules/ROOT/pages/x.yml", "content/modules/ROOT/pages/a b.adoc", "",
])
def test_page_path_rejects_outside_or_non_adoc(path):
    from app import repofiles

    with pytest.raises(ValueError):
        repofiles.check_page_path(path, "content")


def test_blob_sha_matches_git():
    from app import repofiles

    # git hash-object 와 같은 값 (printf 'hello\n' | git hash-object --stdin)
    assert repofiles.blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_read_page_refuses_symlink_escape(tmp_path):
    from app import repofiles

    repo = tmp_path / "repo"
    (repo / "content").mkdir(parents=True)
    (tmp_path / "secret.adoc").write_text("secret")
    (repo / "content" / "link.adoc").symlink_to(tmp_path / "secret.adoc")

    with pytest.raises(FileNotFoundError):
        repofiles.read_page(repo, "content/link.adoc")


def test_build_values_passes_overlays_for_included_contents_only():
    overlays = {"agentops": {"content/modules/ROOT/pages/b.adoc": {"text": "B"},
                             "content/modules/ROOT/pages/a.adoc": {"text": "A"}},
                "removed": {"content/x.adoc": {"text": "X"}}}

    values = deployer.build_values(STATE, WORKSHOP, "deploy", CLUSTER, overlays)

    assert [o["path"] for o in values["contents"]["agentops"]["overlays"]] == [
        "content/modules/ROOT/pages/a.adoc", "content/modules/ROOT/pages/b.adoc"]
    assert values["contents"]["inference"]["overlays"] == []
    assert "removed" not in values["contents"]


@pytest.mark.skipif(shutil.which("helm") is None, reason="helm 이 없으면 건너뛴다")
def test_render_puts_overlay_files_into_site_configmap():
    import yaml

    text = '= 제목 {{ .user }}\n[source]\n----\nkey: "v" # <tag> & \'q\'\n----\n'
    values = deployer.build_values(STATE, {**WORKSHOP, "userCount": 1}, "deploy", CLUSTER,
                                   {"agentops": {"content/modules/ROOT/pages/index.adoc": {"text": text}}})

    site = next(d for d in yaml.safe_load_all(deployer.render(values))
                if d and d["kind"] == "ConfigMap" and d["metadata"]["name"] == "showroom-site")

    assert site["data"]["overlays.txt"].strip() == "agentops 0 content/modules/ROOT/pages/index.adoc"
    assert site["data"]["overlay-agentops-0.adoc"] == text


def test_overlay_store_removes_empty_branches(monkeypatch):
    from app import overlays

    data = {"ws": {"agentops": {"p.adoc": {"text": "x"}}}}
    saved = []
    monkeypatch.setattr(overlays, "load_all", lambda: data)
    monkeypatch.setattr(overlays, "_save", saved.append)

    overlays.remove("ws", "agentops", "p.adoc")

    assert saved == [{}]
    assert data == {"ws": {"agentops": {"p.adoc": {"text": "x"}}}}  # 원본은 바꾸지 않는다


def _git_repo(path, files):
    import subprocess
    for name, text in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(text)
    for args in (["init", "-q", "-b", "main"], ["add", "-A"],
                 ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c"]):
        subprocess.run(["git", *args], cwd=path, check=True)


def test_page_api_lists_saves_and_flags_stale_source(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app import main, overlays, repofiles, store

    source = tmp_path / "src"
    source.mkdir()
    _git_repo(source, {"content/antora.yml": "name: x\n", "content/modules/ROOT/pages/index.adoc": "= 원본\n"})
    monkeypatch.setattr(repofiles, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(repofiles, "REMOTE_CHECK_TTL", -1)
    state = {**STATE, "catalog": {"agentops": {**STATE["catalog"]["agentops"], "repoUrl": str(source), "repoRef": "main"}},
             "workshops": {"ws": {**WORKSHOP, "contents": ["agentops"]}}}
    saved = {}
    monkeypatch.setattr(store, "load", lambda: state)
    monkeypatch.setattr(overlays, "load_all", lambda: saved.get("data", {}))
    monkeypatch.setattr(overlays, "_save", lambda data: saved.update(data=data))
    client = TestClient(main.create_app())
    page = "content/modules/ROOT/pages/index.adoc"

    assert client.get("/api/workshops/ws/pages/agentops").json()["pages"] == [
        {"path": page, "edited": False, "stale": False}]
    assert client.put("/api/workshops/ws/pages/agentops/file", json={"path": page, "text": "= 원본\n"}).status_code == 400
    assert client.put("/api/workshops/ws/pages/agentops/file", json={"path": page, "text": "= 행사용\n"}).status_code == 200
    assert client.get("/api/workshops/ws/pages/agentops/file", params={"path": page}).json()["edited"] == "= 행사용\n"
    assert client.get("/api/workshops/ws/pages/agentops/file", params={"path": "../x.adoc"}).status_code == 400
    assert client.get("/api/workshops/ws/pages/inference").status_code == 404

    _git_repo(source, {"content/modules/ROOT/pages/index.adoc": "= 원본 v2\n"})

    assert client.get("/api/workshops/ws/pages/agentops").json()["pages"][0] == {"path": page, "edited": True, "stale": True}


# ── 왼쪽 목차 · 첫 화면 ──────────────────────────────────────────
@pytest.mark.parametrize("extra", [
    {"homeTitle": "두 줄\n제목"},
    {"homeLabel": "홈]"},
    {"contentLabels": {"agentops": "a]b"}},
    {"navLinks": [{"name": "설문", "url": "javascript:alert(1)"}]},
    {"navLinks": [{"name": "설문", "url": "https://x.com/a]b"}]},
])
def test_workshop_rejects_labels_that_break_navigation(extra):
    with pytest.raises(ValidationError):
        WorkshopIn(**WORKSHOP, **extra)


def test_build_values_applies_nav_customization():
    workshop = {**WORKSHOP, "homeTitle": "BC카드 AI 데이", "homeLabel": "시작", "homePage": "",
                "contentLabels": {"agentops": "2부 · 관찰성"},
                "navLinks": [{"name": "설문", "url": "https://forms.example.com/a"}]}

    values = deployer.build_values(STATE, workshop, "deploy", CLUSTER)

    assert values["site"] == {"title": "BC카드 핸즈온", "homeTitle": "BC카드 AI 데이", "homeLabel": "시작",
                              "navLinks": [{"name": "설문", "url": "https://forms.example.com/a"}]}
    assert values["contents"]["agentops"]["title"] == "2부 · 관찰성"
    assert values["contents"]["inference"]["title"] == "Inference"


@pytest.mark.skipif(shutil.which("helm") is None, reason="helm 이 없으면 건너뛴다")
def test_render_nav_uses_custom_title_labels_and_links():
    import yaml

    workshop = {**WORKSHOP, "userCount": 1, "homeTitle": "BC카드 AI 데이", "homeLabel": "시작",
                "contentLabels": {"agentops": "2부"}, "navLinks": [{"name": "설문", "url": "https://f.example.com/a"}]}
    site = next(d for d in yaml.safe_load_all(deployer.render(deployer.build_values(STATE, workshop, "deploy", CLUSTER)))
                if d and d["kind"] == "ConfigMap" and d["metadata"]["name"] == "showroom-site")

    assert site["data"]["home-nav.adoc"].splitlines() == [
        "* xref:index.adoc[시작]", "* xref:agentops::index.adoc[2부]",
        "* xref:inference::index.adoc[Inference]", "* link:https://f.example.com/a[설문,window=_blank]"]
    assert 'title: "BC카드 AI 데이"' in site["data"]["home-antora.yml"]
    assert site["data"]["home-index.adoc"].startswith("= BC카드 AI 데이\n\n`{user}` 님, 환영합니다.")


@pytest.mark.skipif(shutil.which("helm") is None, reason="helm 이 없으면 건너뛴다")
def test_render_uses_edited_home_page_verbatim():
    import yaml

    page = "= 환영합니다\n\n[NOTE]\n====\n오늘 일정: 10시 시작 {user}\n====\n\n* xref:agentops::index.adoc[관찰성]\n"
    values = deployer.build_values(STATE, {**WORKSHOP, "userCount": 1, "homePage": page}, "deploy", CLUSTER)
    site = next(d for d in yaml.safe_load_all(deployer.render(values))
                if d and d["kind"] == "ConfigMap" and d["metadata"]["name"] == "showroom-site")

    assert site["data"]["home-index.adoc"].rstrip("\n") == page.rstrip("\n")
