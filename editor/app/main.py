"""Showroom Editor API: 카탈로그 → 워크샵 구성 → 미리보기 → 배포."""
import logging
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path as PathParam
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import deployer, gitcheck, overlays, repofiles, status, store
from .kube import KubeError, route_url
from .schemas import NAME_PATTERN, CatalogIn, PageIn, WorkshopIn

logger = logging.getLogger("showroom-editor")
STATIC_DIR = Path(__file__).parent / "static"
Name = Annotated[str, PathParam(pattern=NAME_PATTERN)]
Role = Annotated[str, PathParam(pattern="^(preview|deploy)$")]
ManagedNamespace = Annotated[str, PathParam(pattern=r"^showroom-[a-z0-9-]+$")]
OPS_HUB_ROUTE = ("workshop-ops", "workshop-ops")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@lru_cache(maxsize=1)
def _cluster() -> dict:
    return deployer.cluster_info()


def _fail(exc: Exception, code: int = 500) -> HTTPException:
    logger.warning("요청 실패: %s", exc)
    return HTTPException(status_code=code, detail=str(exc))


def _workshop_or_404(state: dict, wid: str) -> dict:
    workshop = state["workshops"].get(wid)
    if workshop is None:
        raise HTTPException(status_code=404, detail=f"워크샵이 없습니다: {wid}")
    return workshop


def _apply_workshop(wid: str, role: str) -> dict:
    state = store.load()
    workshop = _workshop_or_404(state, wid)
    try:
        values = deployer.build_values(state, workshop, role, _cluster(), overlays.for_workshop(wid))
        result = deployer.apply(values, role)
    except ValueError as exc:
        raise _fail(exc, 400) from exc
    except KubeError as exc:
        raise _fail(exc) from exc
    record = {"workshop": wid, "title": workshop["title"], "contents": workshop["contents"], "at": _now()}
    store.update(lambda s: {**s, role: record})
    return {**result, "record": record}


def _content_repo(wid: str, content: str) -> tuple[dict, Path, str]:
    """워크샵에 포함된 콘텐츠의 (카탈로그 항목, 저장소 작업 디렉터리, 커밋)."""
    state = store.load()
    workshop = _workshop_or_404(state, wid)
    entry = state["catalog"].get(content)
    if entry is None or content not in workshop["contents"]:
        raise HTTPException(status_code=404, detail=f"워크샵에 포함되지 않은 콘텐츠입니다: {content}")
    try:
        repo, commit = repofiles.checkout(entry["repoUrl"], entry["repoRef"])
    except gitcheck.RepoError as exc:
        raise _fail(exc, 502) from exc
    return entry, repo, commit


def _checked_path(entry: dict, path: str) -> str:
    try:
        return repofiles.check_page_path(path, entry["startPath"])
    except ValueError as exc:
        raise _fail(exc, 400) from exc


