from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

CONFIG_DIR = Path.home() / ".danycode"
CONFIG_FILE = CONFIG_DIR / "config.toml"
SESSIONS_DIR = CONFIG_DIR / "sessions"

DEFAULTS = {
    "host": "http://localhost:11434",
    "model": "",
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "min_p": 0.0,
    "num_ctx": 8192,
    "num_predict": 4096,
    "seed": -1,
    "think": "false",
    "keep_alive": "5m",
    "system_prompt": "Coding assistant. Use tools. Be concise.",
    "mode": "ask",
}

VALID_MODES = ("yolo", "ask")
VALID_THINK = ("false", "true", "high", "medium", "low", "max")


@dataclass
class Config:
    host: str = DEFAULTS["host"]
    model: str = DEFAULTS["model"]
    temperature: float = DEFAULTS["temperature"]
    top_p: float = DEFAULTS["top_p"]
    top_k: int = DEFAULTS["top_k"]
    min_p: float = DEFAULTS["min_p"]
    num_ctx: int = DEFAULTS["num_ctx"]
    num_predict: int = DEFAULTS["num_predict"]
    seed: int = DEFAULTS["seed"]
    think: str = DEFAULTS["think"]
    keep_alive: str = DEFAULTS["keep_alive"]
    system_prompt: str = DEFAULTS["system_prompt"]
    mode: str = DEFAULTS["mode"]

    @classmethod
    def load(cls, overrides: dict | None = None) -> Config:
        data = dict(DEFAULTS)
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "rb") as f:
                file_cfg = tomllib.load(f)
            for key in DEFAULTS:
                if key in file_cfg:
                    data[key] = file_cfg[key]
        if overrides:
            for key, val in overrides.items():
                if val is not None:
                    data[key] = val
        return cls(**data)

    def ensure_dirs(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    def update(self, key: str, value: str) -> str | None:
        if key not in DEFAULTS:
            return f"Unknown parameter: {key}. Valid: {', '.join(DEFAULTS.keys())}"
        if key == "temperature":
            try:
                v = float(value)
                if not (0.0 <= v <= 2.0):
                    return "temperature must be between 0.0 and 2.0"
                self.temperature = v
            except ValueError:
                return "temperature must be a number"
        elif key == "top_p":
            try:
                v = float(value)
                if not (0.0 <= v <= 1.0):
                    return "top_p must be between 0.0 and 1.0"
                self.top_p = v
            except ValueError:
                return "top_p must be a number"
        elif key == "top_k":
            try:
                v = int(value)
                if v < 0:
                    return "top_k must be >= 0"
                self.top_k = v
            except ValueError:
                return "top_k must be an integer"
        elif key == "min_p":
            try:
                v = float(value)
                if not (0.0 <= v <= 1.0):
                    return "min_p must be between 0.0 and 1.0"
                self.min_p = v
            except ValueError:
                return "min_p must be a number"
        elif key == "num_ctx":
            try:
                v = int(value)
                if v <= 0:
                    return "num_ctx must be positive"
                self.num_ctx = v
            except ValueError:
                return "num_ctx must be an integer"
        elif key == "num_predict":
            try:
                v = int(value)
                if v <= 0:
                    return "num_predict must be positive"
                self.num_predict = v
            except ValueError:
                return "num_predict must be an integer"
        elif key == "seed":
            try:
                v = int(value)
                self.seed = v
            except ValueError:
                return "seed must be an integer (-1 for random)"
        elif key == "think":
            if value not in VALID_THINK:
                return f"think must be one of: {', '.join(VALID_THINK)}"
            self.think = value
        elif key == "keep_alive":
            self.keep_alive = value
        elif key == "mode":
            if value not in VALID_MODES:
                return f"mode must be one of: {', '.join(VALID_MODES)}"
            self.mode = value
        elif key == "model":
            self.model = value
        elif key == "host":
            self.host = value
        elif key == "system_prompt":
            self.system_prompt = value
        return None

    def save(self) -> None:
        lines = []
        for f in fields(self):
            val = getattr(self, f.name)
            if isinstance(val, str):
                escaped = val.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{f.name} = "{escaped}"')
            elif isinstance(val, float):
                lines.append(f"{f.name} = {val}")
            elif isinstance(val, int):
                lines.append(f"{f.name} = {val}")
        CONFIG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def display(self) -> list[tuple[str, str]]:
        return [
            ("host", self.host),
            ("model", self.model or "(auto)"),
            ("temperature", str(self.temperature)),
            ("top_p", str(self.top_p)),
            ("top_k", str(self.top_k)),
            ("min_p", str(self.min_p)),
            ("num_ctx", str(self.num_ctx)),
            ("num_predict", str(self.num_predict)),
            ("seed", str(self.seed)),
            ("think", self.think),
            ("keep_alive", self.keep_alive),
            ("mode", self.mode),
            (
                "system_prompt",
                self.system_prompt[:80]
                + ("..." if len(self.system_prompt) > 80 else ""),
            ),
        ]
