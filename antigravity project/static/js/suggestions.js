/* ═══════════════════════════════════════════════════
   suggestions.js — Teaching suggestions page logic
   ═══════════════════════════════════════════════════ */

'use strict';

class SuggestionsManager {
  constructor() {
    this._history       = this._loadHistory();
    this._lastSuggestions = [];
    this._HISTORY_KEY   = 'edutrack_suggestions_history';

    this._init();
  }

  _init() {
    this._renderHistory();
    // Sync engagement slider display
    const slider = document.getElementById('engagementSlider');
    if (slider) this.updateSliderDisplay(slider.value);
  }

  // ── Slider display ─────────────────────────────────────
  updateSliderDisplay(val) {
    const disp = document.getElementById('sliderDisplay');
    if (!disp) return;
    const pct = parseInt(val, 10);
    disp.textContent = pct + '%';
    disp.style.color = pct >= 70 ? 'var(--success)' : pct >= 40 ? 'var(--warning)' : 'var(--danger)';
  }

  // ── Generate suggestions ───────────────────────────────
  async generateSuggestions() {
    const context       = document.getElementById('sugContextInput')?.value?.trim() || '';
    const concernsRaw   = document.getElementById('sugConcernsInput')?.value?.trim() || '';
    const engPct        = parseInt(document.getElementById('engagementSlider')?.value || 50, 10);
    const trend         = document.getElementById('trendSelect')?.value || 'stable';
    const studentCount  = parseInt(document.getElementById('studentCountInput')?.value || 25, 10);
    const avgEngagement = engPct / 100;
    const concerns      = concernsRaw ? concernsRaw.split(/[,\n]+/).map(c => c.trim()).filter(Boolean) : [];

    // Show loading state
    const btn = document.getElementById('generateBtn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="loading-spinner"></span>Generating…'; }

    const container = document.getElementById('suggestionsContainer');
    if (container) container.innerHTML = '<div class="text-center py-4"><span class="loading-spinner"></span> Asking Gemini AI…</div>';

    const res = await window.api.post('/api/suggestions/generate', {
      session_id:       window.sessionManager?.getSessionId() || '',
      context,
      avg_engagement:   avgEngagement,
      engagement_trend: trend,
      student_count:    studentCount,
      concerns,
    });

    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-lightbulb me-2"></i>Generate AI Suggestions'; }

    if (res.success && Array.isArray(res.suggestions) && res.suggestions.length > 0) {
      this._lastSuggestions = res.suggestions;
      this._renderSuggestions(res.suggestions, container);

      // Generated at timestamp
      const tsEl = document.getElementById('generatedAt');
      if (tsEl) {
        tsEl.textContent = 'Generated at ' + new Date(res.generated_at).toLocaleString();
        tsEl.style.display = 'block';
      }

      // Save to history
      this._saveToHistory({
        timestamp:  res.generated_at,
        context:    context || 'General Session',
        engagement: engPct + '%',
        count:      res.suggestions.length,
        suggestions: res.suggestions,
      });

      window.notifier.success(`${res.suggestions.length} suggestions generated!`);
    } else {
      if (container) container.innerHTML = '<div class="text-danger p-3">Failed to generate suggestions. Check your API key in Settings.</div>';
      window.notifier.error('Generation failed.');
    }
  }

  // ── Render suggestion cards ────────────────────────────
  _renderSuggestions(suggestions, container) {
    if (!container) return;
    const categoryIcons = {
      pacing:      '🎯',
      interaction: '💬',
      content:     '📚',
      environment: '🌍',
      assessment:  '✅',
    };

    container.innerHTML = suggestions.map((s, i) => {
      const icon = categoryIcons[s.category] || '💡';
      const priClass = `priority-${(s.priority || 'medium').toLowerCase()}`;
      return `
        <div class="suggestion-card" id="sug_${i}">
          <div class="suggestion-header">
            <span class="suggestion-title">${icon} ${s.suggestion}</span>
            <span class="priority-badge ${priClass}">${s.priority || 'medium'}</span>
            <span class="category-badge">${s.category || 'general'}</span>
          </div>
          <p class="suggestion-rationale"><i class="fas fa-info-circle me-1 opacity-50"></i>${s.rationale || ''}</p>
          <div class="suggestion-implementation">
            <i class="fas fa-check-circle me-1" style="color:var(--success)"></i>
            <strong>How:</strong> ${s.implementation || ''}
          </div>
          <div class="d-flex justify-content-end mt-2">
            <button class="btn btn-xs btn-outline-secondary" onclick="sugManager.copySuggestion(${i})">
              <i class="fas fa-copy me-1"></i>Copy
            </button>
          </div>
        </div>`;
    }).join('');
  }

