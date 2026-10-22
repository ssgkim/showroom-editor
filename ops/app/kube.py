"""oc CLI 호출 래퍼. Pod 안에서는 ServiceAccount 토큰으로 인증된다."""
import json
import subprocess

DEFAULT_TIMEOUT = 120


class KubeError(Exception):
    pass


def run(cmd: list[str], stdin: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    try:
        result = subprocess.run(
            cmd, input=stdin, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise KubeError(f"{cmd[0]} 시간 초과 ({timeout}s)") from exc
    if result.returncode != 0:
        raise KubeError(result.stderr.strip() or f"{cmd[0]} 실패 (exit {result.returncode})")
    return result.stdout


def oc(args: list[str], stdin: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    return run(["oc", *args], stdin=stdin, timeout=timeout)


def oc_json(args: list[str], allow_missing: bool = False) -> dict | None:
    try:
        out = oc([*args, "-o", "json"])
    except KubeError as exc:
        if allow_missing and "NotFound" in str(exc):
            return None
        raise
    return json.loads(out)
