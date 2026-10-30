"""
run.py — Quick launcher for EduTrack AI (Multimodal Attendance & Engagement Agent)
Usage:  python run.py
"""
import os
from dotenv import load_dotenv

load_dotenv()  # load .env file if present

from app import app

if __name__ == '__main__':
    host  = os.environ.get('HOST', '127.0.0.1')
    port  = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'

    print("\n" + "=" * 60)
    print("  🎓  EduTrack AI — Multimodal Attendance & Engagement Agent")
    print("=" * 60)
    print(f"  ▶  Server : http://{host}:{port}")
    print(f"  ▶  Debug  : {debug}")
    print(f"  ▶  Gemini : {'Configured ✓' if os.environ.get('GEMINI_API_KEY') else 'Not configured (set GEMINI_API_KEY in .env)'}")
    print("=" * 60 + "\n")

    app.run(host=host, port=port, debug=debug)
