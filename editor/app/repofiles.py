"""콘텐츠 저장소의 페이지 파일을 읽는다. 원격 커밋이 바뀔 때만 다시 clone 한다."""
import hashlib
import os
import shutil
import tempfile
import threading
from pathlib import Path, PurePosixPath

from .gitcheck import RepoError, _git

CACHE_DIR = Path(os.environ.get("REPO_CACHE_DIR", Path(tempfile.gettempdir()) / "showroom-editor-repos"))
PAGE_SUFFIX = ".adoc"

_lock = threading.Lock()


def blob_sha(data: bytes) -> str:
    """git 의 blob 해시와 같은 값. 원본이 바뀌었는지 비교할 때 쓴다."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _remote_commit(url: str, ref: str) -> str:
    out = _git(["ls-remote", url, ref])
    if not out:
        raise RepoError(f"{ref} 를 찾을 수 없습니다")
    return out.split()[0]


def checkout(url: str, ref: str) -> tuple[Path, str]:
    """(작업 디렉터리, 커밋) 을 돌려준다. 같은 커밋이면 캐시를 그대로 쓴다."""
    key = hashlib.sha256(f"{url}@{ref}".encode()).hexdigest()[:16]
    target = CACHE_DIR / key
    with _lock:
        commit = _remote_commit(url, ref)
        if (target / ".git").is_dir() and _git(["rev-parse", "HEAD"], cwd=str(target)) == commit:
            return target, commit
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fresh = Path(tempfile.mkdtemp(dir=CACHE_DIR))
        _git(["clone", "--quiet", "--depth", "1", "--single-branch", "--branch", ref, url, str(fresh / "repo")])
        shutil.rmtree(target, ignore_errors=True)
        (fresh / "repo").rename(target)
        shutil.rmtree(fresh, ignore_errors=True)
        return target, _git(["rev-parse", "HEAD"], cwd=str(target))


def check_page_path(path: str, start_path: str) -> str:
    """저장소 루트 기준 상대 경로. 콘텐츠 경로 아래의 .adoc 파일만 허용한다."""
    parts = PurePosixPath(path).parts
    root = PurePosixPath(start_path).parts
    if (not path or path.startswith("/") or ".." in parts or not path.endswith(PAGE_SUFFIX)
            or tuple(parts[:len(root)]) != root
            or not all(ch.isalnum() or ch in "._/-" for ch in path)):
        raise ValueError(f"수정할 수 없는 경로입니다: {path} ({start_path}/ 아래의 {PAGE_SUFFIX} 파일만 가능)")
    return path


def list_pages(repo: Path, start_path: str) -> list[str]:
    base = repo / start_path
    return sorted(p.relative_to(repo).as_posix() for p in base.rglob(f"*{PAGE_SUFFIX}") if p.is_file())


def read_page(repo: Path, path: str) -> tuple[str, str]:
    """(본문, blob 해시). 저장소에 없는 파일이면 FileNotFoundError."""
    file = (repo / path).resolve()
    if repo.resolve() not in file.parents or not file.is_file():
        raise FileNotFoundError(path)
    data = file.read_bytes()
    return data.decode("utf-8"), blob_sha(data)
