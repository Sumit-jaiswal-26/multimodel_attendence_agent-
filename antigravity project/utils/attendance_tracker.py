"""
attendance_tracker.py
Manages attendance records: mark present, calculate percentages,
detect sustained presence, and export to CSV/JSON.
"""
import csv
import json
import io
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class StudentRecord:
    """Represents a single student's attendance data."""

    def __init__(self, student_id: str, name: str):
        self.student_id = student_id
        self.name = name
        self.first_seen: Optional[str] = None
        self.last_seen: Optional[str] = None
        self.presence_count: int = 0
        self.total_frames: int = 0
        self.status: str = "absent"
        self.engagement_scores: List[float] = []
        self._presence_timestamps: List[str] = []

    @property
    def avg_engagement(self) -> float:
        if not self.engagement_scores:
            return 0.0
        return round(sum(self.engagement_scores) / len(self.engagement_scores), 4)

    @property
    def attendance_rate(self) -> float:
        """Fraction of tracked frames in which this student was present."""
        if self.total_frames == 0:
            return 0.0
        return round(self.presence_count / self.total_frames, 4)

    def mark_present(self, confidence: float = 1.0) -> str:
        """Update presence. Returns 'new' for first mark, 'updated' thereafter."""
        now = datetime.now().isoformat()
        self._presence_timestamps.append(now)
        if self.first_seen is None:
            self.first_seen = now
            self.status = "present"
            action = "marked_present"
        else:
            action = "updated"
        self.last_seen = now
        self.presence_count += 1
        self.total_frames += 1
        return action

    def add_engagement(self, score: float):
        """Append an engagement score sample."""
        self.engagement_scores.append(max(0.0, min(1.0, score)))

    def is_sustained_present(self, min_minutes: float = 5.0) -> bool:
        """True if the student has been seen for at least min_minutes."""
        if not self.first_seen or not self.last_seen:
            return False
        try:
            start = datetime.fromisoformat(self.first_seen)
            end = datetime.fromisoformat(self.last_seen)
            return (end - start).total_seconds() >= min_minutes * 60
        except Exception:
            return False

    def to_dict(self) -> Dict:
        return {
            "id": self.student_id,
            "name": self.name,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "presence_count": self.presence_count,
            "total_frames": self.total_frames,
            "status": self.status,
            "avg_engagement": self.avg_engagement,
            "attendance_rate": self.attendance_rate,
            "engagement_scores": self.engagement_scores[-20:],  # last 20
        }

    def to_csv_row(self) -> List[str]:
        return [
            self.student_id,
            self.name,
            self.first_seen or "",
            self.last_seen or "",
            self.status,
            str(round(self.avg_engagement, 4)),
            str(round(self.attendance_rate * 100, 1)) + "%",
        ]


