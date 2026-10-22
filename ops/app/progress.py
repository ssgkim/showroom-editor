"""진행 현황: 배포된 사용자마다 워크샵 정의의 체크포인트를 점검한다.

결과는 (사용자 × 체크포인트) 표다. 클러스터는 읽기만 한다.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import checks
from .definitions import editor_state, load_overrides, resolve
from .kube import KubeError, oc_json
from .preflight import expected_users

MAX_WORKERS = 8
SHOWROOM_DEPLOYMENT = "showroom"
SHOWROOM_NAMESPACE_PREFIX = "showroom-"


def checkpoint_columns(workshop: dict, catalog: dict, overrides: dict) -> tuple[list[dict], list[dict]]:
    """(체크포인트 열 목록, 정의 상태). 열 id 는 "<콘텐츠>:<순번>" 이다."""
    columns, definitions = [], []
    for name in workshop["contents"]:
        entry = catalog.get(name)
        if entry is None:
            continue
        resolved = resolve(name, entry, overrides)
        definition = resolved["definition"]
        points = definition.checkpoints if definition else []
        definitions.append({"name": name, "title": entry.get("title", name), "source": resolved["source"],
                            "error": resolved["error"], "checkpoints": len(points)})
        columns += [{"id": f"{name}:{index}", "content": name, "module": str(point.module), "name": point.name,
                     "check": point.check.model_dump()} for index, point in enumerate(points)]
    return columns, definitions


def showroom_status(users: list[str]) -> dict[str, str]:
    """사용자별 Showroom 상태: ready | starting | missing (조회 한 번으로 모두 읽는다)."""
    items = oc_json(["get", "deployments", "-A", "--field-selector", f"metadata.name={SHOWROOM_DEPLOYMENT}"])["items"]
    by_namespace = {item["metadata"]["namespace"]: item for item in items}
    status = {}
    for user in users:
        item = by_namespace.get(f"{SHOWROOM_NAMESPACE_PREFIX}{user}")
        if item is None:
            status[user] = "missing"
        else:
            status[user] = "ready" if item.get("status", {}).get("availableReplicas", 0) >= 1 else "starting"
    return status


def _batch_resource_column(column: dict, users: list[str], domain: str) -> dict[str, dict] | None:
    """사용자마다 이름·네임스페이스만 다른 resource 점검은 한 번 조회해 나눠 판정한다.

    예: demo-{{ .user }} 의 planner-backend → `oc get Deployment -A --field-selector metadata.name=planner-backend`
    다른 점검이나 labelSelector 를 쓰는 점검은 None 을 돌려 사용자별로 점검한다.
    """
    check = column["check"]
    if check["type"] != "resource" or check.get("labelSelector") or not check.get("kind"):
        return None
    name, namespace = check.get("name", ""), check.get("namespace", "")
    args = ["get", check["kind"], *(["-A"] if namespace else [])]
    if name and "{{" not in name:
        args += ["--field-selector", f"metadata.name={name}"]
    try:
        items = oc_json(args)["items"]
    except KubeError as exc:
        return {user: {"s": "error", "o": str(exc)[:200]} for user in users}
    cells = {}
    for user in users:
        params = checks.Context(domain=domain, user=user).render({k: v for k, v in check.items() if k != "type"})
        matched = [item for item in items
                   if (not params.get("namespace") or item["metadata"].get("namespace") == params["namespace"])
                   and (not params.get("name") or item["metadata"]["name"] == params["name"])]
        passed, observed = checks.resource_verdict(params, matched)
        cells[user] = {"s": "done" if passed else "todo", "o": observed}
    return cells


def _check_cell(user: str, column: dict, domain: str) -> tuple[str, str, dict]:
    check = column["check"]
    params = {k: v for k, v in check.items() if k != "type"}
    try:
        passed, observed = checks.run(check["type"], params, checks.Context(domain=domain, user=user))
    except checks.CheckError as exc:
        return user, column["id"], {"s": "error", "o": str(exc)[:200]}
    return user, column["id"], {"s": "done" if passed else "todo", "o": observed}


def run(workshop_id: str, domain: str) -> dict:
    state = editor_state()
    workshop = state["workshops"].get(workshop_id)
    if workshop is None:
        raise KeyError(workshop_id)
    users = expected_users(workshop)
    columns, definitions = checkpoint_columns(workshop, state["catalog"], load_overrides())
    try:
        showroom = showroom_status(users)
    except KubeError:
        showroom = {user: "unknown" for user in users}

    cells: dict[str, dict] = {user: {} for user in users}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        batched = {column["id"]: pool.submit(_batch_resource_column, column, users, domain) for column in columns}
        single = []
        for column in columns:
            result = batched[column["id"]].result()
            if result is None:
                single += [pool.submit(_check_cell, user, column, domain) for user in users]
            else:
                for user, cell in result.items():
                    cells[user][column["id"]] = cell
        for future in single:
            user, column_id, cell = future.result()
            cells[user][column_id] = cell

    rows = [{"user": user, "showroom": showroom[user], "cells": cells[user],
             "done": sum(1 for c in cells[user].values() if c["s"] == "done")} for user in users]
    totals = {column["id"]: sum(1 for row in rows if row["cells"][column["id"]]["s"] == "done") for column in columns}
    public_columns = [{k: v for k, v in column.items() if k != "check"} for column in columns]
    return {
        "workshop": workshop_id, "title": workshop["title"], "domain": domain,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "deployed": (state["deploy"] or {}).get("workshop") == workshop_id,
        "columns": public_columns, "definitions": definitions, "rows": rows, "totals": totals,
    }
