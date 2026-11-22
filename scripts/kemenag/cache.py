"""Read and write the raw Kemenag scrape cache."""

import json
from pathlib import Path
from typing import Any

from scripts.kemenag.config import ROOT


def load_cache(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["verse_key"]: row for row in data.get("responses", [])}


def save_cache(rows: list[dict[str, Any]], path: Path, manifest_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "provider": "Quran Kemenag",
                "authority": "LPMQ Kementerian Agama RI",
                "manifest": str(manifest_path.relative_to(ROOT)),
                "responses": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
