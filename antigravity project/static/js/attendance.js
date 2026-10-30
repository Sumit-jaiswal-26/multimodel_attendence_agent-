/* ═══════════════════════════════════════════════════
   attendance.js — Attendance page logic
   ═══════════════════════════════════════════════════ */

'use strict';

class AttendanceManager {
  constructor() {
    this._students = [];
    this._pollInterval = null;
    this._refreshMs = 5000;
    this._init();
  }

  _init() {
    // Pre-fill session ID from active session
    const sid = window.sessionManager?.getSessionId();
    const input = document.getElementById('attSessionId');
    if (sid && input) input.value = sid;

    // Load sessions into selector
    this._loadSessionSelector();

    // Start polling if session active
    if (sid) this._startPolling(sid);

    // Initial load
    this.loadLog(sid || '');
  }

  // ── Session selector ───────────────────────────────────
  async _loadSessionSelector() {
    try {
      const data = await window.api.get('/api/sessions');
      const sel = document.getElementById('sessionSelector');
      if (!sel) return;
      const sessions = data.sessions || [];
      sessions.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.id;
        const ts = s.start_time ? new Date(s.start_time).toLocaleString() : '';
        opt.textContent = `${s.course || s.id} (${s.status}) — ${ts}`;
        sel.appendChild(opt);
      });
      // Pre-select active session
      const sid = window.sessionManager?.getSessionId();
      if (sid) sel.value = sid;
    } catch (e) {
      console.warn('[Attendance] Could not load sessions', e);
    }
  }

  // ── Mark present ───────────────────────────────────────
  async markStudent(id, name, sessionId) {
    const sid = sessionId || document.getElementById('attSessionId')?.value?.trim();
    if (!sid) { window.notifier.warning('No session ID. Start a session first.'); return null; }
    if (!id)  { window.notifier.warning('Please enter a Student ID.'); return null; }

    const data = await window.api.post('/api/attendance/mark', {
      session_id: sid,
      student_id: id,
      student_name: name || `Student_${id}`,
      confidence: 1.0
    });

    if (data.success) {
      const action = data.action === 'marked_present' ? 'Marked present' : 'Updated';
      window.notifier.success(`${action}: ${name || id}`);
      this.loadLog(sid);
    } else {
      window.notifier.error(data.message || 'Failed to mark student.');
    }
    return data;
  }

  // ── Bulk demo ──────────────────────────────────────────
  async markBulk() {
    const sid = document.getElementById('attSessionId')?.value?.trim()
      || window.sessionManager?.getSessionId();
    if (!sid) { window.notifier.warning('No active session. Start one from the Dashboard.'); return; }

    const demos = [
      { id: 'S001', name: 'Alice Johnson' },
      { id: 'S002', name: 'Bob Martinez' },
      { id: 'S003', name: 'Carol Chen' },
      { id: 'S004', name: 'David Kim' },
      { id: 'S005', name: 'Eva Patel' },
    ];

    for (const s of demos) {
      await window.api.post('/api/attendance/mark', {
        session_id: sid, student_id: s.id, student_name: s.name, confidence: 0.95
      });
    }
    window.notifier.success('5 demo students added!');
    this.loadLog(sid);
  }

  // ── Load log ───────────────────────────────────────────
  async loadLog(sessionId) {
    const sid = sessionId || document.getElementById('attSessionId')?.value?.trim()
      || window.sessionManager?.getSessionId();
    if (!sid) return;

    const data = await window.api.getWithParams('/api/attendance/log', { session_id: sid });
    this._students = data.students || [];

    // Update stats
    const total = this._students.length;
    document.getElementById('attTotalPresent').textContent = total;
    document.getElementById('attRegistered').textContent   = total;

    const pct = total > 0 ? Math.round(
      this._students.filter(s => s.status === 'present').length / total * 100
    ) : 0;
    document.getElementById('attPercentage').textContent = pct + '%';
    document.getElementById('attLastUpdated').textContent = new Date().toLocaleTimeString();

    this.renderTable(this._students);
  }

  // ── Render table ───────────────────────────────────────
  renderTable(students) {
    const tbody = document.getElementById('attendanceTableBody');
    if (!tbody) return;

    if (!students || students.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="text-center text-muted py-4">
            <i class="fas fa-inbox fa-2x mb-2 d-block opacity-50"></i>
            No students recorded yet.
          </td>
        </tr>`;
      return;
    }

    tbody.innerHTML = students.map(s => {
      const engPct  = Math.round((s.avg_engagement || 0) * 100);
      const engColor = engPct >= 70 ? 'var(--success)' : engPct >= 40 ? 'var(--warning)' : 'var(--danger)';
      const firstSeen = s.first_seen ? new Date(s.first_seen).toLocaleTimeString() : '—';
      const lastSeen  = s.last_seen  ? new Date(s.last_seen).toLocaleTimeString()  : '—';
      return `
        <tr>
          <td><code>${s.id}</code></td>
          <td class="fw-semibold">${s.name}</td>
          <td><span class="badge badge-${s.status === 'present' ? 'present' : 'absent'}">${s.status || 'present'}</span></td>
          <td>${firstSeen}</td>
          <td>${lastSeen}</td>
          <td>
            <div class="d-flex align-items-center gap-2">
              <div style="flex:1;height:6px;background:rgba(255,255,255,0.1);border-radius:3px;overflow:hidden">
                <div style="width:${engPct}%;height:100%;background:${engColor};border-radius:3px"></div>
              </div>
              <span style="font-size:0.78rem;min-width:32px">${engPct}%</span>
            </div>
          </td>
          <td>
            <button class="btn btn-xs btn-outline-danger" onclick="attManager.markAbsent('${s.id}')">
              <i class="fas fa-times"></i>
            </button>
          </td>
        </tr>`;
    }).join('');
  }

  // ── Search filter ──────────────────────────────────────
  filterStudents(query) {
    if (!query) { this.renderTable(this._students); return; }
    const q = query.toLowerCase();
    const filtered = this._students.filter(s =>
      s.name.toLowerCase().includes(q) || s.id.toLowerCase().includes(q)
    );
    this.renderTable(filtered);
  }

  // ── Mark absent ────────────────────────────────────────
  async markAbsent(studentId) {
    window.notifier.info(`Marked ${studentId} as absent (local only).`);
    this._students = this._students.map(s =>
      s.id === studentId ? { ...s, status: 'absent' } : s
    );
    this.renderTable(this._students);
  }

  // ── Export CSV ─────────────────────────────────────────
  async exportCSV() {
    const sid = document.getElementById('attSessionId')?.value?.trim()
      || window.sessionManager?.getSessionId()
      || document.getElementById('sessionSelector')?.value;
    if (!sid) { window.notifier.warning('No session selected.'); return; }

    const data = await window.api.getWithParams('/api/attendance/export', { session_id: sid });
    if (data.success) {
      const blob = new Blob([data.csv], { type: 'text/csv' });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url;
      a.download = `attendance_${sid}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      window.notifier.success('CSV exported!');
    } else {
      window.notifier.error(data.message || 'Export failed.');
    }
  }

  // ── Auto-refresh polling ───────────────────────────────
  _startPolling(sid) {
    this._pollInterval = setInterval(() => this.loadLog(sid), this._refreshMs);
  }

  stopPolling() {
    if (this._pollInterval) { clearInterval(this._pollInterval); this._pollInterval = null; }
  }

  // ── Session change ─────────────────────────────────────
  onSessionChange(val) {
    const input = document.getElementById('attSessionId');
    if (input) input.value = val;
    this.stopPolling();
    this.loadLog(val);
    if (val) this._startPolling(val);
  }
}

// ── Global instance & helpers ──────────────────────────────
let attManager;

function markStudent() {
  const id   = document.getElementById('attStudentId')?.value?.trim();
  const name = document.getElementById('attStudentName')?.value?.trim();
  attManager.markStudent(id, name);
  document.getElementById('attStudentId').value   = '';
  document.getElementById('attStudentName').value = '';
}

function markBulk()             { attManager.markBulk(); }
function refreshLog()           { attManager.loadLog(); }
function filterStudents()       { attManager.filterStudents(document.getElementById('searchInput')?.value); }
function exportCSV()            { attManager.exportCSV(); }
function onSessionChange()      { attManager.onSessionChange(document.getElementById('sessionSelector')?.value); }

document.addEventListener('DOMContentLoaded', () => {
  attManager = new AttendanceManager();
});
