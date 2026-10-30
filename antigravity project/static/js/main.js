/* ═══════════════════════════════════════════════════
   main.js — Core JavaScript utilities
   SessionManager, ApiClient, ToastNotifier,
   RealTimeClock, SidebarController
   ═══════════════════════════════════════════════════ */

'use strict';

// ── ApiClient ──────────────────────────────────────────────
class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
  }

  async _request(method, path, body = null) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    try {
      const res = await fetch(this.baseUrl + path, opts);
      return await res.json();
    } catch (err) {
      console.error('[ApiClient]', method, path, err);
      return { success: false, error: err.message };
    }
  }

  get(path)        { return this._request('GET', path); }
  post(path, body) { return this._request('POST', path, body); }

  async getWithParams(path, params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this._request('GET', qs ? `${path}?${qs}` : path);
  }
}

// ── SessionManager ─────────────────────────────────────────
class SessionManager {
  constructor() {
    this._key = 'edutrack_session';
  }

  setSession(id, course = '', instructor = '') {
    const data = { id, course, instructor, startedAt: new Date().toISOString() };
    localStorage.setItem(this._key, JSON.stringify(data));
    this._updateBadge(id, true);
  }

  clearSession() {
    localStorage.removeItem(this._key);
    this._updateBadge('', false);
  }

  getSessionId() {
    const raw = localStorage.getItem(this._key);
    if (!raw) return null;
    try { return JSON.parse(raw).id; } catch { return null; }
  }

  getSession() {
    const raw = localStorage.getItem(this._key);
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
  }

  isActive() { return !!this.getSessionId(); }

  _updateBadge(id, active) {
    const dot   = document.getElementById('sessionDot');
    const label = document.getElementById('sessionLabel');
    if (!dot || !label) return;
    if (active) {
      dot.classList.add('active');
      label.textContent = id ? id.slice(0, 20) + '…' : 'Active Session';
    } else {
      dot.classList.remove('active');
      label.textContent = 'No Active Session';
    }
    // Update live indicator in navbar
    const liveInd = document.getElementById('liveIndicator');
    if (liveInd) liveInd.style.display = active ? 'flex' : 'none';
  }
}

// ── ToastNotifier ──────────────────────────────────────────
class ToastNotifier {
  constructor(containerId = 'toastContainer') {
    this._container = document.getElementById(containerId);
  }

  _show(message, type = 'info', duration = 3500) {
    if (!this._container) return;
    const icons = { success: 'fa-check-circle', error: 'fa-times-circle', info: 'fa-info-circle', warning: 'fa-exclamation-triangle' };
    const id = 'toast_' + Date.now();
    const html = `
      <div id="${id}" class="toast edu-toast toast-${type} show align-items-center mb-2" role="alert" aria-live="polite">
        <div class="d-flex align-items-center p-3 gap-2">
          <i class="fas ${icons[type] || icons.info}" style="font-size:1rem;color:var(--${type === 'error' ? 'danger' : type})"></i>
          <div class="flex-grow-1" style="font-size:0.88rem">${message}</div>
          <button type="button" class="btn-close btn-close-white btn-sm ms-2" onclick="document.getElementById('${id}').remove()"></button>
        </div>
      </div>`;
    this._container.insertAdjacentHTML('beforeend', html);
    setTimeout(() => { const el = document.getElementById(id); if (el) el.remove(); }, duration);
  }

  success(msg, dur) { this._show(msg, 'success', dur); }
  error(msg, dur)   { this._show(msg, 'error', dur || 5000); }
  info(msg, dur)    { this._show(msg, 'info', dur); }
  warning(msg, dur) { this._show(msg, 'warning', dur); }
}

// ── RealTimeClock ──────────────────────────────────────────
class RealTimeClock {
  constructor(elementId = 'currentTime') {
    this._el = document.getElementById(elementId);
    if (this._el) this._start();
  }

  _start() {
    const update = () => {
      const now = new Date();
      this._el.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    };
    update();
    setInterval(update, 1000);
  }
}

// ── SidebarController ──────────────────────────────────────
class SidebarController {
  constructor() {
    this._sidebar = document.getElementById('sidebar');
    this._overlay = document.getElementById('sidebarOverlay');
    this._toggleBtn = document.getElementById('sidebarToggle');
    this._closeBtn  = document.getElementById('sidebarClose');
    this._bind();
  }

  _bind() {
    if (this._toggleBtn) this._toggleBtn.addEventListener('click', () => this.open());
    if (this._closeBtn)  this._closeBtn.addEventListener('click',  () => this.close());
    if (this._overlay)   this._overlay.addEventListener('click',   () => this.close());
  }

  open() {
    this._sidebar?.classList.add('open');
    this._overlay?.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  close() {
    this._sidebar?.classList.remove('open');
    this._overlay?.classList.remove('show');
    document.body.style.overflow = '';
  }
}

// ── Settings helpers ───────────────────────────────────────
async function saveGeminiKey() {
  const key = document.getElementById('geminiKeyInput')?.value?.trim();
  if (!key) { window.notifier.warning('Please enter an API key.'); return; }
  const data = await window.api.post('/api/config/gemini', { api_key: key });
  if (data.success) {
    window.notifier.success('Gemini API key saved!');
    localStorage.setItem('gemini_key_set', '1');
    updateApiStatusBadge(true);
    bootstrap.Modal.getInstance(document.getElementById('settingsModal'))?.hide();
  } else {
    window.notifier.error('Failed to save key: ' + (data.message || 'unknown error'));
  }
}

function setTheme(theme) {
  localStorage.setItem('edu_theme', theme);
  window.notifier.info('Theme: ' + theme + ' (refresh to apply)');
}

function updateApiStatusBadge(connected) {
  const badge = document.getElementById('apiStatusBadge');
  const text  = document.getElementById('apiStatusText');
  if (!badge || !text) return;
  if (connected) {
    badge.classList.add('connected');
    text.textContent = 'AI Ready';
  } else {
    badge.classList.remove('connected');
    text.textContent = 'AI';
  }
}

// ── Init ───────────────────────────────────────────────────
window.api            = new ApiClient();
window.sessionManager = new SessionManager();
window.notifier       = new ToastNotifier();

document.addEventListener('DOMContentLoaded', () => {
  new RealTimeClock();
  new SidebarController();

  // Restore session badge on every page
  const sid = window.sessionManager.getSessionId();
  if (sid) {
    window.sessionManager._updateBadge(sid, true);
  }

  // Check if API key was previously set
  if (localStorage.getItem('gemini_key_set')) {
    updateApiStatusBadge(true);
  }
});
