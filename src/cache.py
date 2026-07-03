from __future__ import annotations

import json
import logging
from pathlib import Path


class SeenCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.logger = logging.getLogger(__name__)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text('{"seen_pmids": []}\n', encoding="utf-8")

    def load(self) -> set[str]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return {str(pmid) for pmid in payload.get("seen_pmids", [])}
        except Exception as exc:
            self.logger.warning("Failed to read seen cache %s: %s", self.path, exc)
            return set()

    def add(self, pmids: list[str]) -> None:
        seen = self.load()
        seen.update(str(pmid) for pmid in pmids if pmid)
        payload = {"seen_pmids": sorted(seen, key=lambda item: int(item) if item.isdigit() else item)}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
