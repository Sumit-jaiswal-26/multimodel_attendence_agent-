"""
engagement_analyzer.py
Engagement score computation from multiple signals:
head pose, movement, audio, and interaction.
Returns normalized 0.0-1.0 scores with detailed breakdowns.
"""
import math
import random
import time
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ── Signal Weights ─────────────────────────────────────────────────────────
# These weights sum to 1.0 and control how much each signal contributes
# to the overall engagement score.
SIGNAL_WEIGHTS = {
    "head_pose": 0.30,
    "movement": 0.20,
    "audio": 0.20,
    "interaction": 0.15,
    "gaze": 0.15,
}


class HeadPoseAnalyzer:
    """Classify head pose states into engagement scores."""

    # Maps pose state → engagement contribution (0-1)
    POSE_SCORES = {
        "forward": 1.0,
        "slight_down": 0.85,    # could be note-taking
        "down": 0.50,            # looking down — possibly distracted
        "left": 0.60,
        "right": 0.60,
        "up": 0.70,
        "unknown": 0.50,
    }

    @classmethod
    def score(cls, pose: str) -> float:
        return cls.POSE_SCORES.get(pose.lower(), 0.50)

    @classmethod
    def classify_from_angles(cls, yaw: float, pitch: float, roll: float) -> str:
        """
        Classify head pose from Euler angles (degrees).
        yaw: left/right rotation
        pitch: up/down tilt
        roll: tilt sideways
        """
        if abs(yaw) < 15 and abs(pitch) < 15:
            return "forward"
        elif pitch > 20:
            return "up"
        elif pitch < -20:
            return "down" if pitch < -30 else "slight_down"
        elif yaw > 25:
            return "right"
        elif yaw < -25:
            return "left"
        return "forward"


class MovementAnalyzer:
    """Analyze body/head movement patterns for engagement signals."""

    # Too little OR too much movement reduces engagement score
    MOVEMENT_SCORES = {
        "still": 0.65,       # completely still may mean bored/asleep
        "slight": 1.0,        # natural micro-movements → engaged
        "moderate": 0.80,
        "active": 0.55,       # restless / distracted
        "fidgeting": 0.35,
    }

    def __init__(self, window: int = 30):
        self._history: deque = deque(maxlen=window)

    def update(self, motion_magnitude: float) -> str:
        """Record a motion magnitude and return the classified state."""
        self._history.append(motion_magnitude)
        return self.classify(motion_magnitude)

    @classmethod
    def classify(cls, magnitude: float) -> str:
        if magnitude < 0.02:
            return "still"
        elif magnitude < 0.1:
            return "slight"
        elif magnitude < 0.3:
            return "moderate"
        elif magnitude < 0.6:
            return "active"
        return "fidgeting"

    @classmethod
    def score(cls, state: str) -> float:
        return cls.MOVEMENT_SCORES.get(state.lower(), 0.65)

    def rolling_score(self) -> float:
        """Return an averaged movement score over the history window."""
        if not self._history:
            return 0.65
        avg_mag = sum(self._history) / len(self._history)
        state = self.classify(avg_mag)
        return self.score(state)


class InteractionAnalyzer:
    """Track active classroom interactions: questions, answers, gestures."""

    def __init__(self, decay_seconds: float = 300.0):
        self._events: List[Dict] = []
        self._decay = decay_seconds

    def record(self, event_type: str = "generic", value: float = 1.0):
        self._events.append({
            "time": time.time(),
            "type": event_type,
            "value": value,
        })

    def _active_events(self) -> List[Dict]:
        cutoff = time.time() - self._decay
        return [e for e in self._events if e["time"] > cutoff]

    def score(self) -> float:
        """Compute interaction engagement score (0-1) over the decay window."""
        active = self._active_events()
        if not active:
            return 0.40  # no interactions → lower score
        # Rate: events per minute in window
        rate = len(active) / (self._decay / 60)
        # Saturate at 3 events/min → full score
        return min(1.0, 0.40 + rate / 3 * 0.60)


