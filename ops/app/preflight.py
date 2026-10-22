"""사전 점검: 공통 점검 + 워크샵에 포함된 콘텐츠별 요구 사항."""
import os
import subprocess
import tempfile
from datetime import datetime, timezone

from . import checks
from .definitions import editor_state, load_overrides, resolve
from .kube import KubeError, oc_json

# 사용자 Showroom 하나가 요청하는 자원 (init 빌드 컨테이너 기준)
SHOWROOM_CPU_PER_USER = "100m"
SHOWROOM_MEMORY_PER_USER = "256Mi"
REGISTRY_URL = "https://quay.io/v2/"
LS_REMOTE_TIMEOUT = 30


def _result(scope: str, name: str, status: str, observed: str, fix: str = "") -> dict:
    return {"scope": scope, "name": name, "status": status, "observed": observed, "fix": fix}


def expected_users(workshop: dict) -> list[str]:
    start, count = int(workshop["userStart"]), int(workshop["userCount"])
    return [f"user{i}" for i in range(start, start + count)]


def _check_users(workshop: dict) -> dict:
    expected = expected_users(workshop)
    name = f"사용자 계정 {expected[0]} ~ {expected[-1]}"
    try:
        realms = oc_json(["get", "keycloakrealmimports.k8s.keycloak.org", "-A"]).get("items", [])
    except KubeError:
        realms = []
    present = {u.get("username") for r in realms for u in r["spec"]["realm"].get("users", [])}
    if present:
        missing = [u for u in expected if u not in present]
        if missing:
            return _result("common", name, "fail", f"Keycloak 에 없음: {', '.join(missing[:10])}",
                           "Keycloak realm 에 사용자를 추가하거나 워크샵 사용자 범위를 줄이세요")
        return _result("common", name, "pass", f"Keycloak 에 {len(expected)}명 모두 있음")
    users = {u["metadata"]["name"] for u in oc_json(["get", "users"])["items"]}
    missing = [u for u in expected if u not in users]
    if missing:
        return _result("common", name, "warn", f"OpenShift 사용자 목록에 없음: {', '.join(missing[:10])}",
                       "OpenShift 는 한 번 로그인한 사용자만 목록에 보입니다. ID 공급자(htpasswd 등)에서 계정을 확인하세요")
    return _result("common", name, "pass", f"{len(expected)}명 모두 있음")


def _check_repo(name: str, entry: dict) -> dict:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "HOME": tempfile.gettempdir()}
    label = f"콘텐츠 저장소 접근: {name}"
    try:
        result = subprocess.run(["git", "ls-remote", "--exit-code", entry["repoUrl"], entry["repoRef"]],
                                env=env, capture_output=True, text=True, timeout=LS_REMOTE_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        return _result("common", label, "fail", "응답 없음 (시간 초과)", "클러스터에서 GitHub 로 나가는 연결을 확인하세요")
    if result.returncode != 0:
        return _result("common", label, "fail", f"{entry['repoRef']} 를 찾을 수 없음",
                       "저장소 주소·브랜치가 바뀌었거나 비공개로 전환되었는지 확인하세요")
    return _result("common", label, "pass", f"{entry['repoRef']} @ {result.stdout.split()[0][:12]}")


def _run_check(scope: str, name: str, check: dict, ctx: checks.Context, severity: str, fix: str) -> dict:
    params = {k: v for k, v in check.items() if k != "type"}
    try:
        passed, observed = checks.run(check["type"], params, ctx)
    except checks.CheckError as exc:
        return _result(scope, name, "error", f"점검 실패: {exc}", fix)
    if passed:
        return _result(scope, name, "pass", observed)
    return _result(scope, name, "fail" if severity == "required" else "warn", observed, fix)


def run(workshop_id: str, domain: str) -> dict:
    state = editor_state()
    workshop = state["workshops"].get(workshop_id)
    if workshop is None:
        raise KeyError(workshop_id)
    ctx = checks.Context(domain=domain)
    overrides = load_overrides()
    results: list[dict] = [
        _check_users(workshop),
        _run_check("common", "Showroom 용 클러스터 여유 자원",
                   {"type": "capacity", "users": workshop["userCount"],
                    "cpuPerUser": SHOWROOM_CPU_PER_USER, "memoryPerUser": SHOWROOM_MEMORY_PER_USER},
                   ctx, "required", "워커 노드를 늘리거나 사용자 수를 줄이세요"),
        _run_check("common", "Showroom 이미지 레지스트리(quay.io) 접근",
                   {"type": "http", "url": REGISTRY_URL, "expect": [200, 401]},
                   ctx, "required", "클러스터에서 quay.io 로 나가는 연결(프록시·방화벽)을 확인하세요"),
    ]
    definitions = []
    for name in workshop["contents"]:
        entry = state["catalog"].get(name)
        if entry is None:
            results.append(_result(name, "카탈로그 등록", "fail", "에디터 카탈로그에 없음"))
            continue
        results.append(_check_repo(name, entry))
        resolved = resolve(name, entry, overrides)
        definitions.append({k: v for k, v in resolved.items() if k not in {"definition", "text"}})
        definition = resolved["definition"]
        if definition is None:
            continue
        for req in definition.requirements:
            results.append(_run_check(name, req.name, req.check.model_dump(), ctx, req.severity, req.fix))

    summary = {s: sum(1 for r in results if r["status"] == s) for s in ("pass", "warn", "fail", "error")}
    return {
        "workshop": workshop_id,
        "title": workshop["title"],
        "contents": workshop["contents"],
        "users": expected_users(workshop),
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary": summary,
        "definitions": definitions,
        "results": results,
    }


STATUS_MARK = {"pass": "✅", "warn": "⚠️", "fail": "❌", "error": "❓"}


def to_markdown(report: dict, domain: str) -> str:
    s = report["summary"]
    lines = [
        f"# 사전 점검 보고서: {report['title']}",
        "",
        f"- 클러스터: `{domain}`",
        f"- 점검 시각 (UTC): {report['at']}",
        f"- 콘텐츠: {', '.join(report['contents'])}",
        f"- 사용자: {report['users'][0]} ~ {report['users'][-1]} ({len(report['users'])}명)",
        f"- 결과: ✅ {s['pass']} · ⚠️ {s['warn']} · ❌ {s['fail']} · ❓ {s['error']}",
        "",
        "| 상태 | 범위 | 항목 | 관찰 값 | 조치 |",
        "|---|---|---|---|---|",
    ]
    for r in report["results"]:
        cells = [STATUS_MARK[r["status"]], "공통" if r["scope"] == "common" else r["scope"],
                 r["name"], r["observed"], r["fix"] if r["status"] != "pass" else ""]
        lines.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    missing = [d["name"] for d in report["definitions"] if d["source"] == "none"]
    if missing:
        lines += ["", f"> 워크샵 정의(workshop.yaml)가 없어 요구 사항을 점검하지 못한 콘텐츠: {', '.join(missing)}"]
    return "\n".join(lines) + "\n"
