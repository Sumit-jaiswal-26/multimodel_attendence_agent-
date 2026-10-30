/* ═══════════════════════════════════════════════════
   engagement.js — Engagement monitor page logic
   ═══════════════════════════════════════════════════ */

'use strict';

class EngagementMonitor {
  constructor() {
    this._running     = false;
    this._interval    = null;
    this._scenario    = 'normal';
    this._history     = [];
    this._maxPoints   = 40;
    this._lineChart   = null;
    this._barChart    = null;
    this._intervalChart = null;
    this._intervalData  = [];  // 5-min aggregated
    this._frameStream   = null;

    // Per-student demo data
    this._students = [
      { id: 'S001', name: 'Alice',   score: 0.82 },
      { id: 'S002', name: 'Bob',     score: 0.55 },
      { id: 'S003', name: 'Carol',   score: 0.73 },
      { id: 'S004', name: 'David',   score: 0.40 },
      { id: 'S005', name: 'Eva',     score: 0.91 },
    ];

    this._init();
  }

  _init() {
    this._initLineChart();
    this._initBarChart();
    this._initIntervalChart();

    // Show active session label
    const sid = window.sessionManager?.getSessionId();
    const lbl = document.getElementById('engSessionLabel');
    if (lbl) lbl.textContent = sid ? `Session: ${sid.slice(0, 24)}…` : 'None active';
  }

