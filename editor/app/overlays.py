"""행사별 페이지 수정(오버레이). 원본 저장소는 그대로 두고 빌드할 때 파일을 덮어쓴다.

구조: {워크샵 ID: {콘텐츠 이름: {파일 경로: {text, baseSha, updatedAt}}}}
baseSha 는 수정할 때의 원본 blob 해시로, 원본이 바뀌었는지 알려 주는 데 쓴다.
"""
import json
import threading

from .kube import oc, oc_json
from .store import NAMESPACE

CONFIGMAP = "showroom-editor-overlays"
# ConfigMap 한도(1MiB)보다 여유 있게 막는다
MAX_BYTES = 900_000

_lock = threading.Lock()


def load_all() -> dict:
    obj = oc_json(["get", "configmap", CONFIGMAP, "-n", NAMESPACE], allow_missing=True)
    return json.loads((obj or {}).get("data", {}).get("overlays.json", "{}"))


def for_workshop(wid: str) -> dict:
    return load_all().get(wid, {})


def _save(data: dict) -> None:
    body = json.dumps(data, ensure_ascii=False)
    if len(body.encode("utf-8")) > MAX_BYTES:
        raise ValueError("수정한 페이지가 너무 많거나 큽니다 (전체 900KB 이하)")
    manifest = {"apiVersion": "v1", "kind": "ConfigMap",
                "metadata": {"name": CONFIGMAP, "namespace": NAMESPACE},
                "data": {"overlays.json": body}}
    oc(["apply", "-f", "-"], stdin=json.dumps(manifest))


def put(wid: str, content: str, path: str, entry: dict) -> None:
    with _lock:
        data = load_all()
        workshop = data.get(wid, {})
        files = {**workshop.get(content, {}), path: entry}
        _save({**data, wid: {**workshop, content: files}})


def remove(wid: str, content: str, path: str) -> None:
    with _lock:
        data = load_all()
        workshop = data.get(wid, {})
        files = {p: e for p, e in workshop.get(content, {}).items() if p != path}
        workshop = {**workshop, content: files} if files else {c: f for c, f in workshop.items() if c != content}
        _save({**data, wid: workshop} if workshop else {w: v for w, v in data.items() if w != wid})


def drop_workshop(wid: str) -> None:
    with _lock:
        data = load_all()
        if wid in data:
            _save({w: v for w, v in data.items() if w != wid})


def counts(data: dict) -> dict:
    """화면 배지용: {워크샵: {콘텐츠: 수정한 파일 수}}"""
    return {wid: {c: len(files) for c, files in contents.items()} for wid, contents in data.items()}
