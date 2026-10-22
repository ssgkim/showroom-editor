"""워크샵 정의 읽기: 에디터 카탈로그 + 저장소의 workshop.yaml + Ops Hub 덮어쓰기."""
import json
import os
import subprocess
import tempfile
import threading
from pathlib import Path

from .kube import oc, oc_json
from .schemas import DefinitionError, WorkshopDefinition, parse_definition

EDITOR_NAMESPACE = os.environ.get("EDITOR_NAMESPACE", "showroom-editor")
EDITOR_STATE = "showroom-editor-state"
OPS_NAMESPACE = os.environ.get("OPS_NAMESPACE", "workshop-ops")
OVERRIDES = "workshop-ops-overrides"
DEFINITION_FILE = "workshop.yaml"
CLONE_TIMEOUT = 60

_repo_cache: dict[tuple[str, str, str], str | None] = {}
_lock = threading.Lock()


def editor_state() -> dict:
    obj = oc_json(["get", "configmap", EDITOR_STATE, "-n", EDITOR_NAMESPACE], allow_missing=True)
    raw = (obj or {}).get("data", {}).get("state.json", "{}")
    state = json.loads(raw)
    return {"catalog": state.get("catalog", {}), "workshops": state.get("workshops", {}),
            "deploy": state.get("deploy"), "preview": state.get("preview")}


def load_overrides() -> dict[str, str]:
    obj = oc_json(["get", "configmap", OVERRIDES, "-n", OPS_NAMESPACE], allow_missing=True)
    return dict((obj or {}).get("data", {}))


def save_override(name: str, text: str | None) -> None:
    """text 가 None 이면 덮어쓰기를 지운다."""
    with _lock:
        current = load_overrides()
        updated = {k: v for k, v in current.items() if k != name}
        if text is not None:
            updated[name] = text
        manifest = {
            "apiVersion": "v1", "kind": "ConfigMap",
            "metadata": {"name": OVERRIDES, "namespace": OPS_NAMESPACE},
            "data": updated,
        }
        oc(["apply", "-f", "-"], stdin=json.dumps(manifest))


def _fetch_repo_file(url: str, ref: str, commit: str) -> str | None:
    """저장소 루트의 workshop.yaml. 없으면 None. 커밋 단위로 캐시한다."""
    key = (url, ref, commit)
    if key in _repo_cache:
        return _repo_cache[key]
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "HOME": tempfile.gettempdir()}
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", "--single-branch", "--branch", ref, url, tmp],
            env=env, capture_output=True, text=True, timeout=CLONE_TIMEOUT, check=False,
        )
        if result.returncode != 0:
            raise DefinitionError(f"저장소를 가져오지 못했습니다: {result.stderr.strip().splitlines()[-1:]}")
        path = Path(tmp) / DEFINITION_FILE
        text = path.read_text(encoding="utf-8") if path.is_file() else None
    _repo_cache[key] = text
    return text


def resolve(name: str, entry: dict, overrides: dict[str, str]) -> dict:
    """콘텐츠 하나의 정의. source: override | repo | none"""
    if name in overrides:
        source, text = "override", overrides[name]
    else:
        try:
            text = _fetch_repo_file(entry["repoUrl"], entry["repoRef"], entry.get("commit", ""))
        except (DefinitionError, subprocess.TimeoutExpired) as exc:
            return {"name": name, "source": "none", "text": "", "definition": None, "error": str(exc)}
        source = "repo" if text else "none"
    if not text:
        return {"name": name, "source": "none", "text": "", "definition": None, "error": None}
    try:
        definition: WorkshopDefinition | None = parse_definition(text)
        error = None
    except DefinitionError as exc:
        definition, error = None, str(exc)
    return {"name": name, "source": source, "text": text, "definition": definition, "error": error}
