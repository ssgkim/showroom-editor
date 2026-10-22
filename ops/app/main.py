"""Workshop Ops Hub API. 1차: 사전 점검."""
import logging
import threading
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path as PathParam
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import preflight
from .definitions import editor_state, load_overrides, resolve, save_override
from .kube import KubeError, oc, route_url
from .schemas import DefinitionError, DefinitionIn, parse_definition

logger = logging.getLogger("workshop-ops")
STATIC_DIR = Path(__file__).parent / "static"
NAME_PATTERN = r"^[a-z0-9][a-z0-9-]{0,40}$"
Name = Annotated[str, PathParam(pattern=NAME_PATTERN)]
EDITOR_ROUTE = ("showroom-editor", "showroom-editor")

_reports: dict[str, dict] = {}
_reports_lock = threading.Lock()


@lru_cache(maxsize=1)
def _domain() -> str:
    return oc(["get", "ingresses.config.openshift.io", "cluster", "-o", "jsonpath={.spec.domain}"]).strip()


def _fail(exc: Exception, code: int = 500) -> HTTPException:
    logger.warning("요청 실패: %s", exc)
    return HTTPException(status_code=code, detail=str(exc))


def _catalog_entry(name: str) -> dict:
    entry = editor_state()["catalog"].get(name)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"에디터 카탈로그에 없는 콘텐츠입니다: {name}")
    return entry


def create_app() -> FastAPI:
    app = FastAPI(title="Workshop Ops Hub")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    @app.get("/api/overview")
    def overview() -> dict:
        try:
            state = editor_state()
            domain = _domain()
        except KubeError as exc:
            raise _fail(exc) from exc
        with _reports_lock:
            last = {wid: {"at": r["at"], "summary": r["summary"]} for wid, r in _reports.items()}
        return {"domain": domain, "workshops": state["workshops"], "catalog": state["catalog"],
                "deployed": (state["deploy"] or {}).get("workshop"), "lastRuns": last}

    @app.get("/api/definitions/{name}")
    def get_definition(name: Name) -> dict:
        try:
            resolved = resolve(name, _catalog_entry(name), load_overrides())
        except KubeError as exc:
            raise _fail(exc) from exc
        return {k: v for k, v in resolved.items() if k != "definition"}

    @app.put("/api/definitions/{name}")
    def put_definition(name: Name, body: DefinitionIn) -> dict:
        _catalog_entry(name)
        try:
            parse_definition(body.text)
        except DefinitionError as exc:
            raise _fail(exc, 400) from exc
        save_override(name, body.text)
        return {"name": name, "source": "override"}

    @app.delete("/api/definitions/{name}")
    def delete_definition(name: Name) -> dict:
        save_override(name, None)
        return {"name": name, "source": "repo"}

    @app.post("/api/preflight/{wid}")
    def run_preflight(wid: Name) -> dict:
        try:
            report = preflight.run(wid, _domain())
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"에디터에 없는 워크샵입니다: {wid}") from exc
        except KubeError as exc:
            raise _fail(exc) from exc
        with _reports_lock:
            _reports[wid] = report
        return report

    @app.get("/api/preflight/{wid}")
    def last_preflight(wid: Name) -> dict:
        with _reports_lock:
            report = _reports.get(wid)
        if report is None:
            raise HTTPException(status_code=404, detail="아직 점검하지 않았습니다")
        return report

    @app.get("/api/preflight/{wid}/report.md", response_class=PlainTextResponse)
    def report_markdown(wid: Name) -> PlainTextResponse:
        report = last_preflight(wid)
        return PlainTextResponse(
            preflight.to_markdown(report, _domain()),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="preflight-{wid}.md"'},
        )

    @app.get("/api/links")
    def links() -> dict:
        return {"editor": route_url(*EDITOR_ROUTE)}

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
