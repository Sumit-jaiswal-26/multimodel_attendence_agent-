import os
import json
import base64
import time
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from utils import GeminiUtils, AudioUtils, EngagementAnalyzer, AttendanceTracker, CodeExecutor

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = 'static/audio'
REPORTS_FOLDER = 'reports'
STORAGE_CODE_FOLDER = 'storage/code'
STORAGE_AUDIO_FOLDER = 'storage/audio'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'jpg', 'jpeg', 'png'}

for folder in [UPLOAD_FOLDER, AUDIO_FOLDER, REPORTS_FOLDER, STORAGE_CODE_FOLDER, STORAGE_AUDIO_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# Gemini AI & Utilities setup
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
gemini_utils = GeminiUtils(GEMINI_API_KEY)
audio_utils = AudioUtils()
engagement_analyzer = EngagementAnalyzer()
attendance_tracker = AttendanceTracker()
code_executor = CodeExecutor()

genai_client = gemini_utils.client

def init_gemini():
    global genai_client, gemini_utils
    if GEMINI_API_KEY and genai:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            genai_client = genai.GenerativeModel('gemini-2.0-flash-exp')
            gemini_utils.set_api_key(GEMINI_API_KEY)
        except Exception as e:
            print(f"[Gemini Init Warning] {e}")

init_gemini()

# In-memory session store
sessions = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_session_id():
    return f"session_{int(time.time() * 1000)}"

# ─── Routes ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/attendance')
def attendance():
    return render_template('attendance.html')

@app.route('/engagement')
def engagement():
    return render_template('engagement.html')

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@app.route('/teaching-suggestions')
def teaching_suggestions():
    return render_template('suggestions.html')

@app.route('/code-studio')
def code_studio():
    return render_template('code_studio.html')

# ─── API: Session Management ────────────────────────────────────────────────

@app.route('/api/session/start', methods=['POST'])
def start_session():
    data = request.get_json() or {}
    session_id = generate_session_id()
    sessions[session_id] = {
        'id': session_id,
        'start_time': datetime.now().isoformat(),
        'course': data.get('course', 'Unknown Course'),
        'instructor': data.get('instructor', 'Unknown'),
        'students': {},
        'engagement_timeline': [],
        'audio_events': [],
        'status': 'active'
    }
    return jsonify({'success': True, 'session_id': session_id, 'message': 'Session started'})

@app.route('/api/session/end', methods=['POST'])
def end_session():
    data = request.get_json() or {}
    session_id = data.get('session_id')
    if session_id in sessions:
        sessions[session_id]['status'] = 'ended'
        sessions[session_id]['end_time'] = datetime.now().isoformat()
        # Save report
        report_path = os.path.join(REPORTS_FOLDER, f"{session_id}_report.json")
        with open(report_path, 'w') as f:
            json.dump(sessions[session_id], f, indent=2)
        return jsonify({'success': True, 'message': 'Session ended', 'report': sessions[session_id]})
    return jsonify({'success': False, 'message': 'Session not found'}), 404

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    session_list = []
    for sid, sdata in sessions.items():
        session_list.append({
            'id': sid,
            'course': sdata.get('course'),
            'instructor': sdata.get('instructor'),
            'start_time': sdata.get('start_time'),
            'status': sdata.get('status'),
            'student_count': len(sdata.get('students', {}))
        })
    # Also load from reports
    if os.path.exists(REPORTS_FOLDER):
        for fname in os.listdir(REPORTS_FOLDER):
            if fname.endswith('_report.json'):
                try:
                    with open(os.path.join(REPORTS_FOLDER, fname)) as f:
                        rdata = json.load(f)
                    if rdata['id'] not in sessions:
                        session_list.append({
                            'id': rdata['id'],
                            'course': rdata.get('course'),
                            'instructor': rdata.get('instructor'),
                            'start_time': rdata.get('start_time'),
                            'status': rdata.get('status'),
                            'student_count': len(rdata.get('students', {}))
                        })
                except Exception:
                    pass
    return jsonify({'sessions': session_list})

# ─── API: Attendance ────────────────────────────────────────────────────────

@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    data = request.get_json() or {}
    session_id = data.get('session_id')
    student_id = data.get('student_id')
    student_name = data.get('student_name', f'Student_{student_id}')
    confidence = data.get('confidence', 1.0)

    if session_id not in sessions:
        return jsonify({'success': False, 'message': 'Session not found'}), 404

    students = sessions[session_id]['students']
    now = datetime.now().isoformat()

    if student_id not in students:
        students[student_id] = {
            'id': student_id,
            'name': student_name,
            'first_seen': now,
            'last_seen': now,
            'presence_count': 1,
            'total_frames': 1,
            'status': 'present',
            'engagement_scores': [],
            'avg_engagement': 0.0
        }
        action = 'marked_present'
    else:
        students[student_id]['last_seen'] = now
        students[student_id]['presence_count'] += 1
        students[student_id]['total_frames'] = students[student_id].get('total_frames', 0) + 1
        action = 'updated'

    return jsonify({
        'success': True,
        'action': action,
        'student': students[student_id],
        'total_present': len(students)
    })

@app.route('/api/attendance/log', methods=['GET'])
def get_attendance_log():
    session_id = request.args.get('session_id')
    if session_id in sessions:
        return jsonify({
            'session_id': session_id,
            'students': list(sessions[session_id]['students'].values()),
            'total': len(sessions[session_id]['students']),
            'timestamp': datetime.now().isoformat()
        })
    return jsonify({'students': [], 'total': 0})

@app.route('/api/attendance/export', methods=['GET'])
def export_attendance():
    session_id = request.args.get('session_id')
    if session_id not in sessions:
        return jsonify({'success': False, 'message': 'Session not found'}), 404

    session = sessions[session_id]
    csv_lines = ['Student ID,Name,First Seen,Last Seen,Status,Avg Engagement']
    for sid, student in session['students'].items():
        csv_lines.append(
            f"{sid},{student['name']},{student.get('first_seen','')},{student.get('last_seen','')},{student.get('status','present')},{student.get('avg_engagement', 0):.2f}"
        )

    csv_content = '\n'.join(csv_lines)
    return jsonify({'success': True, 'csv': csv_content, 'session_id': session_id})

# ─── API: Engagement ────────────────────────────────────────────────────────

@app.route('/api/engagement/update', methods=['POST'])
def update_engagement():
    data = request.get_json() or {}
    session_id = data.get('session_id')
    student_id = data.get('student_id')
    engagement_score = float(data.get('engagement_score', 0.5))
    indicators = data.get('indicators', {})

    if session_id not in sessions:
        return jsonify({'success': False, 'message': 'Session not found'}), 404

    now = datetime.now().isoformat()
    # Update per-student engagement
    students = sessions[session_id]['students']
    if student_id in students:
        students[student_id]['engagement_scores'].append(engagement_score)
        scores = students[student_id]['engagement_scores']
        students[student_id]['avg_engagement'] = sum(scores) / len(scores)

    # Add to timeline
    sessions[session_id]['engagement_timeline'].append({
        'timestamp': now,
        'student_id': student_id,
        'score': engagement_score,
        'indicators': indicators
    })

    return jsonify({'success': True, 'timestamp': now})

@app.route('/api/engagement/trends', methods=['GET'])
def get_engagement_trends():
    session_id = request.args.get('session_id')
    if session_id not in sessions:
        return jsonify({'trends': [], 'avg_score': 0})

    timeline = sessions[session_id]['engagement_timeline']
    # Group by minute
    from collections import defaultdict
    minute_scores = defaultdict(list)
    for entry in timeline:
        ts = entry['timestamp'][:16]  # YYYY-MM-DDTHH:MM
        minute_scores[ts].append(entry['score'])

    trends = []
    for ts in sorted(minute_scores.keys()):
        scores = minute_scores[ts]
        trends.append({
            'time': ts,
            'avg_score': sum(scores) / len(scores),
            'count': len(scores)
        })

    overall_avg = 0
    if timeline:
        overall_avg = sum(e['score'] for e in timeline) / len(timeline)

    return jsonify({'trends': trends, 'avg_score': round(overall_avg, 3), 'session_id': session_id})

@app.route('/api/engagement/analyze-frame', methods=['POST'])
def analyze_frame():
    """Analyze a base64 image frame for engagement signals."""
    data = request.get_json() or {}
    image_b64 = data.get('image')
    session_id = data.get('session_id', '')

    if not image_b64:
        return jsonify({'success': False, 'message': 'No image provided'}), 400

    # Simulate CV analysis (replace with real CV model in production)
    import random
    engagement = {
        'head_pose': random.choice(['forward', 'down', 'left', 'right']),
        'movement': random.choice(['still', 'slight', 'active']),
        'attention': round(random.uniform(0.3, 1.0), 2),
        'faces_detected': random.randint(1, 5),
        'engagement_score': round(random.uniform(0.4, 0.95), 2)
    }

    # If Gemini configured, use it for richer analysis
    if genai_client and image_b64:
        try:
            image_bytes = base64.b64decode(image_b64.split(',')[-1])
            import PIL.Image, io
            img = PIL.Image.open(io.BytesIO(image_bytes))
            prompt = """Analyze this classroom image and provide:
1. Number of students visible and their attention level (attentive/distracted/absent)
2. Overall engagement score (0.0-1.0)
3. Behavioral observations (head pose, movement, interaction)
4. Any concerns or positive signals

Respond in JSON format with keys: faces_count, engagement_score, attention_states, observations, concerns"""
            response = genai_client.generate_content([prompt, img])
            try:
                text = response.text.strip()
                if '```json' in text:
                    text = text.split('```json')[1].split('```')[0]
                elif '```' in text:
                    text = text.split('```')[1].split('```')[0]
                ai_result = json.loads(text)
                engagement.update(ai_result)
            except Exception:
                pass
        except Exception as e:
            engagement['ai_error'] = str(e)

    return jsonify({'success': True, 'analysis': engagement})

# ─── API: AI Teaching Suggestions ─────────────────────────────────────────

@app.route('/api/suggestions/generate', methods=['POST'])
def generate_suggestions():
    data = request.get_json() or {}
    session_id = data.get('session_id', '')
    context = data.get('context', '')
    avg_engagement = data.get('avg_engagement', 0.5)
    engagement_trend = data.get('engagement_trend', 'stable')
    student_count = data.get('student_count', 0)
    concerns = data.get('concerns', [])

    prompt = f"""You are an expert educational assistant for a classroom session.

Session Context:
- Course/Topic: {context or 'General classroom session'}
- Students Present: {student_count}
- Average Engagement Score: {avg_engagement:.2f}/1.0
- Engagement Trend: {engagement_trend}
- Concerns Detected: {', '.join(concerns) if concerns else 'None'}

Based on this data, provide 5 specific, actionable teaching suggestions to improve student engagement and learning effectiveness.

Format your response as a JSON array with objects containing:
- "priority": "high"/"medium"/"low"
- "category": "pacing"/"interaction"/"content"/"environment"/"assessment"
- "suggestion": "specific action to take"
- "rationale": "why this will help"
- "implementation": "how to implement it"

Be practical, empathetic, and evidence-based."""

    suggestions = []

    if genai_client:
        try:
            response = genai_client.generate_content(prompt)
            text = response.text.strip()
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            suggestions = json.loads(text)
        except Exception as e:
            suggestions = get_fallback_suggestions(avg_engagement, engagement_trend)
    else:
        suggestions = get_fallback_suggestions(avg_engagement, engagement_trend)

    return jsonify({'success': True, 'suggestions': suggestions, 'generated_at': datetime.now().isoformat()})

def get_fallback_suggestions(avg_engagement, trend):
    if avg_engagement < 0.4:
        return [
            {"priority": "high", "category": "interaction", "suggestion": "Introduce a quick poll or quiz", "rationale": "Low engagement detected – interactive activities re-energize students", "implementation": "Ask 2-3 multiple choice questions related to recent content"},
            {"priority": "high", "category": "pacing", "suggestion": "Take a 5-minute break", "rationale": "Students show signs of fatigue", "implementation": "Allow students to stretch, discuss with neighbors, or reflect"},
            {"priority": "medium", "category": "content", "suggestion": "Switch to a visual or video demonstration", "rationale": "Change in modality can recapture attention", "implementation": "Show a relevant video clip or diagram"},
            {"priority": "medium", "category": "interaction", "suggestion": "Use think-pair-share activity", "rationale": "Peer discussion boosts engagement", "implementation": "Pose a question, give 2 min to think, 3 min to discuss with partner"},
            {"priority": "low", "category": "environment", "suggestion": "Check room temperature and lighting", "rationale": "Environmental factors affect attention", "implementation": "Adjust thermostat or open blinds if needed"}
        ]
    elif avg_engagement < 0.7:
        return [
            {"priority": "medium", "category": "interaction", "suggestion": "Pose open-ended discussion questions", "rationale": "Moderate engagement can be elevated through Socratic dialogue", "implementation": "Ask 'What do you think about...' questions"},
            {"priority": "medium", "category": "pacing", "suggestion": "Vary your speaking pace and volume", "rationale": "Monotone delivery reduces engagement", "implementation": "Emphasize key points with deliberate pauses"},
            {"priority": "low", "category": "assessment", "suggestion": "Use exit ticket at session end", "rationale": "Encourages reflection and accountability", "implementation": "Ask students to write one thing they learned"},
            {"priority": "low", "category": "content", "suggestion": "Connect content to real-world examples", "rationale": "Relevance increases motivation", "implementation": "Share a current news story or case study"},
            {"priority": "low", "category": "environment", "suggestion": "Encourage note-taking", "rationale": "Active note-taking improves retention", "implementation": "Provide a structured note template"}
        ]
    else:
        return [
            {"priority": "low", "category": "interaction", "suggestion": "Maintain current pace – engagement is high!", "rationale": "Students are attentive and engaged", "implementation": "Continue with current teaching strategy"},
            {"priority": "low", "category": "assessment", "suggestion": "Challenge engaged students with extension questions", "rationale": "High engagement is a great time to deepen understanding", "implementation": "Pose 'what if' or application-level questions"},
            {"priority": "low", "category": "pacing", "suggestion": "Consider introducing advanced concepts", "rationale": "Students are ready for more complex material", "implementation": "Gradually increase difficulty level"},
            {"priority": "low", "category": "content", "suggestion": "Incorporate student-generated examples", "rationale": "Learner agency reinforces engagement", "implementation": "Ask students to provide their own examples"},
            {"priority": "low", "category": "interaction", "suggestion": "Facilitate peer teaching moments", "rationale": "Teaching others deepens understanding", "implementation": "Have students explain concepts to each other"}
        ]

# ─── API: Audio Analysis ────────────────────────────────────────────────────

@app.route('/api/audio/analyze', methods=['POST'])
def analyze_audio():
    data = request.get_json() or {}
    session_id = data.get('session_id', '')
    audio_level = float(data.get('audio_level', 0))
    duration = float(data.get('duration', 0))

    event_type = 'silence'
    if audio_level > 0.7:
        event_type = 'high_activity'
    elif audio_level > 0.3:
        event_type = 'moderate_activity'
    elif audio_level > 0.1:
        event_type = 'low_activity'

    event = {
        'timestamp': datetime.now().isoformat(),
        'level': audio_level,
        'duration': duration,
        'type': event_type
    }

    if session_id in sessions:
        sessions[session_id]['audio_events'].append(event)

    return jsonify({'success': True, 'event': event})

@app.route('/api/audio/summary', methods=['GET'])
def audio_summary():
    session_id = request.args.get('session_id', '')
    if session_id not in sessions:
        return jsonify({'events': [], 'summary': {}})

    events = sessions[session_id]['audio_events']
    if not events:
        return jsonify({'events': [], 'summary': {'total': 0}})

    from collections import Counter
    type_counts = Counter(e['type'] for e in events)
    avg_level = sum(e['level'] for e in events) / len(events)

    return jsonify({
        'events': events[-50:],  # last 50 events
        'summary': {
            'total': len(events),
            'avg_level': round(avg_level, 3),
            'type_breakdown': dict(type_counts),
            'most_common': type_counts.most_common(1)[0][0] if type_counts else 'none'
        }
    })

# ─── API: Analytics ────────────────────────────────────────────────────────

@app.route('/api/analytics/session', methods=['GET'])
def session_analytics():
    session_id = request.args.get('session_id')
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404

    session = sessions[session_id]
    students = session['students']
    timeline = session['engagement_timeline']
    audio = session['audio_events']

    # Compute stats
    engagement_scores = [s['avg_engagement'] for s in students.values() if s.get('engagement_scores')]
    avg_eng = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0

    top_students = sorted(students.values(), key=lambda x: x.get('avg_engagement', 0), reverse=True)[:3]
    low_students = sorted(students.values(), key=lambda x: x.get('avg_engagement', 0))[:3]

    analytics = {
        'session_id': session_id,
        'course': session.get('course'),
        'instructor': session.get('instructor'),
        'start_time': session.get('start_time'),
        'status': session.get('status'),
        'attendance': {
            'total_present': len(students),
            'students': list(students.values())
        },
        'engagement': {
            'overall_avg': round(avg_eng, 3),
            'timeline_points': len(timeline),
            'top_engaged': [{'name': s['name'], 'score': s.get('avg_engagement', 0)} for s in top_students],
            'needs_attention': [{'name': s['name'], 'score': s.get('avg_engagement', 0)} for s in low_students]
        },
        'audio': {
            'total_events': len(audio),
            'avg_level': sum(a['level'] for a in audio) / len(audio) if audio else 0
        },
        'generated_at': datetime.now().isoformat()
    }

    return jsonify(analytics)

@app.route('/api/analytics/report', methods=['POST'])
def generate_ai_report():
    data = request.get_json() or {}
    session_id = data.get('session_id', '')

    if session_id not in sessions:
        return jsonify({'success': False, 'message': 'Session not found'}), 404

    session = sessions[session_id]
    students = session['students']
    timeline = session['engagement_timeline']

    engagement_scores = [s['avg_engagement'] for s in students.values() if s.get('engagement_scores')]
    avg_eng = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0.5

    if genai_client:
        prompt = f"""Generate a comprehensive classroom session analytics report.

Session Data:
- Course: {session.get('course', 'Unknown')}
- Instructor: {session.get('instructor', 'Unknown')}
- Start Time: {session.get('start_time', 'Unknown')}
- Students Present: {len(students)}
- Average Engagement Score: {avg_eng:.2f}/1.0
- Total Engagement Data Points: {len(timeline)}

Student Engagement Summary:
{json.dumps([{'name': s['name'], 'avg_engagement': s.get('avg_engagement', 0)} for s in list(students.values())[:10]], indent=2)}

Generate a professional report with:
1. Executive Summary (2-3 sentences)
2. Attendance Analysis
3. Engagement Analysis with trends
4. Key Observations
5. Recommendations for next session
6. Student Recognition (highlight top performers)

Write in a professional, empathetic tone suitable for educators."""

        try:
            response = genai_client.generate_content(prompt)
            return jsonify({'success': True, 'report': response.text, 'generated_at': datetime.now().isoformat()})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({
            'success': True,
            'report': f"""# Session Analytics Report

## Executive Summary
The classroom session recorded {len(students)} students present with an average engagement score of {avg_eng:.2f}/1.0.

## Attendance Analysis
- Total Students Present: {len(students)}
- Session Start: {session.get('start_time', 'N/A')}

## Engagement Analysis
- Overall Average Engagement: {avg_eng:.2f}/1.0
- Data Points Collected: {len(timeline)}

## Recommendations
- Continue monitoring engagement trends
- Use interactive activities to maintain high engagement
- Review individual student performance for personalized support
""",
            'generated_at': datetime.now().isoformat()
        })

# ─── API: Code Generation & Execution Engine ──────────────────────────────

@app.route('/api/code/generate', methods=['POST'])
def generate_code_endpoint():
    data = request.get_json() or {}
    topic = data.get('topic', 'Classroom Engagement Data Visualization')
    difficulty = data.get('difficulty', 'intermediate')
    result = gemini_utils.generate_educational_code(topic, difficulty)
    return jsonify({'success': True, 'data': result, 'generated_at': datetime.now().isoformat()})

@app.route('/api/code/execute', methods=['POST'])
def execute_code_endpoint():
    data = request.get_json() or {}
    code = data.get('code', '')
    prefix = data.get('prefix', 'snippet')
    if not code.strip():
        return jsonify({'success': False, 'message': 'No code provided'}), 400
    exec_result = code_executor.execute_python(code, prefix)
    return jsonify(exec_result)

@app.route('/storage/code/<filename>')
def serve_generated_code(filename):
    return send_from_directory(STORAGE_CODE_FOLDER, filename)

# ─── API: Text-to-Speech & Audio Signals ───────────────────────────────────

@app.route('/api/audio/tts', methods=['POST'])
def text_to_speech_endpoint():
    data = request.get_json() or {}
    text = data.get('text', '')
    if not text.strip():
        return jsonify({'success': False, 'message': 'Text cannot be empty'}), 400
    res = audio_utils.generate_tts_file(text, AUDIO_FOLDER)
    return jsonify(res)

# ─── API: Gemini Visual Aid & Diagram Generator ───────────────────────────

@app.route('/api/visual/generate', methods=['POST'])
def generate_visual_aid():
    data = request.get_json() or {}
    concept = data.get('concept', 'Multimodal Engagement Tracking Architecture')
    res = gemini_utils.generate_visual_aid_prompt(concept)
    return jsonify({'success': True, 'data': res, 'generated_at': datetime.now().isoformat()})

# ─── Static files ───────────────────────────────────────────────────────────

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    if f and allowed_file(f.filename):
        filename = secure_filename(f.filename)
        timestamp = int(time.time())
        filename = f"{timestamp}_{filename}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(save_path)
        return jsonify({'success': True, 'filename': filename, 'path': f'/uploads/{filename}'})
    return jsonify({'success': False, 'message': 'File type not allowed'}), 400

@app.route('/api/config/gemini', methods=['POST'])
def set_gemini_key():
    global GEMINI_API_KEY, genai_client, gemini_utils
    data = request.get_json() or {}
    key = data.get('api_key', '')
    if key:
        GEMINI_API_KEY = key
        gemini_utils.set_api_key(key)
        genai_client = gemini_utils.client
        if genai and genai_client is None:
            try:
                genai.configure(api_key=key)
                genai_client = genai.GenerativeModel('gemini-2.0-flash-exp')
            except Exception:
                pass
        return jsonify({'success': True, 'message': 'Gemini API key configured'})
    return jsonify({'success': False, 'message': 'No API key provided'}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