class AttendanceTracker:
    """
    Session-level attendance management.
    Tracks all students, computes statistics, detects sustained presence,
    and supports export to CSV and JSON.
    """

    CSV_HEADERS = [
        "Student ID", "Name", "First Seen", "Last Seen",
        "Status", "Avg Engagement", "Attendance Rate",
    ]

    def __init__(self, session_id: str = "", course: str = "", instructor: str = ""):
        self.session_id = session_id
        self.course = course
        self.instructor = instructor
        self.created_at = datetime.now().isoformat()
        self._students: Dict[str, StudentRecord] = {}
        self._frame_count: int = 0
        self._log: List[Dict] = []  # audit log of all mark events

    # ── Marking ────────────────────────────────────────────────────────────

    def mark_present(
        self,
        student_id: str,
        student_name: str = "",
        confidence: float = 1.0,
        engagement_score: Optional[float] = None,
    ) -> Dict:
        """
        Mark a student as present. Creates the record if it doesn't exist.
        Returns a result dict with action and current student data.
        """
        if student_id not in self._students:
            name = student_name or f"Student_{student_id}"
            self._students[student_id] = StudentRecord(student_id, name)

        record = self._students[student_id]
        action = record.mark_present(confidence)

        if engagement_score is not None:
            record.add_engagement(engagement_score)

        # Audit log entry
        self._log.append({
            "event": action,
            "student_id": student_id,
            "name": record.name,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
        })

        return {
            "success": True,
            "action": action,
            "student": record.to_dict(),
            "total_present": self.total_present,
        }

    def mark_absent(self, student_id: str) -> bool:
        """Manually mark a student as absent."""
        if student_id in self._students:
            self._students[student_id].status = "absent"
            return True
        return False

    def increment_frame(self):
        """Increment the total frame counter (called each video frame)."""
        self._frame_count += 1
        for rec in self._students.values():
            rec.total_frames += 1

    # ── Queries ────────────────────────────────────────────────────────────

    @property
    def total_present(self) -> int:
        return sum(1 for r in self._students.values() if r.status == "present")

    @property
    def total_registered(self) -> int:
        return len(self._students)

    def attendance_percentage(self, expected_count: int = 0) -> float:
        """
        Attendance percentage. If expected_count > 0, uses it as the denominator.
        Otherwise uses the number of registered students.
        """
        denominator = expected_count or self.total_registered
        if denominator == 0:
            return 0.0
        return round(self.total_present / denominator * 100, 2)

    def get_student(self, student_id: str) -> Optional[Dict]:
        rec = self._students.get(student_id)
        return rec.to_dict() if rec else None

    def get_all_students(self) -> List[Dict]:
        return [r.to_dict() for r in self._students.values()]

    def get_present_students(self) -> List[Dict]:
        return [r.to_dict() for r in self._students.values() if r.status == "present"]

    def get_absent_students(self) -> List[Dict]:
        return [r.to_dict() for r in self._students.values() if r.status != "present"]

    def get_sustained_present(self, min_minutes: float = 5.0) -> List[Dict]:
        """Return students with confirmed sustained presence."""
        return [
            r.to_dict()
            for r in self._students.values()
            if r.is_sustained_present(min_minutes)
        ]

    def get_top_engaged(self, n: int = 5) -> List[Dict]:
        """Return top n students by average engagement score."""
        ranked = sorted(
            self._students.values(),
            key=lambda r: r.avg_engagement,
            reverse=True,
        )
        return [r.to_dict() for r in ranked[:n]]

    def get_needs_attention(self, threshold: float = 0.40, n: int = 5) -> List[Dict]:
        """Return students with engagement below threshold."""
        low = [
            r for r in self._students.values()
            if r.status == "present" and r.avg_engagement < threshold
        ]
        low.sort(key=lambda r: r.avg_engagement)
        return [r.to_dict() for r in low[:n]]

    # ── Statistics ─────────────────────────────────────────────────────────

    def get_summary(self) -> Dict:
        """Return a comprehensive attendance and engagement summary."""
        all_rec = list(self._students.values())
        engagement_vals = [r.avg_engagement for r in all_rec if r.engagement_scores]
        avg_eng = (
            sum(engagement_vals) / len(engagement_vals) if engagement_vals else 0.0
        )
        return {
            "session_id": self.session_id,
            "course": self.course,
            "instructor": self.instructor,
            "created_at": self.created_at,
            "total_present": self.total_present,
            "total_registered": self.total_registered,
            "attendance_percentage": self.attendance_percentage(),
            "avg_engagement": round(avg_eng, 4),
            "frame_count": self._frame_count,
            "log_entries": len(self._log),
        }

    # ── Export ─────────────────────────────────────────────────────────────

    def export_csv(self) -> str:
        """Return attendance data as a CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self.CSV_HEADERS)
        for rec in self._students.values():
            writer.writerow(rec.to_csv_row())
        return output.getvalue()

    def export_json(self) -> str:
        """Return attendance data as a formatted JSON string."""
        data = {
            "summary": self.get_summary(),
            "students": self.get_all_students(),
            "audit_log": self._log[-100:],  # last 100 events
            "exported_at": datetime.now().isoformat(),
        }
        return json.dumps(data, indent=2)

    def save_csv(self, filepath: str):
        """Write attendance data to a CSV file."""
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            f.write(self.export_csv())

    def save_json(self, filepath: str):
        """Write attendance data to a JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.export_json())

    # ── Audit Log ──────────────────────────────────────────────────────────

    def get_log(self, last_n: int = 50) -> List[Dict]:
        """Return the last n audit log entries."""
        return self._log[-last_n:]

    def reset(self):
        """Clear all attendance data."""
        self._students.clear()
        self._frame_count = 0
        self._log.clear()