class EngagementAnalyzer:
    """
    Main engagement analysis class. Combines multiple signal sources
    into a unified, normalized engagement score.
    """

    def __init__(self):
        self._movement = MovementAnalyzer()
        self._interaction = InteractionAnalyzer()
        self._score_history: deque = deque(maxlen=100)
        self._last_analysis: Optional[Dict] = None

    # ── Core Scoring ───────────────────────────────────────────────────────

    def compute_score(
        self,
        head_pose: str = "forward",
        movement: str = "slight",
        audio_level: float = 0.4,
        gaze_score: float = 0.75,
        interaction_events: int = 0,
    ) -> Dict:
        """
        Compute a composite engagement score from individual signals.
        Returns a full breakdown dict.
        """
        # Individual signal scores
        pose_score = HeadPoseAnalyzer.score(head_pose)
        movement_score = MovementAnalyzer.score(movement)
        audio_score = self._audio_to_engagement(audio_level)
        interaction_score = self._interaction.score()
        gaze_val = max(0.0, min(1.0, gaze_score))

        # Weighted sum
        composite = (
            SIGNAL_WEIGHTS["head_pose"] * pose_score
            + SIGNAL_WEIGHTS["movement"] * movement_score
            + SIGNAL_WEIGHTS["audio"] * audio_score
            + SIGNAL_WEIGHTS["interaction"] * interaction_score
            + SIGNAL_WEIGHTS["gaze"] * gaze_val
        )
        composite = round(max(0.0, min(1.0, composite)), 4)

        # Classify
        level = self._classify_score(composite)

        result = {
            "timestamp": datetime.now().isoformat(),
            "overall_score": composite,
            "level": level,
            "signals": {
                "head_pose": {"state": head_pose, "score": round(pose_score, 3)},
                "movement": {"state": movement, "score": round(movement_score, 3)},
                "audio": {"level": round(audio_level, 3), "score": round(audio_score, 3)},
                "interaction": {"score": round(interaction_score, 3)},
                "gaze": {"score": round(gaze_val, 3)},
            },
            "weights": SIGNAL_WEIGHTS,
        }

        self._score_history.append(composite)
        self._last_analysis = result
        return result

    @staticmethod
    def _audio_to_engagement(level: float) -> float:
        """
        Map a raw audio level (0-1) to an engagement-relevant score.
        Moderate activity → high score. Silence or extreme noise → lower.
        """
        if level < 0.05:
            return 0.30
        elif level < 0.20:
            return 0.50 + level * 1.5
        elif level <= 0.65:
            # Sweet spot
            return 0.80 + (level - 0.20) * 0.20 / 0.45
        else:
            return max(0.50, 1.0 - (level - 0.65) * 1.8)

    @staticmethod
    def _classify_score(score: float) -> str:
        if score >= 0.75:
            return "high"
        elif score >= 0.45:
            return "medium"
        return "low"

    # ── Rolling Stats ──────────────────────────────────────────────────────

    def rolling_average(self) -> float:
        """Average engagement score over the history window."""
        if not self._score_history:
            return 0.0
        return round(sum(self._score_history) / len(self._score_history), 4)

    def trend(self) -> str:
        """
        Compute trend direction from the history window.
        Returns 'rising', 'falling', or 'stable'.
        """
        if len(self._score_history) < 6:
            return "stable"
        half = len(self._score_history) // 2
        first_half = list(self._score_history)[:half]
        second_half = list(self._score_history)[half:]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        delta = avg_second - avg_first
        if delta > 0.05:
            return "rising"
        elif delta < -0.05:
            return "falling"
        return "stable"

    def get_stats(self) -> Dict:
        """Return statistical summary of engagement history."""
        scores = list(self._score_history)
        if not scores:
            return {"avg": 0, "min": 0, "max": 0, "trend": "stable", "count": 0}
        return {
            "avg": round(sum(scores) / len(scores), 4),
            "min": round(min(scores), 4),
            "max": round(max(scores), 4),
            "trend": self.trend(),
            "count": len(scores),
        }

    # ── Simulation / Demo ──────────────────────────────────────────────────

    @staticmethod
    def simulate_signals(scenario: str = "normal") -> Dict:
        """
        Generate simulated signal values for demo/testing.
        Scenarios: 'normal', 'distracted', 'engaged', 'mixed'
        """
        scenarios = {
            "normal": {
                "poses": ["forward", "slight_down", "forward"],
                "movements": ["slight", "still", "slight"],
                "audio_range": (0.25, 0.55),
                "gaze_range": (0.60, 0.90),
            },
            "distracted": {
                "poses": ["left", "right", "down"],
                "movements": ["active", "fidgeting", "still"],
                "audio_range": (0.05, 0.30),
                "gaze_range": (0.20, 0.50),
            },
            "engaged": {
                "poses": ["forward", "forward", "slight_down"],
                "movements": ["slight", "slight", "moderate"],
                "audio_range": (0.40, 0.70),
                "gaze_range": (0.75, 1.0),
            },
            "mixed": {
                "poses": ["forward", "down", "left", "forward"],
                "movements": ["slight", "fidgeting", "still", "moderate"],
                "audio_range": (0.20, 0.65),
                "gaze_range": (0.45, 0.85),
            },
        }
        cfg = scenarios.get(scenario, scenarios["normal"])
        return {
            "head_pose": random.choice(cfg["poses"]),
            "movement": random.choice(cfg["movements"]),
            "audio_level": random.uniform(*cfg["audio_range"]),
            "gaze_score": random.uniform(*cfg["gaze_range"]),
        }

    def analyze_simulated(self, scenario: str = "normal") -> Dict:
        """Run a full analysis on simulated signals and return the result."""
        signals = self.simulate_signals(scenario)
        return self.compute_score(**signals)

    # ── Interaction Recording ──────────────────────────────────────────────

    def record_interaction(self, event_type: str = "generic", value: float = 1.0):
        """Record an interaction event (question, answer, gesture)."""
        self._interaction.record(event_type, value)

    def reset(self):
        """Reset all history and state."""
        self._score_history.clear()
        self._movement = MovementAnalyzer()
        self._interaction = InteractionAnalyzer()
        self._last_analysis = None
