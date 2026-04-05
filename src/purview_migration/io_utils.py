from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: str | Path, data: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_json(path: str | Path) -> Any:
    input_path = Path(path)
    return json.loads(input_path.read_text(encoding="utf-8"))
