/**
 * LocalWhisper Minimal Floating Pill Controller
 * Matches user's exact Static & Active state design
 */

document.addEventListener('DOMContentLoaded', () => {
  const pill = document.getElementById('pill');
  const settingsBtn = document.getElementById('settingsBtn');
  const contextMenu = document.getElementById('contextMenu');
  const menuSettings = document.getElementById('menuSettings');
  const menuQuit = document.getElementById('menuQuit');
  const spectrumBars = document.querySelectorAll('.spectrum-bar');

  let currentState = 'idle';
  let isMenuOpen = false;
  let lastToggleTime = 0;

  function triggerRecordingToggle() {
    const now = Date.now();
    if (now - lastToggleTime < 280) {
      return;
    }
    lastToggleTime = now;
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.toggle_recording();
    } else {
      window.addEventListener('pywebviewready', () => {
        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.toggle_recording();
        }
      }, { once: true });
    }
  }

  const shortcutHint = document.getElementById('shortcutHint');
  const hintKeys = document.getElementById('hintKeys');

  const isMac = (navigator.userAgent || navigator.platform || '').toUpperCase().indexOf('MAC') >= 0;
  const hkDisplay = isMac ? '⌘⇧Space' : 'Ctrl+Shift+Space';
  const defaultKeys = isMac ? ['⌘', '⇧', 'Space'] : ['Ctrl', 'Shift', 'Space'];

  function renderKeys(keys) {
    return keys.map(k => `<kbd class="hint-kbd">${k}</kbd>`).join('');
  }

  if (hintKeys) {
    hintKeys.innerHTML = renderKeys(defaultKeys);
  }
  pill.title = `Click to Record (${hkDisplay})`;

  // 1. State Handler called from Python
  window.updateState = function(state, details = '') {
    currentState = state;

    if (state === 'listening' || state === 'recording') {
      pill.className = 'minimal-pill active';
      pill.title = `Click to Stop Recording (${hkDisplay})`;
      if (shortcutHint) {
        shortcutHint.className = 'shortcut-hint active';
      }
    } else {
      pill.className = 'minimal-pill idle';
      pill.title = `Click to Record (${hkDisplay})`;
      if (shortcutHint) {
        shortcutHint.className = 'shortcut-hint';
      }
      // Reset spectrum bar inline transforms when idle
      spectrumBars.forEach(b => {
        b.style.transform = '';
      });
    }
  };

  // 2. Real-Time Audio Reactivity called from Python
  window.updateAudioLevel = function(level) {
    if (currentState === 'listening' || currentState === 'recording') {
      const boost = 0.45 + Math.min(1.2, level * 2.8) * 1.3;
      spectrumBars.forEach((bar, idx) => {
        const factor = boost * (0.85 + 0.35 * Math.sin(idx * 0.65));
        bar.style.transform = `scaleY(${factor.toFixed(2)})`;
      });
    }
  };

  // Transcript callback compatibility (silent in minimal UI)
  window.setTranscript = function(text, latencyMs = 0) {
    // Keystrokes are injected directly at cursor by backend
  };

  // 3. Click anywhere on Pill to Toggle Recording
  pill.addEventListener('click', (e) => {
    if (e.target.closest('#settingsBtn') || e.target.closest('#contextMenu') || e.target.closest('.drag-grip')) {
      return;
    }
    triggerRecordingToggle();
  });

  // 4. Circular Settings Button
  if (settingsBtn) {
    settingsBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.open_settings();
      }
    });
  }

  // 5. Right Click Mini Context Menu
  pill.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    e.stopPropagation();
    isMenuOpen = !isMenuOpen;
    contextMenu.classList.toggle('open', isMenuOpen);
  });

  document.addEventListener('click', (e) => {
    if (isMenuOpen && !e.target.closest('#contextMenu')) {
      isMenuOpen = false;
      contextMenu.classList.remove('open');
    }
  });

  if (menuSettings) {
    menuSettings.addEventListener('click', (e) => {
      e.stopPropagation();
      isMenuOpen = false;
      contextMenu.classList.remove('open');
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.open_settings();
      }
    });
  }

  if (menuQuit) {
    menuQuit.addEventListener('click', (e) => {
      e.stopPropagation();
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.quit();
      }
    });
  }
});
