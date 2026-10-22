"""갤러리: 에디터 카탈로그의 콘텐츠를 워크샵 정의(about, 요구 사항, 체크포인트)와 함께 보여 준다."""
from .definitions import resolve

READINESS_ORDER = ("blocked", "caution", "ready")


def _readiness(name: str, reports: dict[str, dict]) -> dict | None:
    """이 콘텐츠를 포함한 가장 최근 사전 점검에서 콘텐츠 항목만 모은 결과."""
    latest = max((r for r in reports.values() if name in r["contents"]), key=lambda r: r["at"], default=None)
    if latest is None:
        return None
    results = [r for r in latest["results"] if r["scope"] == name]
    counts = {key: sum(1 for r in results if r["status"] == key) for key in ("pass", "warn", "fail", "error")}
    verdict = "blocked" if counts["fail"] else "caution" if counts["warn"] + counts["error"] else "ready"
    return {"verdict": verdict, "at": latest["at"], "workshop": latest["workshop"], **counts}


def build(state: dict, overrides: dict[str, str], reports: dict[str, dict]) -> list[dict]:
    deployed = (state.get("deploy") or {}).get("workshop")
    cards = []
    for name, entry in state["catalog"].items():
        resolved = resolve(name, entry, overrides)
        definition = resolved["definition"]
        workshops = [{"id": wid, "title": w["title"], "deployed": wid == deployed}
                     for wid, w in state["workshops"].items() if name in w["contents"]]
        cards.append({
            "name": name,
            "title": entry.get("title") or name,
            "repoUrl": entry["repoUrl"],
            "repoRef": entry["repoRef"],
            "commit": entry.get("commit", ""),
            "source": resolved["source"],
            "error": resolved["error"],
            "about": definition.about.model_dump() if definition else None,
            "requirements": [{"name": r.name, "severity": r.severity} for r in definition.requirements] if definition else [],
            "checkpoints": [{"module": str(c.module), "name": c.name} for c in definition.checkpoints] if definition else [],
            "workshops": workshops,
            "readiness": _readiness(name, reports),
        })
    return sorted(cards, key=lambda card: (not any(w["deployed"] for w in card["workshops"]), card["title"]))
