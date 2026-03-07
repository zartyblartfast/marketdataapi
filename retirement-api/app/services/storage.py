import json
import tempfile
from pathlib import Path
from typing import Any
from app.config import Config
from app.utils.logging_setup import log


def get_data_dir() -> Path:
    path = Config.DATA_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(filename: str, payload: Any) -> None:
    """Write JSON atomically: write to temp file then rename."""
    target = get_data_dir() / filename
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=get_data_dir(), suffix=".tmp"
        )
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        Path(tmp_path).rename(target)
        log.info(f"Written {filename}")
    except Exception as e:
        log.error(f"Failed to write {filename}: {e}")
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass
        raise


def read_json(filename: str) -> Any:
    """Read a cached JSON file. Returns None if missing."""
    path = get_data_dir() / filename
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
