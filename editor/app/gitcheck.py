"""카탈로그 등록 전에 git 저장소가 Showroom(Antora) 형식인지 확인한다."""
import os
import subprocess
import tempfile
from pathlib import Path

import yaml

CLONE_TIMEOUT = 90


class RepoError(Exception):
    pass


def _git(args: list[str], cwd: str | None = None) -> str:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "HOME": tempfile.gettempdir()}
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, env=env, capture_output=True, text=True,
            timeout=CLONE_TIMEOUT, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RepoError("저장소를 가져오는 데 시간이 너무 오래 걸립니다") from exc
    if result.returncode != 0:
        raise RepoError(result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "git 실패")
    return result.stdout.strip()


def inspect_repo(url: str, ref: str, start_path: str) -> dict:
    if ".." in Path(start_path).parts:
        raise RepoError("startPath 에 '..' 을 쓸 수 없습니다")
    with tempfile.TemporaryDirectory() as tmp:
        repo = os.path.join(tmp, "repo")
        _git(["clone", "--quiet", "--depth", "1", "--single-branch", "--branch", ref, url, repo])
        descriptor = Path(repo) / start_path / "antora.yml"
        if not descriptor.is_file():
            raise RepoError(f"{start_path}/antora.yml 이 없습니다. Showroom(Antora) 형식의 저장소가 아닙니다")
        try:
            data = yaml.safe_load(descriptor.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise RepoError(f"antora.yml 을 읽을 수 없습니다: {exc}") from exc
        return {
            "title": str(data.get("title") or data.get("name") or ""),
            "component": str(data.get("name") or ""),
            "commit": _git(["rev-parse", "--short=12", "HEAD"], cwd=repo),
        }
