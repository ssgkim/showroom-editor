"""에디터 상태(카탈로그, 워크샵 구성, 배포 기록)를 ConfigMap 하나에 저장한다."""
import copy
import json
import os
import threading
from typing import Callable

from .kube import oc, oc_json

NAMESPACE = os.environ.get("EDITOR_NAMESPACE", "showroom-editor")
CONFIGMAP = "showroom-editor-state"
# preview / deploy: 마지막으로 적용한 워크샵 기록 (역할 이름과 같은 키)
EMPTY_STATE = {"catalog": {}, "workshops": {}, "preview": None, "deploy": None}

_lock = threading.Lock()


def load() -> dict:
    obj = oc_json(["get", "configmap", CONFIGMAP, "-n", NAMESPACE], allow_missing=True)
    raw = (obj or {}).get("data", {}).get("state.json", "{}")
    return {**copy.deepcopy(EMPTY_STATE), **json.loads(raw)}


def _save(state: dict) -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": CONFIGMAP, "namespace": NAMESPACE},
        "data": {"state.json": json.dumps(state, ensure_ascii=False, indent=2)},
    }
    oc(["apply", "-f", "-"], stdin=json.dumps(manifest))


def update(change: Callable[[dict], dict]) -> dict:
    """현재 상태를 받아 새 상태를 돌려주는 change 를 적용해 저장한다."""
    with _lock:
        new_state = change(load())
        _save(new_state)
        return new_state
