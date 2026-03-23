import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _parse_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def _to_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _to_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _to_optional_int(name: str) -> Optional[int]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


@dataclass(frozen=True)
class Config:
    sample_rate: int
    block_size: int
    input_device: Optional[int]
    output_device: Optional[int]
    input_channels: int
    ratio_threshold: float
    peak_threshold: float
    min_energy: float
    tier_medium: float
    tier_hard: float
    cooldown_ms: int
    sample_rate_out: int
    master_volume: float
    startup_test_sound: bool
    custom_sound_dir: Path
    custom_light: Optional[str]
    custom_medium: Optional[str]
    custom_hard: Optional[str]


def load_config(project_root: Path) -> Config:
    _parse_env_file(project_root / ".env")

    return Config(
        sample_rate=_to_int("IMPACT_SAMPLE_RATE", 44100),
        block_size=_to_int("IMPACT_BLOCK_SIZE", 128),
        input_device=_to_optional_int("IMPACT_INPUT_DEVICE"),
        output_device=_to_optional_int("IMPACT_OUTPUT_DEVICE"),
        input_channels=max(1, min(2, _to_int("IMPACT_INPUT_CHANNELS", 1))),
        ratio_threshold=_to_float("IMPACT_RATIO_THRESHOLD", 4.8),
        peak_threshold=_to_float("IMPACT_PEAK_THRESHOLD", 0.045),
        min_energy=_to_float("IMPACT_MIN_ENERGY", 0.00045),
        tier_medium=_to_float("IMPACT_TIER_MEDIUM", 9.0),
        tier_hard=_to_float("IMPACT_TIER_HARD", 16.0),
        cooldown_ms=_to_int("IMPACT_COOLDOWN_MS", 120),
        sample_rate_out=_to_int("IMPACT_SAMPLE_RATE_OUT", 44100),
        master_volume=max(0.0, min(1.0, _to_float("IMPACT_MASTER_VOLUME", 0.9))),
        startup_test_sound=os.getenv("IMPACT_STARTUP_TEST_SOUND", "1").strip() not in {"0", "false", "False"},
        custom_sound_dir=project_root / "sounds",
        custom_light=os.getenv("IMPACT_CUSTOM_LIGHT", "").strip() or None,
        custom_medium=os.getenv("IMPACT_CUSTOM_MEDIUM", "").strip() or None,
        custom_hard=os.getenv("IMPACT_CUSTOM_HARD", "").strip() or None,
    )

