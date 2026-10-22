"""미리보기/배포 Showroom의 사용자별 상태를 모은다."""
import re

from .deployer import ROLE_LABEL
from .kube import KubeError, oc, oc_json

APP_LABEL = "app.kubernetes.io/name=showroom"
STEP_LABELS = {"clone": "저장소 가져오는 중", "build": "Antora 빌드 중"}
LOG_TAIL = "80"


def _user_sort_key(ns: str) -> tuple[str, int]:
    match = re.match(r"^(.*?)(\d+)$", ns)
    return (match.group(1), int(match.group(2))) if match else (ns, 0)


def _latest_pods(pods: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for pod in pods:
        if pod["metadata"].get("deletionTimestamp"):
            continue
        ns = pod["metadata"]["namespace"]
        current = latest.get(ns)
        if current is None or pod["metadata"]["creationTimestamp"] > current["metadata"]["creationTimestamp"]:
            latest[ns] = pod
    return latest


def _pod_phase(pod: dict | None) -> tuple[str, str]:
    if pod is None:
        return "pending", "Pod 생성 대기"
    status = pod.get("status", {})
    for init in status.get("initContainerStatuses", []):
        state, last = init.get("state", {}), init.get("lastState", {})
        step = STEP_LABELS.get(init["name"], init["name"])
        failed = state.get("terminated", {}).get("exitCode", 0) != 0 or (
            state.get("waiting", {}).get("reason") == "CrashLoopBackOff"
            or last.get("terminated", {}).get("exitCode", 0) != 0
        )
        if failed:
            return "failed", f"{step} 실패"
        if "running" in state or "waiting" in state:
            return "building", step
    ready = all(c.get("ready") for c in status.get("containerStatuses", [])) and status.get("containerStatuses")
    return ("ready", "준비됨") if ready else ("starting", "서비스 시작 중")


def collect() -> dict:
    namespaces = oc_json(["get", "namespaces", "-l", ROLE_LABEL])["items"]
    pods = _latest_pods(oc_json(["get", "pods", "-A", "-l", APP_LABEL])["items"])
    routes = oc_json(["get", "routes", "-A", "--field-selector", "metadata.name=showroom"])["items"]
    hosts = {r["metadata"]["namespace"]: r["spec"].get("host", "") for r in routes}

    result: dict[str, list] = {"preview": [], "deploy": []}
    for ns_obj in namespaces:
        meta = ns_obj["metadata"]
        ns, role = meta["name"], meta["labels"].get(ROLE_LABEL)
        if role not in result:
            continue
        phase, detail = _pod_phase(pods.get(ns))
        if meta.get("deletionTimestamp"):
            phase, detail = "terminating", "삭제 중"
        host = hosts.get(ns)
        result[role].append({
            "namespace": ns,
            "user": meta["labels"].get("workshop-user", ns),
            "phase": phase,
            "detail": detail,
            "url": f"https://{host}" if host else "",
        })
    for role in result:
        result[role].sort(key=lambda item: _user_sort_key(item["namespace"]))
    return result


def build_logs(namespace: str) -> dict:
    labels = oc_json(["get", "namespace", namespace])["metadata"].get("labels", {})
    if ROLE_LABEL not in labels:
        raise PermissionError("에디터가 관리하는 네임스페이스가 아닙니다")
    pod = _latest_pods(oc_json(["get", "pods", "-n", namespace, "-l", APP_LABEL])["items"]).get(namespace)
    if pod is None:
        return {}
    logs = {}
    for container in STEP_LABELS:
        try:
            logs[container] = oc(["logs", "-n", namespace, pod["metadata"]["name"], "-c", container, "--tail", LOG_TAIL])
        except KubeError as exc:
            logs[container] = f"(로그 없음: {exc})"
    return logs
