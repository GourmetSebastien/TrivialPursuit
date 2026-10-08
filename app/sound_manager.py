import math
import struct
import wave
from pathlib import Path
from typing import Dict, List

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

SOUNDS_DIR = Path(__file__).resolve().parent.parent / "assets" / "sounds"
SAMPLE_RATE = 44100


# ---------------------------------------------------------------------------
# Procedural WAV generation (no external audio assets required)
# ---------------------------------------------------------------------------

def _envelope(i: int, n: int, fade_samples: int) -> float:
    if fade_samples <= 0:
        return 1.0
    if i < fade_samples:
        return i / fade_samples
    if i > n - fade_samples:
        return max(0.0, (n - i) / fade_samples)
    return 1.0


def _tone(freq: float, duration: float, amp: float = 0.5, fade: float = 0.01) -> List[float]:
    n = int(SAMPLE_RATE * duration)
    fade_samples = int(SAMPLE_RATE * fade)
    return [
        amp * _envelope(i, n, fade_samples) * math.sin(2 * math.pi * freq * (i / SAMPLE_RATE))
        for i in range(n)
    ]


def _sweep(freq_start: float, freq_end: float, duration: float, amp: float = 0.5, fade: float = 0.01) -> List[float]:
    n = int(SAMPLE_RATE * duration)
    fade_samples = int(SAMPLE_RATE * fade)
    samples = []
    phase = 0.0
    for i in range(n):
        t = i / n if n else 0
        freq = freq_start + (freq_end - freq_start) * t
        phase += 2 * math.pi * freq / SAMPLE_RATE
        samples.append(amp * _envelope(i, n, fade_samples) * math.sin(phase))
    return samples


def _silence(duration: float) -> List[float]:
    return [0.0] * int(SAMPLE_RATE * duration)


def _mix(*parts: List[float]) -> List[float]:
    length = max(len(p) for p in parts)
    out = [0.0] * length
    for p in parts:
        for i, v in enumerate(p):
            out[i] += v
    peak = max((abs(v) for v in out), default=1.0) or 1.0
    if peak > 1.0:
        out = [v / peak for v in out]
    return out


def _concat(*parts: List[float]) -> List[float]:
    out: List[float] = []
    for p in parts:
        out.extend(p)
    return out


def _write_wav(path: Path, samples: List[float]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        frames = b"".join(
            struct.pack("<h", max(-32767, min(32767, int(s * 32767)))) for s in samples
        )
        f.writeframes(frames)


def _generate_click() -> List[float]:
    return _tone(1400, 0.04, amp=0.4, fade=0.005)


def _generate_land() -> List[float]:
    return _mix(_tone(180, 0.18, amp=0.5, fade=0.01), _tone(90, 0.18, amp=0.35, fade=0.02))


def _generate_spin() -> List[float]:
    parts = []
    gap = 0.03
    for i in range(28):
        parts.append(_tone(1500, 0.02, amp=0.35, fade=0.003))
        parts.append(_silence(gap))
        gap += 0.006
    return _concat(*parts)


def _generate_correct() -> List[float]:
    notes = [523.25, 659.25, 783.99]
    parts = []
    for freq in notes:
        parts.append(_tone(freq, 0.14, amp=0.5, fade=0.01))
        parts.append(_silence(0.02))
    return _concat(*parts)


def _generate_wrong_shot() -> List[float]:
    glug = _concat(
        _sweep(700, 250, 0.18, amp=0.5),
        _silence(0.03),
        _sweep(650, 220, 0.16, amp=0.45),
        _silence(0.03),
        _sweep(600, 200, 0.14, amp=0.4),
    )
    gasp = _tone(320, 0.22, amp=0.35, fade=0.02)
    return _concat(glug, _silence(0.05), gasp)


def _generate_victory() -> List[float]:
    notes = [523.25, 659.25, 783.99, 1046.5]
    parts = []
    for i, freq in enumerate(notes):
        dur = 0.16 if i < len(notes) - 1 else 0.5
        parts.append(_tone(freq, dur, amp=0.5, fade=0.01))
        parts.append(_silence(0.02))
    return _concat(*parts)


def _generate_wedge() -> List[float]:
    return _mix(_tone(880, 0.15, amp=0.4, fade=0.01), _tone(1320, 0.15, amp=0.25, fade=0.01))


GENERATORS = {
    "click": _generate_click,
    "land": _generate_land,
    "spin": _generate_spin,
    "correct": _generate_correct,
    "shot": _generate_wrong_shot,
    "victory": _generate_victory,
    "wedge": _generate_wedge,
}


def ensure_sounds_exist():
    SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
    for name, generator in GENERATORS.items():
        path = SOUNDS_DIR / f"{name}.wav"
        if not path.exists():
            _write_wav(path, generator())


class SoundManager:
    def __init__(self, db):
        self.db = db
        ensure_sounds_exist()
        self._effects: Dict[str, QSoundEffect] = {}
        for name in GENERATORS:
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(SOUNDS_DIR / f"{name}.wav")))
            effect.setVolume(0.8)
            self._effects[name] = effect
        self._muted = False

    def set_volume(self, percent: int):
        vol = max(0, min(100, percent)) / 100.0
        for effect in self._effects.values():
            effect.setVolume(vol)

    def set_muted(self, muted: bool):
        self._muted = muted

    def play(self, name: str):
        if self._muted:
            return
        effect = self._effects.get(name)
        if effect is not None:
            effect.play()
