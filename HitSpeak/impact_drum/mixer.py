import threading

import numpy as np
import sounddevice as sd


class Mixer:
    def __init__(self, sample_rate: int, block_size: int, output_device: int | None = None):
        self._voices: list[list] = []
        self._lock = threading.Lock()
        self._stream = sd.OutputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocksize=block_size,
            device=output_device,
            callback=self._callback,
        )
        self._stream.start()

    def play(self, samples: np.ndarray) -> None:
        with self._lock:
            self._voices.append([samples, 0])

    def _callback(self, outdata: np.ndarray, frames: int, *_) -> None:
        mix = np.zeros(frames, dtype=np.float32)
        with self._lock:
            still_alive = []
            for voice in self._voices:
                buf, pos = voice
                end = min(pos + frames, len(buf))
                take = end - pos
                if take > 0:
                    mix[:take] += buf[pos:end]
                if end < len(buf):
                    voice[1] = end
                    still_alive.append(voice)
            self._voices = still_alive
        np.clip(mix, -1.0, 1.0, out=mix)
        outdata[:, 0] = mix

    def close(self) -> None:
        self._stream.stop()
        self._stream.close()

