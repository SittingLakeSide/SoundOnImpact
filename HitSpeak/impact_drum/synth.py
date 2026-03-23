import math
import wave
from pathlib import Path
from typing import Optional

import numpy as np


class Synth:
    def __init__(self, sample_rate: int, master_volume: float):
        self.sr = sample_rate
        self.master_volume = master_volume
        self.rng = np.random.default_rng(seed=42)

    def _t(self, duration: float) -> np.ndarray:
        return np.linspace(0, duration, int(self.sr * duration), endpoint=False)

    @staticmethod
    def _env(t: np.ndarray, attack: float, decay: float) -> np.ndarray:
        att = np.clip(t / max(attack, 1e-6), 0, 1)
        dec = np.exp(-t * decay)
        return att * dec

    def _sweep(self, t: np.ndarray, f0: float, f1: float) -> np.ndarray:
        ratio = (f1 / f0) if f0 > 0 and f1 > 0 else 1.0
        freq = f0 * (ratio ** (t / (t[-1] + 1e-9)))
        phase = np.cumsum(2 * np.pi * freq / self.sr)
        return np.sin(phase)

    def _noise(self, length: int) -> np.ndarray:
        return self.rng.uniform(-1.0, 1.0, length)

    @staticmethod
    def _highpass(x: np.ndarray, passes: int = 3) -> np.ndarray:
        for _ in range(passes):
            x = np.diff(x, prepend=x[0])
        return x / (np.max(np.abs(x)) + 1e-9)

    @staticmethod
    def _normalize(x: np.ndarray) -> np.ndarray:
        return x / (np.max(np.abs(x)) + 1e-9)

    @staticmethod
    def _saturate(x: np.ndarray, amount: float = 2.0) -> np.ndarray:
        return np.tanh(x * amount) / (np.tanh(amount) + 1e-9)

    def make_kick(self, velocity: float = 1.0) -> np.ndarray:
        t = self._t(0.55)
        body = self._sweep(t, 175, 28) * self._env(t, 0.001, 10)
        click = np.sin(2 * np.pi * 1400 * t) * self._env(t, 0.0002, 200)
        wave = self._saturate(body * 0.90 + click * 0.10, amount=3.0)
        return (wave * self._env(t, 0.0005, 8) * velocity * self.master_volume).astype(np.float32)

    def make_snare(self, velocity: float = 1.0) -> np.ndarray:
        t = self._t(0.28)
        tone = (np.sin(2 * np.pi * 182 * t) * 0.55 + np.sin(2 * np.pi * 207 * t) * 0.45) * self._env(t, 0.001, 35)
        raw = self._noise(len(t))
        hp = np.diff(raw, prepend=raw[0])
        bp = np.convolve(hp, np.ones(5) / 5, mode="same")
        snap = np.sin(2 * np.pi * 950 * t) * self._env(t, 0.0001, 250)
        wave = tone * 0.42 + bp * self._env(t, 0.0005, 24) * 0.48 + snap * 0.10
        return (self._normalize(wave) * velocity * self.master_volume).astype(np.float32)

    def make_hihat_closed(self, velocity: float = 1.0) -> np.ndarray:
        t = self._t(0.075)
        freqs = [205, 296, 415, 511, 618, 784]
        wave = sum(np.sign(np.sin(2 * np.pi * f * 38 * t)) for f in freqs)
        wave = self._highpass(wave * 0.55 + self._noise(len(t)) * 0.45, passes=3)
        return (wave * self._env(t, 0.0001, 80) * velocity * 0.52 * self.master_volume).astype(np.float32)

    def make_tom(self, base_freq: float = 110.0, velocity: float = 1.0) -> np.ndarray:
        t = self._t(0.44)
        body = self._sweep(t, base_freq * 1.65, base_freq * 0.62) * self._env(t, 0.001, 10)
        click = np.sin(2 * np.pi * base_freq * 3.2 * t) * self._env(t, 0.0002, 165)
        wave = self._saturate(body * 0.88 + click * 0.12, amount=2.0)
        return (wave * self._env(t, 0.0005, 8.5) * velocity * self.master_volume).astype(np.float32)

    def make_clap(self, velocity: float = 1.0) -> np.ndarray:
        t = self._t(0.18)
        bursts = np.zeros(len(t))
        for offset in [0, 0.008, 0.016]:
            idx = int(offset * self.sr)
            n = self._noise(len(t) - idx)
            bursts[idx:idx + len(n)] += n * np.exp(-np.arange(len(n)) * 60 / self.sr)
        wave = self._highpass(bursts, passes=1)
        return (self._normalize(wave) * self._env(t, 0.0005, 20) * velocity * 0.70 * self.master_volume).astype(np.float32)

    def load_custom_wav(self, path: Path, velocity: float = 1.0) -> Optional[np.ndarray]:
        if not path.exists():
            return None
        try:
            with wave.open(str(path), "rb") as wf:
                n_channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                frame_rate = wf.getframerate()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)
        except Exception:
            return None

        if sample_width == 1:
            data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            data = (data - 128.0) / 128.0
        elif sample_width == 2:
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sample_width == 4:
            data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            return None

        if n_channels > 1:
            data = data.reshape(-1, n_channels).mean(axis=1)

        if frame_rate != self.sr:
            src_idx = np.linspace(0, len(data) - 1, num=max(1, int(len(data) * self.sr / frame_rate)))
            data = np.interp(src_idx, np.arange(len(data)), data)

        data = self._normalize(data) * velocity * self.master_volume
        return data.astype(np.float32)

