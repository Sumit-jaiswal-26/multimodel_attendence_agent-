/* ═══════════════════════════════════════════════════
   code_studio.js — AI Code Studio & AI Services
   Code Generation Engine, Code Executor,
   Text-to-Speech Engine, Gemini Visual Aid Generator
   ═══════════════════════════════════════════════════ */

'use strict';

const api = new ApiClient();

async function generateCode() {
  const topic = document.getElementById('codeTopicInput').value.trim();
  const difficulty = document.getElementById('codeDifficultySelect').value;
  const btn = document.getElementById('btnGenerateCode');

  if (!topic) {
    window.notifier.warning('Please enter a topic for code generation.');
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Generating...';

  try {
    const res = await api.post('/api/code/generate', { topic, difficulty });
    if (res && res.success && res.data) {
      const data = res.data;
      if (data.title) {
        document.getElementById('codeSnippetTitle').textContent = data.title;
      }
      if (data.code) {
        document.getElementById('codeEditor').value = data.code;
      }
      window.notifier.success('Educational code generated successfully!');
    } else {
      window.notifier.error('Could not generate code snippet. Using template.');
    }
  } catch (err) {
    console.error(err);
    window.notifier.error('Error generating code: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-magic me-1"></i>Generate';
  }
}

async function executeCode() {
  const code = document.getElementById('codeEditor').value;
  const btn = document.getElementById('btnExecuteCode');
  const consoleEl = document.getElementById('executionConsole');
  const fileBadge = document.getElementById('savedFileBadge');

  if (!code.trim()) {
    window.notifier.warning('Code cannot be empty.');
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Executing in Code Executor...';
  consoleEl.textContent = 'Running in isolated environment...';

  try {
    const res = await api.post('/api/code/execute', { code });
    if (res && res.success) {
      consoleEl.style.color = '#a5f3fc';
      consoleEl.textContent = res.output || '(Execution finished with no standard output)';
      fileBadge.innerHTML = `<i class="fas fa-save me-1 text-success"></i>Saved: <a href="${res.file_path}" target="_blank" class="text-decoration-none">${res.saved_file}</a> (${res.execution_time_sec}s)`;
      window.notifier.success('Script executed successfully!');
    } else {
      consoleEl.style.color = '#f87171';
      consoleEl.textContent = res.output || 'Execution Error occurred.';
      fileBadge.innerHTML = '<span class="text-danger"><i class="fas fa-times me-1"></i>Execution error</span>';
      window.notifier.error('Execution encountered errors.');
    }
  } catch (err) {
    console.error(err);
    consoleEl.textContent = 'Execution request failed: ' + err.message;
    window.notifier.error('Request failed.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-play me-2"></i>Execute in Code Executor';
  }
}

function copyCodeSnippet() {
  const code = document.getElementById('codeEditor').value;
  navigator.clipboard.writeText(code).then(() => {
    window.notifier.success('Code copied to clipboard!');
  }).catch(() => {
    window.notifier.info('Could not copy automatically.');
  });
}

function resetDefaultCode() {
  document.getElementById('codeEditor').value = `# Classroom Attendance & Engagement Simulation
import math
import random

students = ["Alice", "Bob", "Charlie", "Diana", "Evan"]
print("=== Real-time Multimodal Engagement Analysis ===")

total_score = 0.0
for s in students:
    attention = round(random.uniform(0.65, 0.98), 2)
    head_pose = random.choice(["forward", "slight_down", "forward"])
    total_score += attention
    status = "Active 🟢" if attention > 0.75 else "Moderate 🟡"
    print(f"Student: {s:8} | Pose: {head_pose:11} | Score: {attention:.2f} | {status}")

avg_engagement = round(total_score / len(students), 3)
print("-" * 48)
print(f"Overall Classroom Engagement Index: {avg_engagement * 100:.1f}%")
`;
  document.getElementById('codeSnippetTitle').textContent = 'Python Script';
  window.notifier.info('Reset code to default demo.');
}

// ── Text-to-Speech Engine (Audio Layer) ─────────────────────────
function playSpeech() {
  const text = document.getElementById('ttsTextInput').value.trim();
  if (!text) {
    window.notifier.warning('Please enter announcement text to speak.');
    return;
  }

  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
    window.notifier.success('Broadcasting speech via Web Speech API...');
  } else {
    window.notifier.warning('Browser speech synthesis not supported; generating audio file instead.');
    generateAudioFile();
  }
}

async function generateAudioFile() {
  const text = document.getElementById('ttsTextInput').value.trim();
  if (!text) {
    window.notifier.warning('Please enter text.');
    return;
  }

  window.notifier.info('Generating audio file in Storage Layer...');
  try {
    const res = await api.post('/api/audio/tts', { text });
    if (res && res.success && res.url) {
      const container = document.getElementById('ttsAudioPlayerContainer');
      const player = document.getElementById('ttsAudioPlayer');
      player.src = res.url;
      container.style.display = 'block';
      player.play().catch(() => {});
      window.notifier.success(`Audio generated (${res.engine}): ${res.filename}`);
    } else {
      window.notifier.error('Could not generate audio file.');
    }
  } catch (err) {
    window.notifier.error('Audio generation failed: ' + err.message);
  }
}

// ── Gemini Visual Aid Generator ────────────────────────────────
async function generateVisualAid() {
  const concept = document.getElementById('visualConceptInput').value.trim();
  if (!concept) {
    window.notifier.warning('Please enter a concept or topic.');
    return;
  }

  window.notifier.info('Generating visual aid with Gemini...');
  try {
    const res = await api.post('/api/visual/generate', { concept });
    if (res && res.success && res.data) {
      const d = res.data;
      document.getElementById('visualAidTitle').textContent = d.concept || concept;
      document.getElementById('visualAidDesc').textContent = d.visual_description || 'Visual breakdown generated.';
      document.getElementById('visualAidDiagram').textContent = d.mermaid_diagram || '';
      window.notifier.success('Visual aid updated!');
    }
  } catch (err) {
    window.notifier.error('Visual aid generation failed: ' + err.message);
  }
}
