# 🎓 Multimodal Attendance & Engagement Agent

An AI-powered, privacy-preserving classroom intelligence system built with **Flask** and **Google Gemini 2.0 Flash**. Automatically tracks attendance, analyzes student engagement in real-time, generates AI-driven teaching suggestions, and provides session analytics.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎯 **Automated Attendance** | Detect & track participants from video/webcam with timestamped logs & CSV export |
| 📊 **Engagement Analysis** | Head pose, movement, audio activity & behavioral signal fusion into 0–1 engagement scores |
| 🤖 **AI Teaching Suggestions** | Context-aware, evidence-based suggestions powered by Google Gemini 2.0 Flash |
| 📈 **Session Analytics** | Charts (line, pie, bar), AI-generated markdown reports, JSON/CSV export |
| 🎙️ **Audio Activity Monitor** | Real-time audio level classification & silence detection |
| 📷 **Frame Analyzer** | Analyze webcam snapshots for engagement signals using Gemini Vision |
| 💻 **Code & AI Studio** | Generate & execute educational Python scripts, TTS announcements, visual diagrams |

---

## 🚀 Quick Start (Windows)

### Option A — One-Click Setup
Double-click **`setup_and_run.bat`** — it installs dependencies and starts the server automatically.

### Option B — Manual
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure Gemini API Key (optional for full AI features)
copy .env.example .env
# Edit .env → set GEMINI_API_KEY=your_key_here

# 3. Run
python run.py
```

Open **http://127.0.0.1:5000** in your browser.

> **Note:** The app works without a Gemini API key using built-in fallback logic. To unlock full AI features (smart suggestions, frame analysis, report generation), add your key via **Settings ⚙️** in the sidebar or in `.env`.

---

## 📁 Project Structure

```
antigravity project/
├── app.py                        # Flask application & all API routes
├── run.py                        # Pretty-print launcher
├── setup_and_run.bat             # Windows one-click setup & run
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
├── README.md
│
├── utils/
│   ├── __init__.py
│   ├── genai_utils.py            # Google Gemini AI: text, image, code, visual aids
│   ├── audio_utils.py            # Audio events, TTS engine, engagement signal
│   ├── engagement_analyzer.py    # Multi-signal engagement score computation
│   ├── attendance_tracker.py     # Attendance records, CSV/JSON export
│   └── code_executor.py          # Safe Python code execution engine
│
├── templates/
│   ├── base.html                 # Base layout: sidebar, topbar, modals
│   ├── index.html                # Landing page: hero, features, architecture
│   ├── dashboard.html            # Live session control, webcam, gauge, activity feed
│   ├── attendance.html           # Student table, mark present, search, CSV export
│   ├── engagement.html           # Real-time charts, frame analyzer, audio meter
│   ├── analytics.html            # Charts, AI report generation, metadata
│   ├── suggestions.html          # Context form, AI suggestions, history
│   └── code_studio.html          # Code editor, executor, TTS, visual aid generator
│
├── static/
│   ├── css/style.css             # Full custom stylesheet (glassmorphism dark theme)
│   └── js/
│       ├── main.js               # ApiClient, SessionManager, ToastNotifier, Clock
│       ├── attendance.js         # AttendanceManager class
│       ├── engagement.js         # EngagementMonitor, Chart.js, webcam
│       ├── analytics.js          # AnalyticsDashboard, charts, report renderer
│       ├── suggestions.js        # SuggestionsManager, history, clipboard
│       └── code_studio.js        # Code generate/execute, TTS, visual aids
│
├── storage/
│   ├── code/                     # Generated Python scripts
│   └── audio/                    # Generated audio chime files
│
├── static/audio/                 # TTS & audio files served to browser
├── uploads/                      # Uploaded media (images, video frames)
└── reports/                      # Session reports saved as JSON
```

---

## 🌐 API Reference

### Session Management
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/session/start` | Start a new session |
| POST | `/api/session/end` | End active session & save report |
| GET | `/api/sessions` | List all sessions |

### Attendance
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/attendance/mark` | Mark student present |
| GET | `/api/attendance/log?session_id=` | Get attendance log |
| GET | `/api/attendance/export?session_id=` | Export CSV |

### Engagement
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/engagement/update` | Add engagement data point |
| GET | `/api/engagement/trends?session_id=` | Get trends by minute |
| POST | `/api/engagement/analyze-frame` | Analyze base64 image frame |

### AI Features
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/suggestions/generate` | Get teaching suggestions |
| POST | `/api/analytics/report` | Generate AI session report |
| POST | `/api/code/generate` | Generate educational Python code |
| POST | `/api/code/execute` | Execute code safely |
| POST | `/api/audio/tts` | Text-to-speech → save audio file |
| POST | `/api/visual/generate` | Gemini visual aid / Mermaid diagram |
| POST | `/api/config/gemini` | Set Gemini API key at runtime |

---

## 🏗️ System Architecture

```
Frontend Layer                    AI Service Layer
──────────────────               ──────────────────────────────
HTML5 Templates    ──────────►   Google Gemini 2.0 Flash
CSS3 Styling                     Gemini Image Generation
JavaScript Controllers           Text-to-Speech Engine
Chart.js                         Code Generation Engine
         │
         ▼
Flask API Gateway
──────────────────
Route Handlers
GenAI Utils
Audio Utils
Code Executor
Engagement Analyzer
Attendance Tracker
         │
         ▼
Storage Layer         Utility Layer
──────────────       ──────────────────────────
Generated Audio      Uploaded Files
Generated Code       Reports (JSON)
Session Data         Local Browser Storage
```

---

## ⚙️ System Requirements

- **Python** 3.8 or above
- **RAM:** 8 GB minimum (16 GB recommended)
- **OS:** Windows 10/11, macOS Monterey+, Ubuntu 20.04+
- **Browser:** Chrome, Firefox, or Edge (latest)
- **Internet:** Required only for Gemini API calls (optional)

---

## 📝 License
MIT — Free for educational and research use.
