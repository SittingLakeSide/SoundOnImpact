import time
from pathlib import Path

import numpy as np
import sounddevice as sd

from .config import load_config
from .detector import DrumBrain
from .logging_setup import create_logger
from .mixer import Mixer
from .synth import Synth


def run() -> None:
    project_root = Path(__file__).resolve().parent.parent
    config = load_config(project_root)
    log, log_file = create_logger()

    log.info("=" * 62)
    log.info("ImpactDrum - Mic Transient Edition")
    log.info(f"Log file: {log_file}")
    log.info("=" * 62)

    try:
        devices = sd.query_devices()
        default_in, default_out = sd.default.device
        log.info("Input devices:")
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                marker = " <- DEFAULT" if i == default_in else ""
                log.info(f"  [{i}] {d['name']}{marker}")
        log.info("Output devices:")
        for i, d in enumerate(devices):
            if d["max_output_channels"] > 0:
                marker = " <- DEFAULT" if i == default_out else ""
                log.info(f"  [{i}] {d['name']}{marker}")
    except Exception as exc:
        log.warning(f"Could not list devices: {exc}")

    mixer = Mixer(config.sample_rate_out, config.block_size, config.output_device)
    synth = Synth(config.sample_rate_out, config.master_volume)
    brain = DrumBrain(config, mixer, synth, log)

    if config.startup_test_sound:
        mixer.play(synth.make_kick(0.8))
        log.info("Startup audio test played.")

    def input_callback(indata: np.ndarray, frames: int, time_info, status) -> None:  # noqa: ARG001
        if status:
            log.debug(f"Stream status: {status}")
        mono = indata[:, 0] if indata.ndim == 1 else indata.mean(axis=1)
        brain.process(mono.astype(np.float64))

    log.info("Ready. Knock on desk / clap near mic.")
    try:
        with sd.InputStream(
            device=config.input_device,
            samplerate=config.sample_rate,
            blocksize=config.block_size,
            channels=config.input_channels,
            dtype="float32",
            callback=input_callback,
            latency="low",
        ):
            while True:
                time.sleep(0.5)
    except KeyboardInterrupt:
        log.info("Stopped by user.")
    except sd.PortAudioError as exc:
        log.error(f"Audio device error: {exc}")
        log.error("Set IMPACT_INPUT_DEVICE / IMPACT_OUTPUT_DEVICE in .env.")
    finally:
        mixer.close()
        log.info("ImpactDrum shut down cleanly.")

