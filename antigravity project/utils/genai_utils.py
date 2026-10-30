"""
genai_utils.py
Wrapper around Google Gemini API for text generation, image analysis,
teaching suggestions, and report generation.
"""
import json
import base64
import io
from typing import Optional, List, Dict, Any


class GeminiUtils:
    """Helper class for Google Gemini API interactions."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.client = None
        self.model_name = "gemini-2.0-flash-exp"
        self._init_client()

    def _init_client(self):
        """Initialize the Gemini client if API key is available."""
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model_name)
            except Exception as e:
                print(f"[GeminiUtils] Failed to initialize client: {e}")
                self.client = None

    def set_api_key(self, api_key: str):
        """Update the API key and reinitialize the client."""
        self.api_key = api_key
        self._init_client()

    def is_available(self) -> bool:
        """Check if the Gemini client is ready."""
        return self.client is not None

    # ── Text Generation ────────────────────────────────────────────────────

    def generate_text(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        """Generate text from a prompt."""
        if not self.is_available():
            return None
        try:
            response = self.client.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"[GeminiUtils] generate_text error: {e}")
            return None

    def generate_json(self, prompt: str) -> Optional[Any]:
        """Generate and parse a JSON response from a prompt."""
        full_prompt = prompt + "\n\nRespond ONLY with valid JSON, no markdown fences."
        text = self.generate_text(full_prompt)
        if not text:
            return None
        try:
            # Strip markdown fences if present
            text = text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"[GeminiUtils] JSON parse error: {e}")
            return None

    # ── Image Analysis ─────────────────────────────────────────────────────

    def analyze_image(self, image_b64: str, prompt: str) -> Optional[str]:
        """Analyze a base64-encoded image with a given prompt."""
        if not self.is_available():
            return None
        try:
            from PIL import Image
            image_data = base64.b64decode(image_b64.split(",")[-1])
            img = Image.open(io.BytesIO(image_data))
            response = self.client.generate_content([prompt, img])
            return response.text
        except Exception as e:
            print(f"[GeminiUtils] analyze_image error: {e}")
            return None

    def analyze_classroom_frame(self, image_b64: str) -> Dict[str, Any]:
        """
        Analyze a classroom image frame for engagement signals.
        Returns a dict with faces_count, engagement_score, attention_states,
        observations, and concerns.
        """
        prompt = """Analyze this classroom image and provide:
1. Number of students visible and their attention level (attentive/distracted/absent)
2. Overall engagement score from 0.0 to 1.0
3. Behavioral observations (head pose, movement, interaction)
4. Any concerns or positive signals

