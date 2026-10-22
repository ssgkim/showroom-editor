"""워크샵 구성을 통합 Antora 차트로 렌더링해 클러스터에 적용한다."""
import json
import os
import tempfile

import yaml

from .kube import oc, oc_json, run

CHART_DIR = os.environ.get("CHART_DIR", "/opt/chart")
ROLE_LABEL = "showroom.editor/role"
ROLES = ("preview", "deploy")
ORDER_STEP = 10


def cluster_info() -> dict:
    domain = oc(["get", "ingresses.config.openshift.io", "cluster", "-o", "jsonpath={.spec.domain}"])
    api_url = oc(["get", "infrastructure", "cluster", "-o", "jsonpath={.status.apiServerURL}"])
    return {"domain": domain.strip(), "apiUrl": api_url.strip()}


def _home(workshop: dict) -> dict:
    """첫 화면 값. 비어 있으면 차트 기본값(워크샵 제목, 환영 문구)을 쓰도록 넘기지 않는다."""
    home = {key: workshop.get(key, "").strip() for key in ("homeTitle", "homePage", "homeLabel")}
    return {**{key: value for key, value in home.items() if value}, "navLinks": workshop.get("navLinks", [])}


def build_values(state: dict, workshop: dict, role: str, cluster: dict, overlays: dict | None = None) -> dict:
    """overlays: {콘텐츠 이름: {파일 경로: {text, ...}}} — 빌드할 때 원본 위에 덮어쓸 페이지"""
    overlays = overlays or {}
    contents = {}
    for index, name in enumerate(workshop["contents"]):
        entry = state["catalog"].get(name)
        if entry is None:
            raise ValueError(f"카탈로그에 없는 콘텐츠입니다: {name}")
        contents[name] = {
            "repoUrl": entry["repoUrl"],
            "repoRef": entry["repoRef"],
            "startPath": entry["startPath"],
            "title": workshop.get("contentLabels", {}).get(name) or entry["title"],
            "order": (index + 1) * ORDER_STEP,
            "tabs": entry.get("tabs", []),
            "attributes": entry.get("attributes", {}),
            "overlays": [{"path": path, "text": item["text"]}
                         for path, item in sorted(overlays.get(name, {}).items())],
        }
    if role == "deploy":
        users = {"prefix": "user", "start": workshop["userStart"], "count": workshop["userCount"]}
    else:
        users = {"prefix": "preview", "start": 1, "count": 1}
    return {
        "cluster": cluster,
        "site": {"title": workshop["title"], **_home(workshop)},
        "users": users,
        "contents": contents,
        "namespaceLabels": {ROLE_LABEL: role},
    }


def render(values: dict) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(values, handle)
        values_file = handle.name
    try:
        return run(["helm", "template", "showroom", CHART_DIR, "-f", values_file])
    finally:
        os.unlink(values_file)


def _namespaces_in(manifests: str) -> set[str]:
    return {
        doc["metadata"]["name"]
        for doc in yaml.safe_load_all(manifests)
        if doc and doc.get("kind") == "Namespace"
    }


def role_namespaces(role: str) -> list[str]:
    """역할 레이블이 붙은 네임스페이스. 이미 삭제 중인 것은 제외한다."""
    items = oc_json(["get", "namespaces", "-l", f"{ROLE_LABEL}={role}"])["items"]
    return sorted(
        item["metadata"]["name"]
        for item in items
        if item.get("status", {}).get("phase") != "Terminating"
    )


def prune(role: str, keep: set[str]) -> list[str]:
    stale = [ns for ns in role_namespaces(role) if ns not in keep]
    if stale:
        oc(["delete", "namespace", *stale, "--wait=false"])
    return stale


def apply(values: dict, role: str) -> dict:
    manifests = render(values)
    desired = _namespaces_in(manifests)
    if desired:
        oc(["apply", "-f", "-"], stdin=manifests, timeout=300)
    removed = prune(role, desired)
    return {"namespaces": sorted(desired), "removed": removed}


def remove(role: str) -> list[str]:
    return prune(role, set())


def restart(role: str) -> list[str]:
    namespaces = role_namespaces(role)
    for ns in namespaces:
        oc(["rollout", "restart", "deployment/showroom", "-n", ns])
    return namespaces
