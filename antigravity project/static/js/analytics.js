/* ═══════════════════════════════════════════════════
   analytics.js — Analytics dashboard logic
   ═══════════════════════════════════════════════════ */

'use strict';

class AnalyticsDashboard {
  constructor() {
    this._sessionData   = null;
    this._timeChart     = null;
    this._pieChart      = null;
    this._compChart     = null;
    this._currentReport = '';

    this._init();
  }

  async _init() {
    await this._loadSessionSelector();

    // Auto-load active session if one exists
    const sid = window.sessionManager?.getSessionId();
    if (sid) {
      const sel = document.getElementById('analyticsSessionSelect');
      if (sel) sel.value = sid;
      const inp = document.getElementById('analyticsSessionInput');
      if (inp) inp.value = sid;
      await this.loadSession(sid);
    }
  }

  // ── Session selector ───────────────────────────────────
  async _loadSessionSelector() {
    const data = await window.api.get('/api/sessions');
    const sel  = document.getElementById('analyticsSessionSelect');
    if (!sel) return;
    (data.sessions || []).forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.id;
      const ts = s.start_time ? new Date(s.start_time).toLocaleString() : '';
      opt.textContent = `${s.course || s.id} — ${s.status} — ${ts}`;
      sel.appendChild(opt);
    });
  }

  loadCurrentSession() {
    const sid = window.sessionManager?.getSessionId();
    if (!sid) { window.notifier.warning('No active session.'); return; }
    this.loadSession(sid);
  }

  // ── Load session data ──────────────────────────────────
  async loadSession(sessionId) {
    if (!sessionId) { window.notifier.warning('Please select or enter a session ID.'); return; }

    window.notifier.info('Loading analytics…');
    const data = await window.api.getWithParams('/api/analytics/session', { session_id: sessionId });

    if (data.error) {
      window.notifier.error('Session not found: ' + sessionId);
      return;
    }

    this._sessionData = data;
    this._renderSummaryCards(data);
    this._renderMetadata(data);
    this._renderEngagementChart(data);
    this._renderAttendancePie(data);
    this._renderStudentComparison(data);
    window.notifier.success('Analytics loaded!');
  }

  // ── Summary cards ──────────────────────────────────────
  _renderSummaryCards(data) {
    const cards = document.getElementById('summaryCards');
    if (cards) cards.style.removeProperty('display');

    const students = data.attendance?.students || [];
    const total    = students.length;
    const avgEng   = data.engagement?.overall_avg || 0;
    const topList  = data.engagement?.top_engaged || [];
    const topName  = topList[0]?.name || '—';
    const audioEvt = data.audio?.total_events || 0;

    this._set('anTotalStudents', total);
    this._set('anAvgEngagement', Math.round(avgEng * 100) + '%');
    this._set('anTopPerformer', topName);
    this._set('anAudioEvents', audioEvt);
  }

  _renderMetadata(data) {
    this._set('metaSessionId', data.session_id || '—');
    this._set('metaCourse', data.course || '—');
    this._set('metaInstructor', data.instructor || '—');
    this._set('metaStartTime', data.start_time ? new Date(data.start_time).toLocaleString() : '—');
    const statusEl = document.getElementById('metaStatus');
    if (statusEl) {
      statusEl.textContent = data.status || '—';
      statusEl.style.color = data.status === 'active' ? 'var(--success)' : 'var(--text-muted)';
    }
  }

  // ── Engagement over time chart ─────────────────────────
  _renderEngagementChart(data) {
    const ctx = document.getElementById('engagementTimeChart');
    if (!ctx) return;

    const students = data.attendance?.students || [];
    // Build synthetic timeline from student avg scores per index
    const labels = students.map((_, i) => `Student ${i + 1}`);
    const scores = students.map(s => s.avg_engagement || 0);

    if (this._timeChart) this._timeChart.destroy();
    this._timeChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Avg Engagement',
          data: scores,
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99,102,241,0.2)',
          tension: 0.4,
          fill: true,
          pointRadius: 5,
          pointBackgroundColor: scores.map(s =>
            s >= 0.7 ? '#10b981' : s >= 0.4 ? '#f59e0b' : '#ef4444'
          ),
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        scales: {
          x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y: {
            min: 0, max: 1,
            ticks: { color: '#94a3b8', callback: v => Math.round(v * 100) + '%' },
            grid: { color: 'rgba(255,255,255,0.05)' }
          }
        },
        plugins: { legend: { labels: { color: '#e2e8f0' } } }
      }
    });
  }

  // ── Attendance pie ─────────────────────────────────────
  _renderAttendancePie(data) {
    const ctx = document.getElementById('attendancePieChart');
    if (!ctx) return;

    const students = data.attendance?.students || [];
    const present  = students.filter(s => s.status === 'present').length;
    const absent   = students.length - present;

    if (this._pieChart) this._pieChart.destroy();
    this._pieChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Present', 'Absent'],
        datasets: [{
          data: [present, absent],
          backgroundColor: ['rgba(16,185,129,0.8)', 'rgba(239,68,68,0.5)'],
          borderColor: ['#10b981', '#ef4444'],
          borderWidth: 1,
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { labels: { color: '#e2e8f0' }, position: 'bottom' },
          tooltip: { callbacks: { label: c => `${c.label}: ${c.raw}` } }
        }
      }
    });
  }

  // ── Student comparison bar ─────────────────────────────
  _renderStudentComparison(data) {
    const ctx = document.getElementById('studentComparisonChart');
    if (!ctx) return;

    const students = data.attendance?.students || [];
    const sorted   = [...students].sort((a, b) => (b.avg_engagement || 0) - (a.avg_engagement || 0));

    if (this._compChart) this._compChart.destroy();
    this._compChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: sorted.map(s => s.name),
        datasets: [{
          label: 'Avg Engagement',
          data: sorted.map(s => s.avg_engagement || 0),
          backgroundColor: sorted.map(s =>
            (s.avg_engagement || 0) >= 0.7 ? 'rgba(16,185,129,0.7)'
            : (s.avg_engagement || 0) >= 0.4 ? 'rgba(245,158,11,0.7)'
            : 'rgba(239,68,68,0.7)'
          ),
          borderRadius: 6,
        }]
      },
      options: {
        responsive: true,
        scales: {
          x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y: {
            min: 0, max: 1,
            ticks: { color: '#94a3b8', callback: v => Math.round(v * 100) + '%' },
            grid: { color: 'rgba(255,255,255,0.05)' }
          }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  // ── Generate AI report ─────────────────────────────────
  async generateReport() {
    if (!this._sessionData) { window.notifier.warning('Load a session first.'); return; }
    const btn = document.getElementById('generateReportBtn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="loading-spinner"></span>Generating…'; }

    const res = await window.api.post('/api/analytics/report', { session_id: this._sessionData.session_id });

    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-robot me-1"></i>Generate AI Report'; }

    const container = document.getElementById('aiReportContainer');
    if (!container) return;

    if (res.success) {
      this._currentReport = res.report;
      // Render markdown-like formatting
      const html = this._renderMarkdown(res.report);
      container.innerHTML = `<div class="report-body">${html}</div>
        <div class="text-muted small mt-2">Generated at ${new Date(res.generated_at).toLocaleString()}</div>`;
      window.notifier.success('Report generated!');
    } else {
      container.innerHTML = `<div class="text-danger p-3">Failed: ${res.error || res.message || 'unknown'}</div>`;
      window.notifier.error('Report generation failed.');
    }
  }

  _renderMarkdown(text) {
    return text
      .replace(/^# (.+)$/gm,   '<h4 style="color:#a5b4fc;margin-top:1rem">$1</h4>')
      .replace(/^## (.+)$/gm,  '<h5 style="color:#e2e8f0;margin-top:0.75rem">$1</h5>')
      .replace(/^### (.+)$/gm, '<h6 style="color:#94a3b8;margin-top:0.5rem">$1</h6>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g,   '<em>$1</em>')
      .replace(/^- (.+)$/gm,   '<li style="margin-left:1rem;color:#e2e8f0">$1</li>')
      .replace(/\n\n/g,        '<br/><br/>');
  }

  // ── Export functions ───────────────────────────────────
  exportJSON() {
    if (!this._sessionData) { window.notifier.warning('Load a session first.'); return; }
    const blob = new Blob([JSON.stringify(this._sessionData, null, 2)], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url;
    a.download = `analytics_${this._sessionData.session_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
    window.notifier.success('JSON exported!');
  }

  async exportCSV() {
    if (!this._sessionData) { window.notifier.warning('Load a session first.'); return; }
    const res = await window.api.getWithParams('/api/attendance/export', { session_id: this._sessionData.session_id });
    if (res.success) {
      const blob = new Blob([res.csv], { type: 'text/csv' });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url;
      a.download = `attendance_${this._sessionData.session_id}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      window.notifier.success('CSV exported!');
    }
  }

  copyReport() {
    if (!this._currentReport) { window.notifier.warning('Generate a report first.'); return; }
    navigator.clipboard.writeText(this._currentReport)
      .then(() => window.notifier.success('Report copied to clipboard!'))
      .catch(() => window.notifier.error('Clipboard not available.'));
  }

  printReport() {
    if (!this._currentReport) { window.notifier.warning('Generate a report first.'); return; }
    const win = window.open('', '_blank');
    win.document.write(`<html><head><title>Session Report</title>
      <style>body{font-family:sans-serif;padding:20px;white-space:pre-wrap}</style></head>
      <body>${this._currentReport}</body></html>`);
    win.print();
  }

  // ── Utility ────────────────────────────────────────────
  _set(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }
}

// ── Globals ────────────────────────────────────────────────
let analyticsDashboard;

function loadSession(sid)      { analyticsDashboard.loadSession(sid); }
function loadCurrentSession()  { analyticsDashboard.loadCurrentSession(); }
function generateReport()      { analyticsDashboard.generateReport(); }
function exportJSON()          { analyticsDashboard.exportJSON(); }
function exportCSV()           { analyticsDashboard.exportCSV(); }
function copyReport()          { analyticsDashboard.copyReport(); }
function printReport()         { analyticsDashboard.printReport(); }

document.addEventListener('DOMContentLoaded', () => {
  analyticsDashboard = new AnalyticsDashboard();
});