def create_app() -> FastAPI:
    app = FastAPI(title="Showroom Editor")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    @app.get("/api/state")
    def get_state() -> dict:
        try:
            return {**store.load(), "cluster": _cluster(), "edits": overlays.counts(overlays.load_all())}
        except KubeError as exc:
            raise _fail(exc) from exc

    @app.post("/api/catalog")
    def upsert_catalog(item: CatalogIn) -> dict:
        try:
            info = gitcheck.inspect_repo(item.repoUrl, item.repoRef, item.startPath)
        except gitcheck.RepoError as exc:
            raise _fail(exc, 400) from exc
        entry = {
            **item.model_dump(exclude={"name"}),
            "title": item.title or info["title"] or item.name,
            "commit": info["commit"],
            "checkedAt": _now(),
        }
        store.update(lambda s: {**s, "catalog": {**s["catalog"], item.name: entry}})
        return {"name": item.name, **entry}

    @app.delete("/api/catalog/{name}")
    def delete_catalog(name: Name) -> dict:
        users = [wid for wid, w in store.load()["workshops"].items() if name in w["contents"]]
        if users:
            raise HTTPException(status_code=409, detail=f"워크샵에서 사용 중입니다: {', '.join(users)}")
        store.update(lambda s: {**s, "catalog": {k: v for k, v in s["catalog"].items() if k != name}})
        return {"deleted": name}

    @app.put("/api/workshops/{wid}")
    def save_workshop(wid: Name, body: WorkshopIn) -> dict:
        missing = [c for c in body.contents if c not in store.load()["catalog"]]
        if missing:
            raise HTTPException(status_code=400, detail=f"카탈로그에 없는 콘텐츠: {', '.join(missing)}")
        workshop = {**body.model_dump(), "updatedAt": _now()}
        store.update(lambda s: {**s, "workshops": {**s["workshops"], wid: workshop}})
        return {"id": wid, **workshop}

    @app.delete("/api/workshops/{wid}")
    def delete_workshop(wid: Name) -> dict:
        deployed = store.load().get("deploy") or {}
        if deployed.get("workshop") == wid:
            raise HTTPException(status_code=409, detail="배포 중인 워크샵은 삭제할 수 없습니다. 먼저 배포를 해제하세요")
        store.update(lambda s: {**s, "workshops": {k: v for k, v in s["workshops"].items() if k != wid}})
        overlays.drop_workshop(wid)
        return {"deleted": wid}

    @app.post("/api/workshops/{wid}/preview")
    def preview(wid: Name) -> dict:
        return _apply_workshop(wid, "preview")

    @app.post("/api/workshops/{wid}/deploy")
    def deploy(wid: Name) -> dict:
        return _apply_workshop(wid, "deploy")

    @app.delete("/api/roles/{role}")
    def undeploy(role: Role) -> dict:
        try:
            removed = deployer.remove(role)
        except KubeError as exc:
            raise _fail(exc) from exc
        store.update(lambda s: {**s, role: None})
        return {"removed": removed}

    @app.post("/api/roles/{role}/restart")
    def restart(role: Role) -> dict:
        try:
            return {"restarted": deployer.restart(role)}
        except KubeError as exc:
            raise _fail(exc) from exc

    @app.get("/api/status")
    def get_status() -> dict:
        try:
            return status.collect()
        except KubeError as exc:
            raise _fail(exc) from exc

    @app.get("/api/logs/{namespace}")
    def get_logs(namespace: ManagedNamespace) -> dict:
        try:
            return status.build_logs(namespace)
        except PermissionError as exc:
            raise _fail(exc, 403) from exc
        except KubeError as exc:
            raise _fail(exc) from exc

    @app.get("/api/workshops/{wid}/pages/{content}")
    def list_pages(wid: Name, content: Name) -> dict:
        entry, repo, commit = _content_repo(wid, content)
        edited = overlays.for_workshop(wid).get(content, {})
        pages = []
        for path in repofiles.list_pages(repo, entry["startPath"]):
            item = edited.get(path)
            stale = bool(item) and repofiles.read_page(repo, path)[1] != item["baseSha"]
            pages.append({"path": path, "edited": bool(item), "stale": stale})
        missing = [{"path": p, "edited": True, "stale": True} for p in edited if p not in {x["path"] for x in pages}]
        return {"commit": commit[:12], "pages": pages + missing}

    @app.get("/api/workshops/{wid}/pages/{content}/file")
    def get_page(wid: Name, content: Name, path: str) -> dict:
        entry, repo, _commit = _content_repo(wid, content)
        path = _checked_path(entry, path)
        try:
            original, sha = repofiles.read_page(repo, path)
        except FileNotFoundError:
            original, sha = None, None
        item = overlays.for_workshop(wid).get(content, {}).get(path)
        return {"path": path, "original": original, "edited": item["text"] if item else None,
                "updatedAt": item["updatedAt"] if item else None,
                "stale": bool(item) and item["baseSha"] != sha}

    @app.put("/api/workshops/{wid}/pages/{content}/file")
    def put_page(wid: Name, content: Name, body: PageIn) -> dict:
        entry, repo, _commit = _content_repo(wid, content)
        path = _checked_path(entry, body.path)
        try:
            original, sha = repofiles.read_page(repo, path)
        except FileNotFoundError as exc:
            raise _fail(ValueError(f"원본 저장소에 없는 파일입니다: {path}"), 404) from exc
        if body.text == original:
            raise HTTPException(status_code=400, detail="원본과 같습니다. 되돌리려면 '원본으로 되돌리기'를 누르세요")
        try:
            overlays.put(wid, content, path, {"text": body.text, "baseSha": sha, "updatedAt": _now()})
        except ValueError as exc:
            raise _fail(exc, 413) from exc
        except KubeError as exc:
            raise _fail(exc) from exc
        return {"saved": path}

    @app.delete("/api/workshops/{wid}/pages/{content}/file")
    def delete_page(wid: Name, content: Name, path: str) -> dict:
        _workshop_or_404(store.load(), wid)
        overlays.remove(wid, content, path)
        return {"reverted": path}

    @app.get("/api/links")
    def links() -> dict:
        return {"opsHub": route_url(*OPS_HUB_ROUTE)}

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
