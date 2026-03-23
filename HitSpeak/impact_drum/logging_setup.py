import logging
import os
import sys
from pathlib import Path


def create_logger() -> tuple[logging.Logger, Path]:
    log_dir = Path(os.getenv("APPDATA", ".")) / "ImpactDrum"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "impact_drum.log"

    handlers: list[logging.Handler] = [logging.FileHandler(log_file, encoding="utf-8")]
    try:
        if sys.stdout and sys.stdout.fileno() >= 0:
            handlers.append(logging.StreamHandler(sys.stdout))
    except Exception:
        pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )
    return logging.getLogger("ImpactDrum"), log_file