  // ── Line Chart ─────────────────────────────────────────
  _initLineChart() {
    const ctx = document.getElementById('engagementLineChart');
    if (!ctx) return;
    this._lineChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Engagement Score',
          data: [],
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99,102,241,0.15)',
          tension: 0.4,
          fill: true,
          pointRadius: 3,
          pointBackgroundColor: '#6366f1',
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        animation: { duration: 400 },
        scales: {
          x: { ticks: { color: '#94a3b8', maxTicksLimit: 8 }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y: {
            min: 0, max: 1,
            ticks: { color: '#94a3b8', callback: v => Math.round(v * 100) + '%' },
            grid: { color: 'rgba(255,255,255,0.05)' }
          }
        },
        plugins: {
          legend: { labels: { color: '#e2e8f0' } },
          tooltip: { callbacks: { label: ctx => `${Math.round(ctx.raw * 100)}%` } }
        }
      }
    });
  }

  // ── Bar Chart (per-student) ────────────────────────────
  _initBarChart() {
    const ctx = document.getElementById('studentEngagementChart');
    if (!ctx) return;
    this._barChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: this._students.map(s => s.name),
        datasets: [{
          label: 'Engagement',
          data: this._students.map(s => s.score),
          backgroundColor: this._students.map(s =>
            s.score >= 0.7 ? 'rgba(16,185,129,0.7)'
            : s.score >= 0.4 ? 'rgba(245,158,11,0.7)'
            : 'rgba(239,68,68,0.7)'
          ),
          borderRadius: 6,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        animation: { duration: 500 },
        scales: {
          x: {
            min: 0, max: 1,
            ticks: { color: '#94a3b8', callback: v => Math.round(v*100)+'%' },
            grid: { color: 'rgba(255,255,255,0.05)' }
          },
          y: { ticks: { color: '#e2e8f0' }, grid: { display: false } }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  // ── Interval Chart (5-min) ─────────────────────────────
  _initIntervalChart() {
    const ctx = document.getElementById('intervalChart');
    if (!ctx) return;
    this._intervalChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: [],
        datasets: [{
          label: 'Avg Engagement per 5min',
          data: [],
          backgroundColor: [],
          borderRadius: 6,
          borderSkipped: false,
        }]
      },
      options: {
        responsive: true,
        animation: { duration: 500 },
        scales: {
          x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y: {
            min: 0, max: 1,
            ticks: { color: '#94a3b8', callback: v => Math.round(v*100)+'%' },
            grid: { color: 'rgba(255,255,255,0.05)' }
          }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  // ── Generate signals ───────────────────────────────────
  _simulateSignals() {
    const scenarios = {
      normal:     { range: [0.45, 0.82], poses: ['forward','slight_down','forward'], movements: ['slight','still','slight'], gaze: [0.6, 0.9], audio: [0.25, 0.55] },
      engaged:    { range: [0.70, 0.97], poses: ['forward','forward'], movements: ['slight','moderate'], gaze: [0.75, 1.0], audio: [0.40, 0.70] },
      distracted: { range: [0.20, 0.55], poses: ['left','right','down'], movements: ['active','fidgeting'], gaze: [0.2, 0.5], audio: [0.05, 0.30] },
      mixed:      { range: [0.35, 0.90], poses: ['forward','down','left','forward'], movements: ['slight','fidgeting','still','moderate'], gaze: [0.35, 0.90], audio: [0.15, 0.65] },
    };
    const cfg = scenarios[this._scenario] || scenarios.normal;
    const [lo, hi] = cfg.range;
    const score = lo + Math.random() * (hi - lo);
    return {
      score,
      head_pose:    cfg.poses[Math.floor(Math.random() * cfg.poses.length)],
      movement:     cfg.movements[Math.floor(Math.random() * cfg.movements.length)],
      gaze:         cfg.gaze[0] + Math.random() * (cfg.gaze[1] - cfg.gaze[0]),
      audio_level:  cfg.audio[0] + Math.random() * (cfg.audio[1] - cfg.audio[0]),
    };
  }

  // ── Tick ───────────────────────────────────────────────
  _tick() {
    const signals = this._simulateSignals();
    const { score, head_pose, movement, gaze, audio_level } = signals;
    const pct = Math.round(score * 100);
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    // Update line chart
    this._history.push({ time: now, score });
    if (this._history.length > this._maxPoints) this._history.shift();

    if (this._lineChart) {
      this._lineChart.data.labels   = this._history.map(h => h.time);
      this._lineChart.data.datasets[0].data = this._history.map(h => h.score);
      this._lineChart.update('none');
    }

    // Update status bar
    const badge = document.getElementById('currentScoreBadge');
    if (badge) {
      badge.textContent = pct + '%';
      badge.style.background = pct >= 70 ? 'rgba(16,185,129,0.2)' : pct >= 40 ? 'rgba(245,158,11,0.2)' : 'rgba(239,68,68,0.2)';
      badge.style.color      = pct >= 70 ? 'var(--success)' : pct >= 40 ? 'var(--warning)' : 'var(--danger)';
      badge.style.border     = `1px solid ${pct >= 70 ? 'rgba(16,185,129,0.4)' : pct >= 40 ? 'rgba(245,158,11,0.4)' : 'rgba(239,68,68,0.4)'}`;
      badge.style.borderRadius = '12px';
      badge.style.padding    = '4px 14px';
      badge.style.fontWeight = '700';
    }

    // Trend
    this._updateTrend();

    // Signals
    this._updateSignal('headPoseVal', 'headPoseBar', head_pose, this._poseScore(head_pose));
    this._updateSignal('movementVal', 'movementBar', movement, this._movementScore(movement));
    this._updateSignal('gazeVal', 'gazeBar', (gaze * 100).toFixed(0) + '%', gaze,
      pct >= 70 ? '#10b981' : pct >= 40 ? '#f59e0b' : '#ef4444');

    // Audio meter
    const audioEl = document.getElementById('audioMeterFill');
    const audioLbl = document.getElementById('audioLevelVal');
    if (audioEl) audioEl.style.width = Math.round(audio_level * 100) + '%';
    if (audioLbl) audioLbl.textContent = audio_level > 0.6 ? 'High' : audio_level > 0.3 ? 'Moderate' : 'Low';

    // Update per-student bars
    this._tickStudents();

    // Update interval chart (every 10 ticks ≈ 30s)
    this._tickIntervals(score, now);

    // Post to backend
    const sid = window.sessionManager?.getSessionId();
    if (sid) {
      window.api.post('/api/engagement/update', {
        session_id: sid, student_id: 'live_monitor', engagement_score: score,
        indicators: { head_pose, movement, audio_level }
      }).catch(() => {});
    }
  }

  _poseScore(pose) {
    const map = { forward: 1, slight_down: 0.85, down: 0.5, left: 0.6, right: 0.6, up: 0.7 };
    return map[pose] || 0.5;
  }

  _movementScore(m) {
    const map = { still: 0.65, slight: 1, moderate: 0.8, active: 0.55, fidgeting: 0.35 };
    return map[m] || 0.65;
  }

  _updateSignal(labelId, barId, labelText, fraction, color) {
    const lbl = document.getElementById(labelId);
    const bar = document.getElementById(barId);
    if (lbl) lbl.textContent = labelText;
    if (bar) {
      bar.style.width = Math.round(fraction * 100) + '%';
      if (color) bar.style.background = color;
      else {
        const pct = fraction * 100;
        bar.style.background = pct >= 70 ? '#10b981' : pct >= 40 ? '#f59e0b' : '#ef4444';
      }
    }
  }

  _updateTrend() {
    if (this._history.length < 6) return;
    const half  = Math.floor(this._history.length / 2);
    const first = this._history.slice(0, half).reduce((s, h) => s + h.score, 0) / half;
    const second = this._history.slice(half).reduce((s, h) => s + h.score, 0) / (this._history.length - half);
    const delta = second - first;
    const el = document.getElementById('trendIndicator');
    if (!el) return;
    if (delta > 0.05) { el.textContent = '↑ Rising';      el.className = 'trend-badge trend-rising'; }
    else if (delta < -0.05) { el.textContent = '↓ Falling'; el.className = 'trend-badge trend-falling'; }
    else { el.textContent = '→ Stable'; el.className = 'trend-badge trend-stable'; }
  }

  _tickStudents() {
    // Slightly vary each student's score
    this._students = this._students.map(s => ({
      ...s,
      score: Math.max(0.05, Math.min(0.99, s.score + (Math.random() - 0.5) * 0.06))
    }));
    if (!this._barChart) return;
    this._barChart.data.datasets[0].data = this._students.map(s => s.score);
    this._barChart.data.datasets[0].backgroundColor = this._students.map(s =>
      s.score >= 0.7 ? 'rgba(16,185,129,0.7)' : s.score >= 0.4 ? 'rgba(245,158,11,0.7)' : 'rgba(239,68,68,0.7)'
    );
    this._barChart.update('none');
  }

  _tickCounter = 0;
  _intervalBucket = [];
  _tickIntervals(score, now) {
    this._tickCounter++;
    this._intervalBucket.push(score);
    if (this._tickCounter % 10 === 0) {
      const avg = this._intervalBucket.reduce((a, b) => a + b, 0) / this._intervalBucket.length;
      this._intervalData.push({ label: now, avg });
      this._intervalBucket = [];
      if (this._intervalData.length > 12) this._intervalData.shift();
      if (this._intervalChart) {
        this._intervalChart.data.labels = this._intervalData.map(d => d.label);
        this._intervalChart.data.datasets[0].data = this._intervalData.map(d => d.avg);
        this._intervalChart.data.datasets[0].backgroundColor = this._intervalData.map(d =>
          d.avg >= 0.7 ? 'rgba(16,185,129,0.7)' : d.avg >= 0.4 ? 'rgba(245,158,11,0.7)' : 'rgba(239,68,68,0.7)'
        );
        this._intervalChart.update('none');
      }
    }
  }

  // ── Start / Stop ───────────────────────────────────────
  startMonitoring() {
    if (this._running) return;
    this._running = true;
    this._interval = setInterval(() => this._tick(), 3000);
    this._tick(); // immediate
    document.getElementById('engStartMonitor').disabled = true;
    document.getElementById('engStopMonitor').disabled  = false;
    window.notifier.info('Engagement monitoring started.');
  }

  stopMonitoring() {
    if (!this._running) return;
    this._running = false;
    clearInterval(this._interval);
    this._interval = null;
    document.getElementById('engStartMonitor').disabled = false;
    document.getElementById('engStopMonitor').disabled  = true;
    window.notifier.info('Monitoring paused.');
  }

  clearChart() {
    this._history = [];
    this._intervalData = [];
    if (this._lineChart)     { this._lineChart.data.labels = [];     this._lineChart.data.datasets[0].data = [];     this._lineChart.update(); }
    if (this._intervalChart) { this._intervalChart.data.labels = []; this._intervalChart.data.datasets[0].data = []; this._intervalChart.update(); }
    window.notifier.info('Chart cleared.');
  }

  setScenario(val) { this._scenario = val; }

  // ── Frame analysis ─────────────────────────────────────
  async analyzeUploadedFrame(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (e) => {
      const b64 = e.target.result;
      await this._sendFrameForAnalysis(b64);
    };
    reader.readAsDataURL(file);
  }

  async startFrameCamera() {
    const video = document.getElementById('frameVideo');
    if (!video) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      video.srcObject = stream;
      video.style.display = 'block';
      this._frameStream = stream;

      // Capture frame after 1.5s
      setTimeout(async () => {
        const canvas = document.getElementById('frameCanvas');
        canvas.width  = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        const b64 = canvas.toDataURL('image/jpeg', 0.8);
        stream.getTracks().forEach(t => t.stop());
        video.style.display = 'none';
        this._lastFrame = b64;
        await this._sendFrameForAnalysis(b64);
      }, 1500);
    } catch (e) {
      window.notifier.error('Camera error: ' + e.message);
    }
  }

  async analyzeStoredFrame() {
    if (!this._lastFrame) { window.notifier.warning('Capture a frame first.'); return; }
    await this._sendFrameForAnalysis(this._lastFrame);
  }

  async _sendFrameForAnalysis(b64) {
    const sid = window.sessionManager?.getSessionId() || '';
    const res = await window.api.post('/api/engagement/analyze-frame', { image: b64, session_id: sid });
    const panel = document.getElementById('frameResults');
    if (!panel) return;
    if (res.success) {
      const a = res.analysis;
      const eng = Math.round((a.engagement_score || 0) * 100);
      panel.innerHTML = `
        <div class="frame-result-grid mt-2">
          <div class="fr-item"><span class="fr-label">Faces Detected</span><span class="fr-val">${a.faces_detected || a.faces_count || '—'}</span></div>
          <div class="fr-item"><span class="fr-label">Engagement</span><span class="fr-val">${eng}%</span></div>
          <div class="fr-item"><span class="fr-label">Head Pose</span><span class="fr-val">${a.head_pose || '—'}</span></div>
          <div class="fr-item"><span class="fr-label">Movement</span><span class="fr-val">${a.movement || '—'}</span></div>
          ${a.observations ? `<div class="fr-item" style="grid-column:1/-1"><span class="fr-label">Observations</span><span class="fr-val" style="font-size:0.78rem">${a.observations}</span></div>` : ''}
        </div>`;
      window.notifier.success('Frame analyzed: ' + eng + '% engagement');
    } else {
      panel.innerHTML = `<div class="text-danger small mt-2">Analysis failed: ${res.message || 'unknown error'}</div>`;
    }
  }
}

// ── Globals ────────────────────────────────────────────────
let engMonitor;

function startMonitoring()          { engMonitor.startMonitoring(); }
function stopMonitoring()           { engMonitor.stopMonitoring(); }
function clearChart()               { engMonitor.clearChart(); }
function setScenario(val)           { engMonitor.setScenario(val); }
function analyzeUploadedFrame(ev)   { engMonitor.analyzeUploadedFrame(ev); }
function startFrameCamera()         { engMonitor.startFrameCamera(); }
function analyzeStoredFrame()       { engMonitor.analyzeStoredFrame(); }

document.addEventListener('DOMContentLoaded', () => {
  engMonitor = new EngagementMonitor();
  // Auto-start monitoring
  setTimeout(() => engMonitor.startMonitoring(), 600);
});