Respond ONLY in JSON with keys:
  faces_count (int),
  engagement_score (float 0-1),
  attention_states (list of strings),
  observations (string),
  concerns (list of strings)"""

        result_text = self.analyze_image(image_b64, prompt)
        if not result_text:
            return {}
        try:
            text = result_text.strip()
            if "```" in text:
                parts = text.split("```")
                text = parts[1] if len(parts) > 1 else text
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception:
            return {"observations": result_text}

    # ── Teaching Suggestions ───────────────────────────────────────────────

    def generate_teaching_suggestions(
        self,
        context: str = "",
        avg_engagement: float = 0.5,
        engagement_trend: str = "stable",
        student_count: int = 0,
        concerns: List[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Generate AI teaching suggestions based on session context.
        Returns a list of suggestion dicts with priority, category,
        suggestion, rationale, and implementation keys.
        """
        concerns = concerns or []
        prompt = f"""You are an expert educational assistant for a live classroom session.

Session Context:
- Course/Topic: {context or 'General classroom session'}
- Students Present: {student_count}
- Average Engagement Score: {avg_engagement:.2f}/1.0
- Engagement Trend: {engagement_trend}
- Concerns Detected: {', '.join(concerns) if concerns else 'None'}

Provide exactly 5 specific, actionable teaching suggestions to improve student engagement.

Return a JSON array where each element has:
  "priority": "high" | "medium" | "low"
  "category": "pacing" | "interaction" | "content" | "environment" | "assessment"
  "suggestion": "one-sentence action to take right now"
  "rationale": "why this helps"
  "implementation": "step-by-step how to do it"

Be practical, evidence-based, and empathetic. JSON only, no extra text."""

        result = self.generate_json(prompt)
        if isinstance(result, list):
            return result
        return []

    # ── Session Report ─────────────────────────────────────────────────────

    def generate_session_report(
        self,
        course: str,
        instructor: str,
        start_time: str,
        student_count: int,
        avg_engagement: float,
        timeline_points: int,
        top_students: List[Dict],
    ) -> Optional[str]:
        """Generate a professional markdown session report."""
        top_str = "\n".join(
            f"  - {s.get('name', 'Unknown')}: {s.get('avg_engagement', 0):.2f}"
            for s in top_students
        )

        prompt = f"""Generate a comprehensive classroom session analytics report as professional Markdown.

Session Data:
- Course: {course}
- Instructor: {instructor}
- Start Time: {start_time}
- Students Present: {student_count}
- Average Engagement Score: {avg_engagement:.2f}/1.0
- Engagement Data Points: {timeline_points}
- Top Performers:
{top_str or '  (none recorded)'}

Include these sections:
1. ## Executive Summary (2-3 sentences)
2. ## Attendance Analysis
3. ## Engagement Analysis (with observations)
4. ## Key Observations
5. ## Recommendations for Next Session
6. ## Student Recognition

Use professional, empathetic educator-friendly language. Markdown formatting only."""

        return self.generate_text(prompt)

    # ── Code Generation Engine ────────────────────────────────────────────

    def generate_educational_code(self, topic: str, difficulty: str = "intermediate") -> Dict[str, Any]:
        """
        Generate educational code exercises or demonstrations for the classroom.
        Returns dict with code snippet, explanation, and expected output.
        """
        prompt = f"""You are a computer science teaching assistant.
Generate a clean, executable Python demonstration script on the topic: "{topic}".
Difficulty level: {difficulty}.

Return ONLY a JSON object with:
- "title": string (short title)
- "code": string (clean, runnable python code without markdown fences)
- "explanation": string (brief explanation of what the code teaches)
- "expected_output": string (what printing this code produces)
- "suggested_exercise": string (a quick question or task for students to try)"""

        res = self.generate_json(prompt)
        if isinstance(res, dict) and "code" in res:
            return res

        # Fallback template if Gemini is offline
        return {
            "title": f"Demo: {topic}",
            "code": f"# Classroom Demonstration: {topic}\ndef demonstrate():\n    print('Exploring: {topic}')\n    for i in range(1, 4):\n        print(f'Step {{i}}: Analyzing engagement and attendance data')\n    return 'Demo Complete'\n\nprint(demonstrate())\n",
            "explanation": f"Interactive script demonstrating core principles of {topic}.",
            "expected_output": f"Exploring: {topic}\nStep 1: Analyzing engagement and attendance data\nStep 2: Analyzing engagement and attendance data\nStep 3: Analyzing engagement and attendance data\nDemo Complete",
            "suggested_exercise": "Modify the script to adjust parameters and re-run in the Code Executor."
        }

    # ── Gemini Image / Diagram Generation ─────────────────────────────────

    def generate_visual_aid_prompt(self, concept: str) -> Dict[str, Any]:
        """
        Generate visual aid description, SVG diagram or Gemini image prompt for teaching concept.
        """
        prompt = f"""You are an educational visual designer.
Create a visual aid description and Mermaid.js diagram or SVG illustration for the concept: "{concept}".

Return ONLY a JSON object with:
- "concept": "{concept}"
- "visual_description": string (detailed description of visual)
- "mermaid_diagram": string (valid mermaid flowchart/graph TD code)
- "teaching_talking_points": list of strings"""

        res = self.generate_json(prompt)
        if isinstance(res, dict) and "visual_description" in res:
            return res

        return {
            "concept": concept,
            "visual_description": f"A comprehensive visual breakdown explaining {concept}.",
            "mermaid_diagram": f"graph TD\n    A[Start: {concept}] --> B[Analyze Attendance]\n    B --> C[Compute Engagement Score]\n    C --> D[Generate AI Teaching Insight]\n    D --> E[Classroom Feedback Loop]",
            "teaching_talking_points": [
                f"Highlight the key mechanisms of {concept}",
                "Engage students with a real-time question",
                "Observe participation patterns before proceeding"
            ]
        }
