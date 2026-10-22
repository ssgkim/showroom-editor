"""점검 엔진. 정해진 유형만 실행하며 클러스터는 읽기만 한다.

각 점검은 (통과 여부, 관찰한 값) 을 돌려준다. 점검 자체가 실패하면 CheckError 를 던진다.
"""
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from .kube import KubeError, oc, oc_json

HTTP_TIMEOUT = 8
REACHABLE_CODES = [200, 301, 302, 401, 403]
GPU_RESOURCE = "nvidia.com/gpu"
CSV_QUERY = ["get", "csv", "-A", "-l", "!olm.copiedFrom"]
CPU_UNITS = {"m": 0.001, "": 1.0}
MEMORY_UNITS = {"Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40, "K": 1e3, "M": 1e6, "G": 1e9, "": 1.0}


class CheckError(Exception):
    pass


@dataclass
class Context:
    """한 번의 점검 실행 동안 클러스터 조회 결과를 재사용한다."""
    domain: str
    user: str = ""
    _cache: dict = field(default_factory=dict)

    def cached(self, key: str, loader: Callable[[], object]) -> object:
        if key not in self._cache:
            self._cache[key] = loader()
        return self._cache[key]

    def placeholders(self) -> dict[str, str]:
        number = re.search(r"(\d+)$", self.user)
        digits = number.group(1) if number else ""
        return {"{{ .domain }}": self.domain, "{{ .user }}": self.user,
                "{{ .userNumber }}": str(int(digits)) if digits else "",
                "{{ .userNumber2 }}": f"{int(digits):02d}" if digits else ""}

    def render(self, value: object) -> object:
        if isinstance(value, str):
            for placeholder, replacement in self.placeholders().items():
                value = value.replace(placeholder, replacement)
            return value
        if isinstance(value, dict):
            return {k: self.render(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.render(v) for v in value]
        return value


def version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def parse_quantity(text: str, units: dict[str, float]) -> float:
    match = re.fullmatch(r"([0-9.]+)([A-Za-z]*)", str(text))
    if not match or match.group(2) not in units:
        raise CheckError(f"수량을 해석할 수 없습니다: {text}")
    return float(match.group(1)) * units[match.group(2)]


# ── 점검 유형 ──────────────────────────────────────────
def check_operator(params: dict, ctx: Context) -> tuple[bool, str]:
    package = params.get("package")
    if not package:
        raise CheckError("package 가 필요합니다")
    # 글로벌 Operator 의 CSV 는 모든 네임스페이스에 복사된다(olm.copiedFrom). 원본만 읽어야
    # 응답이 수백 MB 로 커지지 않는다.
    csvs = ctx.cached("csvs", lambda: oc_json(CSV_QUERY)["items"])
    matches = {c["metadata"]["name"]: c for c in csvs if c["metadata"]["name"].startswith(f"{package}.")}
    if not matches:
        return False, _subscription_hint(package, ctx)
    csv = sorted(matches.values(), key=lambda c: version_tuple(c["spec"].get("version", "0")))[-1]
    version, phase = csv["spec"].get("version", "?"), csv.get("status", {}).get("phase", "?")
    if phase != "Succeeded":
        return False, f"{csv['metadata']['name']} 상태 {phase}"
    minimum = params.get("minVersion")
    if minimum and version_tuple(version) < version_tuple(str(minimum)):
        return False, f"{version} 설치됨 (필요: {minimum} 이상)"
    return True, f"{version} 설치됨"


def _subscription_hint(package: str, ctx: Context) -> str:
    subs = ctx.cached("subs", lambda: oc_json(["get", "subscriptions.operators.coreos.com", "-A"])["items"])
    sub = next((s for s in subs if s["spec"].get("name") == package), None)
    if sub is None:
        return "설치되지 않음 (Subscription 없음)"
    failed = [c for c in sub.get("status", {}).get("conditions", [])
              if c.get("status") == "True" and c.get("type", "").endswith("Failed")]
    reason = f" · {failed[0]['type']}: {failed[0].get('reason', '')}" if failed else ""
    return f"Subscription 은 있으나 설치 미완료 (CSV 없음){reason}"


def check_cluster_version(params: dict, ctx: Context) -> tuple[bool, str]:
    version = oc(["get", "clusterversion", "version", "-o", "jsonpath={.status.desired.version}"]).strip()
    minimum = params.get("min")
    if minimum and version_tuple(version) < version_tuple(str(minimum)):
        return False, f"OpenShift {version} (필요: {minimum} 이상)"
    return True, f"OpenShift {version}"


def _nodes(ctx: Context) -> list[dict]:
    return ctx.cached("nodes", lambda: oc_json(["get", "nodes"])["items"])


def check_gpu_nodes(params: dict, ctx: Context) -> tuple[bool, str]:
    resource = params.get("resource", GPU_RESOURCE)
    counts = [int(n["status"].get("allocatable", {}).get(resource, "0")) for n in _nodes(ctx)]
    gpu_nodes = [c for c in counts if c > 0]
    minimum = int(params.get("min", 1))
    observed = f"GPU 노드 {len(gpu_nodes)}개, GPU {sum(gpu_nodes)}개 ({resource})"
    return len(gpu_nodes) >= minimum, observed


def _is_ready(obj: dict) -> bool:
    status = obj.get("status", {})
    if "replicas" in status or obj.get("kind") in {"Deployment", "StatefulSet"}:
        if status.get("availableReplicas", status.get("readyReplicas", 0)) >= 1:
            return True
    return any(c.get("type") in {"Ready", "Available"} and c.get("status") == "True"
               for c in status.get("conditions", []))


def check_resource(params: dict, ctx: Context) -> tuple[bool, str]:
    kind = params.get("kind")
    if not kind:
        raise CheckError("kind 가 필요합니다")
    args = ["get", kind]
    if params.get("name"):
        args.append(params["name"])
    if params.get("namespace"):
        args += ["-n", params["namespace"]]
    if params.get("labelSelector"):
        args += ["-l", params["labelSelector"]]
    target = f"{kind}/{params.get('name', '*')}" + (f" ({params['namespace']})" if params.get("namespace") else "")
    try:
        obj = oc_json(args, allow_missing=True)
    except KubeError as exc:
        raise CheckError(str(exc)) from exc
    items = (obj or {}).get("items", [obj] if obj else [])
    if not items:
        return False, f"{target} 없음"
    if params.get("ready"):
        ready = [i for i in items if _is_ready(i)]
        return bool(ready), f"{target} {'Ready' if ready else 'Ready 아님'}"
    return True, f"{target} {len(items)}개 있음"


def check_http(params: dict, ctx: Context) -> tuple[bool, str]:
    url = params.get("url", "")
    if not url.startswith(("https://", "http://")):
        raise CheckError("url 은 http(s):// 로 시작해야 합니다")
    expect = params.get("expect", REACHABLE_CODES)
    # 사내 인증서를 쓰는 클러스터가 많아 인증서 검증은 하지 않는다 (도달 여부만 확인)
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "workshop-ops-hub"})
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT, context=context) as response:
            code = response.status
    except urllib.error.HTTPError as exc:
        code = exc.code
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"접속 실패: {getattr(exc, 'reason', exc)}"
    return code in expect, f"HTTP {code}"


