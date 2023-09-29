from __future__ import annotations

from pathlib import Path


def convert_str_or_path_to_absolute_path(str_or_path: str | Path) -> Path:
    if isinstance(str_or_path, Path):
        return str_or_path.absolute()

    path_ = Path(str_or_path)
    return path_.absolute()
