from __future__ import annotations

import json
from pathlib import Path

from danycode.config import SESSIONS_DIR


class Session:
    def __init__(self, name: str):
        self.name = name
        self.path = SESSIONS_DIR / f"{name}.json"
        self.messages: list[dict] = []
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                self.messages = json.load(f)

    def add(self, message: dict) -> None:
        self.messages.append(message)
        self.save()

    def add_many(self, messages: list[dict]) -> None:
        self.messages.extend(messages)
        self.save()

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.messages, f, ensure_ascii=False, indent=2)

    def clear(self) -> None:
        self.messages = []
        self.save()

    @staticmethod
    def list_sessions() -> list[str]:
        if not SESSIONS_DIR.exists():
            return []
        return [p.stem for p in SESSIONS_DIR.glob("*.json")]
