import os
from pathlib import Path


_ENV_LOADED = False
_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _REPO_ROOT / ".env"


def _strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()
    if "=" not in stripped:
        return None

    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    return key, _strip_optional_quotes(value.strip())


def load_repo_env() -> None:
    global _ENV_LOADED

    if _ENV_LOADED:
        return

    if _ENV_FILE.exists():
        for raw_line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(raw_line)
            if parsed is None:
                continue
            key, value = parsed
            if key in os.environ:
                continue
            os.environ[key] = value

    _ENV_LOADED = True


def get_tushare_token(token: str | None = None, required: bool = True) -> str | None:
    load_repo_env()
    resolved = token or os.getenv("TUSHARE_TOKEN")
    if resolved or not required:
        return resolved
    raise RuntimeError(
        "Missing TUSHARE_TOKEN. Add it to the repo root .env file or pass --token."
    )


def configure_tushare(ts_module, token: str | None = None) -> str:
    resolved = get_tushare_token(token=token, required=True)
    ts_module.set_token(resolved)
    return resolved


def get_tushare_pro(ts_module, token: str | None = None):
    configure_tushare(ts_module, token=token)
    return ts_module.pro_api()