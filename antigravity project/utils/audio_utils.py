"""
audio_utils.py
Audio event classification, level detection, and silence detection utilities.
Works with simulated signals (no microphone dependency) and optionally with
real Web Audio API data forwarded from the browser.
"""
import math
import os
import time
import random
import struct
import wave
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class AudioEvent:
    """Represents a single classified audio event."""

    TYPES = {
        "silence": (0.0, 0.1),
        "low_activity": (0.1, 0.3),
        "moderate_activity": (0.3, 0.7),
        "high_activity": (0.7, 1.0),
    }

    def __init__(self, level: float, duration: float = 0.0, timestamp: str = ""):
        self.level = max(0.0, min(1.0, level))
        self.duration = duration
        self.timestamp = timestamp or datetime.now().isoformat()
        self.event_type = self._classify(self.level)

    @staticmethod
    def _classify(level: float) -> str:
        if level > 0.7:
            return "high_activity"
        elif level > 0.3:
            return "moderate_activity"
        elif level > 0.1:
            return "low_activity"
        return "silence"

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "level": round(self.level, 4),
            "duration": round(self.duration, 2),
            "type": self.event_type,
        }


class AudioUtils:
    """
    Utility class for audio event management, classification,
    and statistical analysis of classroom audio activity.
    """

    # Rolling window size for recent-event analysis
    WINDOW_SIZE = 200

    def __init__(self):
        self._events: deque = deque(maxlen=self.WINDOW_SIZE)
        self._silence_start: Optional[float] = None
        self._silence_threshold = 0.1
        self._silence_min_duration = 3.0  # seconds before flagged as silence

    # ── Event Ingestion ────────────────────────────────────────────────────

    def record_event(self, level: float, duration: float = 1.0) -> AudioEvent:
        """Record a new audio event and return the classified AudioEvent."""
        event = AudioEvent(level=level, duration=duration)
        self._events.append(event)
        self._update_silence_tracker(level, duration)
        return event

    def record_event_dict(self, level: float, duration: float = 1.0) -> Dict:
        """Convenience wrapper returning a dict instead of AudioEvent."""
        return self.record_event(level, duration).to_dict()

    def _update_silence_tracker(self, level: float, duration: float):
        """Track continuous silence for alerting purposes."""
        now = time.time()
        if level <= self._silence_threshold:
            if self._silence_start is None:
                self._silence_start = now
        else:
            self._silence_start = None  # reset on audio detection

    # ── Silence Detection ──────────────────────────────────────────────────

    @property
    def silence_duration(self) -> float:
        """Return the number of seconds of continuous silence, or 0."""
        if self._silence_start is None:
            return 0.0
        return time.time() - self._silence_start

    @property
    def is_silent(self) -> bool:
        """True if the room has been silent longer than the minimum duration."""
        return self.silence_duration >= self._silence_min_duration

    # ── Statistics ─────────────────────────────────────────────────────────

    def get_average_level(self) -> float:
        """Mean audio level over the rolling window."""
        if not self._events:
            return 0.0
        return sum(e.level for e in self._events) / len(self._events)

    def get_peak_level(self) -> float:
        """Maximum level in the rolling window."""
        if not self._events:
            return 0.0
        return max(e.level for e in self._events)

    def get_type_distribution(self) -> Dict[str, int]:
        """Count of each event type in the rolling window."""
        dist: Dict[str, int] = {t: 0 for t in AudioEvent.TYPES}
        for e in self._events:
            dist[e.event_type] = dist.get(e.event_type, 0) + 1
        return dist

    def get_dominant_type(self) -> str:
        """Most common event type in the rolling window."""
        dist = self.get_type_distribution()
        return max(dist, key=lambda k: dist[k]) if dist else "silence"

    def get_summary(self) -> Dict:
        """Return a comprehensive summary of audio activity."""
        dist = self.get_type_distribution()
        total = len(self._events)
        return {
            "total_events": total,
            "avg_level": round(self.get_average_level(), 4),
            "peak_level": round(self.get_peak_level(), 4),
            "dominant_type": self.get_dominant_type(),
            "is_silent": self.is_silent,
            "silence_duration_s": round(self.silence_duration, 1),
            "type_breakdown": dist,
            "type_percentages": {
                k: round(v / total * 100, 1) if total else 0
                for k, v in dist.items()
            },
        }

    def get_recent_events(self, n: int = 50) -> List[Dict]:
        """Return the last n events as dicts."""
        events = list(self._events)
        return [e.to_dict() for e in events[-n:]]

    # ── Simulation ─────────────────────────────────────────────────────────

    @staticmethod
    def simulate_level(scenario: str = "normal") -> float:
        """
        Simulate a realistic audio level for demo/testing purposes.
        Scenarios: 'normal', 'lecture', 'discussion', 'quiet', 'noisy'
        """
        scenarios = {
            "normal": (0.2, 0.6),
            "lecture": (0.3, 0.65),
            "discussion": (0.5, 0.9),
            "quiet": (0.0, 0.15),
            "noisy": (0.65, 1.0),
        }
        low, high = scenarios.get(scenario, (0.1, 0.8))
        # Add some realistic variation with a sine wave + noise
        t = time.time()
        wave = (math.sin(t * 0.5) + 1) / 2  # 0-1 slow oscillation
        noise = random.uniform(-0.1, 0.1)
        level = low + (high - low) * wave + noise
        return max(0.0, min(1.0, level))

    @staticmethod
    def classify_level(level: float) -> str:
        """Classify a raw level value into an event type string."""
        return AudioEvent._classify(level)

    # ── Engagement Signal ──────────────────────────────────────────────────

    def audio_engagement_signal(self) -> float:
        """
        Derive an engagement-relevant signal from audio data.
        Moderate activity correlates with healthy classroom participation.
        Returns 0.0-1.0.
        """
        avg = self.get_average_level()
        # Ideal classroom: 0.2-0.6 activity
        # Too silent or too noisy → lower engagement signal
        if avg < 0.05:
            return 0.3  # completely silent — may indicate disengagement
        elif avg < 0.2:
            return 0.5 + avg * 2  # low but acceptable
        elif avg <= 0.65:
            return 0.75 + (avg - 0.2) * 0.5  # healthy range
        else:
            return max(0.5, 1.0 - (avg - 0.65) * 2)  # too noisy

    def reset(self):
        """Clear all recorded events and reset silence tracking."""
        self._events.clear()
        self._silence_start = None

    # ── Text-to-Speech Engine ──────────────────────────────────────────────

    @staticmethod
    def generate_tts_file(text: str, output_dir: str = "static/audio") -> Dict[str, Any]:
        """
        Generate audio file from text using available TTS engine (gTTS if installed,
        or built-in audio wave chime/tone generator for offline deployment).
        Returns dict with file path and status.
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = int(time.time())
        safe_name = f"announcement_{timestamp}"

        # Try gTTS if installed
        try:
            from gtts import gTTS
            filename = f"{safe_name}.mp3"
            filepath = os.path.join(output_dir, filename)
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(filepath)
            return {
                "success": True,
                "engine": "gTTS",
                "filename": filename,
                "url": f"/static/audio/{filename}",
                "text": text
            }
        except Exception:
            pass

        # Built-in pure-python WAV tone generator for offline privacy-preserving operation
        try:
            import wave
            import struct
            filename = f"{safe_name}.wav"
            filepath = os.path.join(output_dir, filename)
            sample_rate = 44100
            duration = 1.5  # 1.5 seconds alert chime
            frequency = 440.0  # A4 note
            num_samples = int(sample_rate * duration)

            with wave.open(filepath, 'w') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)   # 16-bit
                wav_file.setframerate(sample_rate)
                for i in range(num_samples):
                    t = float(i) / sample_rate
                    # Two-tone chime (440Hz -> 880Hz)
                    current_freq = frequency if t < 0.75 else frequency * 2
                    decay = math.exp(-2.0 * (t % 0.75))
                    sample = decay * math.sin(2.0 * math.pi * current_freq * t)
                    int_sample = int(sample * 32767.0 * 0.5)
                    wav_file.writeframes(struct.pack('<h', int_sample))

            return {
                "success": True,
                "engine": "offline_audio_chime",
                "filename": filename,
                "url": f"/static/audio/{filename}",
                "text": text,
                "note": "Offline chime generated; browser Web Speech API used for live voice"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "text": text}