def check_capacity(params: dict, ctx: Context) -> tuple[bool, str]:
    users = int(params.get("users", 1))
    need_cpu = users * parse_quantity(params.get("cpuPerUser", "0"), CPU_UNITS)
    need_mem = users * parse_quantity(params.get("memoryPerUser", "0"), MEMORY_UNITS)
    workers = [n for n in _nodes(ctx)
               if not n["spec"].get("unschedulable")
               and not any(t.get("effect") == "NoSchedule" for t in n["spec"].get("taints", []))]
    names = {n["metadata"]["name"] for n in workers}
    alloc_cpu = sum(parse_quantity(n["status"]["allocatable"]["cpu"], CPU_UNITS) for n in workers)
    alloc_mem = sum(parse_quantity(n["status"]["allocatable"]["memory"], MEMORY_UNITS) for n in workers)
    pods = ctx.cached("pods", lambda: oc_json(["get", "pods", "-A", "--field-selector",
                                               "status.phase!=Succeeded,status.phase!=Failed"])["items"])
    used_cpu = used_mem = 0.0
    for pod in pods:
        if pod["spec"].get("nodeName") not in names:
            continue
        for container in pod["spec"].get("containers", []):
            requests = container.get("resources", {}).get("requests", {})
            used_cpu += parse_quantity(requests.get("cpu", "0"), CPU_UNITS)
            used_mem += parse_quantity(requests.get("memory", "0"), MEMORY_UNITS)
    free_cpu, free_mem = alloc_cpu - used_cpu, alloc_mem - used_mem
    observed = (f"여유 CPU {free_cpu:.1f} / 필요 {need_cpu:.1f} 코어 · "
                f"여유 메모리 {free_mem / 2**30:.1f} / 필요 {need_mem / 2**30:.1f} GiB ({users}명)")
    return free_cpu >= need_cpu and free_mem >= need_mem, observed


CHECKERS: dict[str, Callable[[dict, Context], tuple[bool, str]]] = {
    "operator": check_operator,
    "clusterVersion": check_cluster_version,
    "gpuNodes": check_gpu_nodes,
    "resource": check_resource,
    "http": check_http,
    "capacity": check_capacity,
}


def run(check_type: str, params: dict, ctx: Context) -> tuple[bool, str]:
    checker = CHECKERS.get(check_type)
    if checker is None:
        raise CheckError(f"알 수 없는 점검 유형: {check_type}")
    try:
        return checker(ctx.render(params), ctx)
    except KubeError as exc:
        raise CheckError(str(exc)) from exc