  // ── Copy single suggestion ─────────────────────────────
  copySuggestion(index) {
    const s = this._lastSuggestions[index];
    if (!s) return;
    const text = `${s.suggestion}\n\nWhy: ${s.rationale}\nHow: ${s.implementation}`;
    navigator.clipboard.writeText(text)
      .then(() => window.notifier.success('Copied!'))
      .catch(() => window.notifier.error('Clipboard not available.'));
  }

  // ── Copy all suggestions ───────────────────────────────
  copyAllSuggestions() {
    if (!this._lastSuggestions.length) { window.notifier.warning('No suggestions to copy.'); return; }
    const text = this._lastSuggestions.map((s, i) =>
      `${i + 1}. [${s.priority?.toUpperCase()} / ${s.category}] ${s.suggestion}\n   Why: ${s.rationale}\n   How: ${s.implementation}`
    ).join('\n\n');
    navigator.clipboard.writeText(text)
      .then(() => window.notifier.success('All suggestions copied!'))
      .catch(() => window.notifier.error('Clipboard not available.'));
  }

  // ── Clear suggestions ──────────────────────────────────
  clearSuggestions() {
    this._lastSuggestions = [];
    const container = document.getElementById('suggestionsContainer');
    if (container) container.innerHTML = `
      <div class="suggestions-placeholder">
        <i class="fas fa-lightbulb fa-3x mb-3 opacity-30"></i>
        <p class="text-muted">Fill in the context form and click <strong>Generate AI Suggestions</strong>.</p>
      </div>`;
    const tsEl = document.getElementById('generatedAt');
    if (tsEl) tsEl.style.display = 'none';
  }

  // ── History ────────────────────────────────────────────
  _loadHistory() {
    try {
      return JSON.parse(localStorage.getItem('edutrack_suggestions_history') || '[]');
    } catch { return []; }
  }

  _saveToHistory(entry) {
    this._history.unshift(entry);
    if (this._history.length > 20) this._history = this._history.slice(0, 20);
    localStorage.setItem('edutrack_suggestions_history', JSON.stringify(this._history));
    this._renderHistory();
  }

  _renderHistory() {
    const container = document.getElementById('historyContainer');
    if (!container) return;
    if (!this._history.length) {
      container.innerHTML = '<div class="text-muted text-center py-3"><i class="fas fa-clock me-2"></i>No history yet.</div>';
      return;
    }
    container.innerHTML = this._history.map((h, i) => `
      <div class="history-item" onclick="sugManager.restoreHistory(${i})">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <span class="fw-semibold">${h.context || 'General Session'}</span>
            <span class="ms-2 badge category-badge">${h.count} suggestions</span>
            <span class="ms-2 badge category-badge">Engagement: ${h.engagement}</span>
          </div>
          <span class="history-ts">${new Date(h.timestamp).toLocaleString()}</span>
        </div>
      </div>
    `).join('');
  }

  restoreHistory(index) {
    const entry = this._history[index];
    if (!entry || !entry.suggestions) return;
    this._lastSuggestions = entry.suggestions;
    const container = document.getElementById('suggestionsContainer');
    this._renderSuggestions(entry.suggestions, container);
    window.notifier.info('Restored: ' + entry.context);
  }

  clearHistory() {
    if (!confirm('Clear all suggestion history?')) return;
    this._history = [];
    localStorage.removeItem('edutrack_suggestions_history');
    this._renderHistory();
    window.notifier.info('History cleared.');
  }
}

// ── Globals ────────────────────────────────────────────────
let sugManager;

function generateSuggestions()   { sugManager.generateSuggestions(); }
function clearSuggestions()      { sugManager.clearSuggestions(); }
function copyAllSuggestions()    { sugManager.copyAllSuggestions(); }
function clearHistory()          { sugManager.clearHistory(); }
function updateSliderDisplay(v)  { sugManager.updateSliderDisplay(v); }

document.addEventListener('DOMContentLoaded', () => {
  sugManager = new SuggestionsManager();
});
