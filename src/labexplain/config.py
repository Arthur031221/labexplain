"""Settings stored as a flat TOML file.

The file lives in the labexplain home directory, which is
``~/Library/Application Support/labexplain`` on macOS, ``$XDG_CONFIG_HOME/labexplain``
elsewhere, or whatever ``LABEXPLAIN_HOME`` points to.
"""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path

OCR_BACKENDS = ("auto", "mlx", "ollama")


def home() -> Path:
    env = os.environ.get("LABEXPLAIN_HOME")
    if env:
        return Path(env).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "labexplain"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "labexplain"


def config_path() -> Path:
    return home() / "config.toml"


@dataclass
class Config:
    ocr_backend: str = "auto"
    mlx_model: str = "mlx-community/GLM-OCR-8bit"
    ollama_ocr_model: str = "glm-ocr:q8_0"
    ollama_explain_model: str = "qwen3:4b"
    ollama_url: str = "http://localhost:11434"
    max_ocr_tokens: int = 2048
    max_explain_tokens: int = 300
    port: int = 8000
    explain: bool = True

    @classmethod
    def field_names(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    def to_dict(self) -> dict:
        return asdict(self)


class ConfigError(ValueError):
    pass


def coerce(key: str, raw: object) -> object:
    if key not in Config.field_names():
        valid = ", ".join(Config.field_names())
        raise ConfigError(f"unknown key '{key}'. Valid keys: {valid}")
    default = getattr(Config(), key)
    if isinstance(default, bool):
        if isinstance(raw, bool):
            return raw
        if str(raw).lower() in ("1", "true", "yes", "on"):
            return True
        if str(raw).lower() in ("0", "false", "no", "off"):
            return False
        raise ConfigError(f"{key} must be true or false, got '{raw}'")
    if isinstance(default, int):
        try:
            value = int(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"{key} must be an integer, got '{raw}'") from exc
        if value < 0:
            raise ConfigError(f"{key} must not be negative")
        return value
    value = str(raw).strip()
    if key == "ocr_backend" and value not in OCR_BACKENDS:
        raise ConfigError(f"ocr_backend must be one of {', '.join(OCR_BACKENDS)}, got '{value}'")
    return value


def load(path: Path | None = None) -> Config:
    path = path or config_path()
    cfg = Config()
    if not path.exists():
        return cfg
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"cannot parse {path}: {exc}") from exc
    for key, raw in data.items():
        if key not in Config.field_names():
            continue
        setattr(cfg, key, coerce(key, raw))
    return cfg


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def save(cfg: Config, path: Path | None = None) -> Path:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# labexplain settings. Edit here or with `labexplain config set KEY VALUE`."]
    lines += [f"{k} = {_toml_value(v)}" for k, v in cfg.to_dict().items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
