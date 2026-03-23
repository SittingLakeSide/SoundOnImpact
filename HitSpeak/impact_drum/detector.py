import math
import time
from collections import deque
from typing import Callable

import numpy as np

from .config import Config
from .mixer import Mixer
from .synth import Synth


Factory = Callable[[float], np.ndarray]


class DrumBrain:
    def __init__(self, config: Config, mixer: Mixer, synth: Synth, log):
        self._cfg = config
        self._mixer = mixer
        self._synth = synth
        self._log = log
        self._short_buf = deque(maxlen=2)
        self._long_buf = deque(maxlen=28)
        self._last_trig = 0.0
        self._last_debug = 0.0
        self._hit_count = 0
        self._idx_light = 0
        self._idx_medium = 0
        self._idx_hard = 0

        self._sounds_light = self._build_light()
        self._sounds_medium = self._build_medium()
        self._sounds_hard = self._build_hard()

    def _custom(self, filename: str | None, fallback: Factory) -> Factory:
        if not filename:
            return fallback
        sample_path = self._cfg.custom_sound_dir / filename

        def _factory(v: float) -> np.ndarray:
            loaded = self._synth.load_custom_wav(sample_path, v)
            return loaded if loaded is not None else fallback(v)

        return _factory

    def _build_light(self):
        return [
            ("Hi-Hat", self._custom(self._cfg.custom_light, self._synth.make_hihat_closed)),
            ("Rim", self._synth.make_clap),
            ("Hi-Hat", self._custom(self._cfg.custom_light, self._synth.make_hihat_closed)),
        ]

    def _build_medium(self):
        return [
            ("Snare", self._custom(self._cfg.custom_medium, self._synth.make_snare)),
            ("Tom Hi", lambda v: self._synth.make_tom(118, v)),
            ("Snare", self._custom(self._cfg.custom_medium, self._synth.make_snare)),
        ]

    def _build_hard(self):
        hard_fallback = lambda v: self._synth.make_kick(v)  # noqa: E731
        return [
            ("Kick", self._custom(self._cfg.custom_hard, hard_fallback)),
            ("Tom Lo", lambda v: self._synth.make_tom(68, v)),
            ("Kick", self._custom(self._cfg.custom_hard, hard_fallback)),
        ]

    def process(self, frame: np.ndarray) -> None:
        rms = float(np.sqrt(np.mean(frame ** 2)))
        self._short_buf.append(rms)
        self._long_buf.append(rms)

        if len(self._short_buf) < self._short_buf.maxlen or len(self._long_buf) < self._long_buf.maxlen:
            return

        short_rms = math.sqrt(sum(x * x for x in self._short_buf) / len(self._short_buf))
        long_rms = math.sqrt(sum(x * x for x in self._long_buf) / len(self._long_buf))
        peak = float(np.max(np.abs(frame)))

        if long_rms < 1e-9 or short_rms < self._cfg.min_energy * 0.5:
            return

        ratio = short_rms / long_rms
        ratio_hit = ratio >= self._cfg.ratio_threshold and short_rms >= self._cfg.min_energy
        peak_hit = peak >= self._cfg.peak_threshold and short_rms >= self._cfg.min_energy * 0.5
        if not (ratio_hit or peak_hit):
            now = time.monotonic()
            if now - self._last_debug > 1.0:
                self._last_debug = now
                self._log.info(
                    f"LISTEN ratio={ratio:>5.2f} short={short_rms:.6f} long={long_rms:.6f} peak={peak:.4f}"
                )
            return

        now = time.monotonic()
        if (now - self._last_trig) * 1000 < self._cfg.cooldown_ms:
            return
        self._last_trig = now

        if peak_hit and not ratio_hit:
            velocity = float(np.clip((peak / max(self._cfg.peak_threshold, 1e-6)) * 0.35, 0.25, 1.0))
        else:
            velocity = self._ratio_to_velocity(ratio)
        self._trigger(ratio, velocity)

    def _ratio_to_velocity(self, ratio: float) -> float:
        v = math.log(ratio / max(self._cfg.ratio_threshold, 1e-6) + 1) / math.log(8)
        return float(np.clip(v, 0.18, 1.0))

    def _trigger(self, ratio: float, velocity: float) -> None:
        self._hit_count += 1
        if ratio >= self._cfg.tier_hard:
            table = self._sounds_hard
            idx = self._idx_hard % len(table)
            self._idx_hard += 1
        elif ratio >= self._cfg.tier_medium:
            table = self._sounds_medium
            idx = self._idx_medium % len(table)
            self._idx_medium += 1
        else:
            table = self._sounds_light
            idx = self._idx_light % len(table)
            self._idx_light += 1

        name, factory = table[idx]
        self._mixer.play(factory(velocity))
        self._log.info(
            f"HIT #{self._hit_count:>4d}  |  {name:<10s}  |  ratio={ratio:>6.1f}  |  vel={velocity:.2f}"
        )

