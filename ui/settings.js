/**
 * LocalWhisper Settings Controller
 * Aesthetics: Modern Obsidian & Mint & Apple Human Interface Precision
 */

document.addEventListener('DOMContentLoaded', () => {
  // Navigation & Page Headings
  const navItems = document.querySelectorAll('.sidebar-nav-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');
  const pageEyebrow = document.getElementById('pageEyebrow');
  const pageTitle = document.getElementById('pageTitle');
  const pageSubtitle = document.getElementById('pageSubtitle');
  const revealFinderBtn = document.getElementById('revealFinderBtn');
  const openSysPrefsBtn = document.getElementById('openSysPrefsBtn');

  const pageHeaders = {
    models: {
      eyebrow: 'CORE ARCHITECTURE',
      title: 'AI Models & Storage',
      sub: 'Select which Whisper AI model processes speech on your Mac.'
    },
    flow: {
      eyebrow: 'VOICE PURIFICATION PIPELINE',
      title: 'Dictation Flow',
      sub: 'Customize transcription modes, punctuation parsing, and typing behavior.'
    },
    audio: {
      eyebrow: 'HARDWARE INTEGRATION',
      title: 'Audio & Microphone',
      sub: 'Select input hardware and calibrate silence noise cancellation.'
    },
    hotkeys: {
      eyebrow: 'SYSTEM INTEGRATION',
      title: 'Global Shortcuts',
      sub: 'Configure system-wide hotkeys and push-to-talk behaviors.'
    },
    about: {
      eyebrow: 'SECURITY & SPECIFICATIONS',
      title: 'System & Privacy',
      sub: 'Permissions status, technical specs, and 100% offline guarantee.'
    }
  };

  const isMac = (navigator.userAgent || navigator.platform || '').toUpperCase().indexOf('MAC') >= 0;
  if (!isMac) {
    pageHeaders.models.sub = 'Select which Whisper AI model processes speech on your PC.';
    const kbdGroup = document.querySelector('.lw-kbd-group');
    if (kbdGroup) {
      kbdGroup.innerHTML = '<kbd class="lw-kbd">Ctrl</kbd><kbd class="lw-kbd">Shift</kbd><kbd class="lw-kbd">Space</kbd>';
    }
    const permHeader = document.querySelector('#pane-about .card-headline');
    if (permHeader) {
      permHeader.textContent = 'System Status & Integration';
    }
    const permSubhead = document.querySelector('#pane-about .card-subhead');
    if (permSubhead) {
      permSubhead.textContent = 'LocalWhisper is configured for Windows offline operation.';
    }
    const openPrefs = document.getElementById('openSysPrefsBtn');
    if (openPrefs) {
      openPrefs.textContent = 'Open Windows Settings ↗';
    }
  }

  // Tab Switching
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const tab = item.getAttribute('data-tab');
      navItems.forEach(i => i.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      item.classList.add('active');
      const targetPane = document.getElementById(`pane-${tab}`);
      if (targetPane) targetPane.classList.add('active');

      if (pageHeaders[tab]) {
        if (pageEyebrow) pageEyebrow.textContent = pageHeaders[tab].eyebrow;
        if (pageTitle) pageTitle.textContent = pageHeaders[tab].title;
        if (pageSubtitle) pageSubtitle.textContent = pageHeaders[tab].sub;
      }
    });
  });

  // Reveal in Finder
  if (revealFinderBtn) {
    revealFinderBtn.addEventListener('click', () => {
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.reveal_in_finder();
      }
    });
  }

  // Open System Settings
  if (openSysPrefsBtn) {
    openSysPrefsBtn.addEventListener('click', () => {
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.open_accessibility_settings();
      }
    });
  }

  // Pre-configured models catalog for instant 0ms render
  const DEFAULT_MODELS = [
    {
      id: "tiny.en",
      name: "Whisper Tiny (English)",
      tag: "⚡⚡⚡ Ultra Fast",
      description: "Blazing fast inference (~180ms). Minimal RAM & battery usage. Best for short notes.",
      download_size: "~75 MB",
      actual_size: "~75 MB",
      vram_ram: "~390 MB RAM",
      speed_rating: "5/5",
      accuracy_rating: "3/5",
      is_installed: false,
      is_active: false
    },
    {
      id: "base.en",
      name: "Whisper Base (English)",
      tag: "⚡⚡ Fast • Default",
      description: "Recommended default (~450ms). Perfect balance between ultra-fast speed and high accuracy.",
      download_size: "~142 MB",
      actual_size: "281.8 MB",
      vram_ram: "~500 MB RAM",
      speed_rating: "4/5",
      accuracy_rating: "4/5",
      is_installed: true,
      is_active: true
    },
    {
      id: "small.en",
      name: "Whisper Small (English)",
      tag: "⚡ High Accuracy",
      description: "Superior accuracy for technical terminology, developer terms, and varied accents (~1.1s).",
      download_size: "~480 MB",
      actual_size: "~480 MB",
      vram_ram: "~1.0 GB RAM",
      speed_rating: "3/5",
      accuracy_rating: "4.5/5",
      is_installed: false,
      is_active: false
    },
    {
      id: "medium.en",
      name: "Whisper Medium (English)",
      tag: "🎯 Studio Grade",
      description: "Studio-level accuracy (~2.8s). Handles complex dictation, specialized jargon, and fast speech.",
      download_size: "~1.5 GB",
      actual_size: "~1.5 GB",
      vram_ram: "~2.6 GB RAM",
      speed_rating: "2/5",
      accuracy_rating: "5/5",
      is_installed: false,
      is_active: false
    },
    {
      id: "large-v3-turbo",
      name: "Whisper Large V3 Turbo",
      tag: "🌐 Multilingual Champion",
      description: "State-of-the-art multilingual model with optimized turbo decoding (~1.8s).",
      download_size: "~1.6 GB",
      actual_size: "~1.6 GB",
      vram_ram: "~2.8 GB RAM",
      speed_rating: "3/5",
      accuracy_rating: "5/5",
      is_installed: false,
      is_active: false
    }
  ];

  // 1. Render Models Grid
  function renderModelsGrid(models) {
    const grid = document.getElementById('modelsGrid');
    if (!grid) return;
    grid.innerHTML = '';

    models.forEach(m => {
      const card = document.createElement('div');
      card.className = `model-card-item ${m.is_active ? 'active' : ''}`;

      // Start Icon: Checkmark for active/selected model, clean radio for unselected
      let startIconHtml = '';
      if (m.is_active) {
        startIconHtml = `
          <div class="squircle-icon bg-mint active-check-icon" title="Selected Active Model">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.8">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
        `;
      } else {
        startIconHtml = `
          <div class="squircle-icon bg-surface unselected-model-icon" title="${m.is_installed ? 'Click to select' : 'Download to use'}">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="8"/>
            </svg>
          </div>
        `;
      }

      // Action Right: Active indicator, Select button, or Download icon with size pill
      let actionHtml = '';
      if (m.is_active) {
        actionHtml = `
          <span class="pill-tag tag-mint pill-active-indicator">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.8"><polyline points="20 6 9 17 4 12"/></svg>
            Active Model
          </span>
        `;
      } else if (m.is_installed) {
        actionHtml = `<button class="pill-btn-secondary micro" data-switch="${m.id}">Select</button>`;
      } else {
        actionHtml = `
          <div class="model-download-action-group">
            <span class="model-action-size font-mono">${m.download_size}</span>
            <button class="pill-btn-download-icon" data-switch="${m.id}" title="Download and use ${m.name} (${m.download_size})">
              <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.3">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </button>
          </div>
        `;
      }

      // Model size in specs
      const sizeTag = m.is_installed ? m.actual_size : m.download_size;

      card.innerHTML = `
        <div class="model-item-main">
          ${startIconHtml}
          <div class="model-item-text">
            <div class="model-item-header">
              <span class="model-name">${m.name}</span>
              <span class="pill-tag ${m.is_active ? 'tag-mint' : 'tag-neutral'} micro">${m.tag}</span>
            </div>
            <p class="model-desc">${m.description}</p>
            <div class="model-specs-row">
              <span class="pill-tag tag-cyan micro font-mono">⚡ ${m.speed_rating} speed</span>
              <span class="pill-tag tag-mint micro font-mono">🎯 ${m.accuracy_rating} accuracy</span>
              <span class="pill-tag tag-neutral micro font-mono">💾 ${sizeTag}</span>
              <span class="pill-tag tag-neutral micro font-mono">🧠 ${m.vram_ram}</span>
            </div>
          </div>
        </div>
        <div class="model-item-action">
          ${actionHtml}
        </div>
      `;

      // Allow clicking installed row to select
      if (!m.is_active && m.is_installed) {
        card.style.cursor = 'pointer';
        card.addEventListener('click', (e) => {
          if (e.target.closest('button')) return;
          const selectBtn = card.querySelector('[data-switch]');
          if (selectBtn) selectBtn.click();
        });
      }

      grid.appendChild(card);
    });

    // Wire Switch / Download Buttons
    grid.querySelectorAll('[data-switch]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const modelId = btn.getAttribute('data-switch');
        btn.innerHTML = `
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" class="spin"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>
        `;
        btn.style.opacity = '0.7';
        btn.style.pointerEvents = 'none';

        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.switch_model(modelId).then(() => {
            loadModelsInfo();
          }).catch(err => {
            console.error("Failed to switch model:", err);
            loadModelsInfo();
          });
        }
      });
    });
  }

  // Pre-render immediately so the UI is NEVER empty
  renderModelsGrid(DEFAULT_MODELS);

  // 2. Fetch Models Info from Python Backend
  function loadModelsInfo() {
    if (!window.pywebview || !window.pywebview.api) return;

    window.pywebview.api.get_models_info().then(data => {
      if (!data) return;

      const totalDiskEl = document.getElementById('totalDiskSize');
      const miniStorageEl = document.getElementById('miniStorageVal');
      const modelCountSub = document.getElementById('modelCountSub');
      const installedBadge = document.getElementById('installedBadge');
      const modelsPathCode = document.getElementById('modelsPathCode');
      const activeModelEl = document.getElementById('activeModelName');
      const miniStorageFill = document.getElementById('miniStorageFill');

      if (totalDiskEl) totalDiskEl.textContent = data.total_size;
      if (miniStorageEl) miniStorageEl.textContent = data.total_size;
      if (modelCountSub) modelCountSub.textContent = `${data.installed_count} of ${data.models.length} Models`;
      if (installedBadge) installedBadge.textContent = data.installed_count;
      if (modelsPathCode) modelsPathCode.textContent = data.models_dir;

      if (miniStorageFill && data.models.length > 0) {
        const pct = Math.round((data.installed_count / data.models.length) * 100);
        miniStorageFill.style.width = `${Math.max(16, pct)}%`;
      }

      const activeModel = data.models.find(m => m.is_active);
      if (activeModel && activeModelEl) {
        activeModelEl.textContent = activeModel.name;
      }

      renderModelsGrid(data.models);
    }).catch(err => console.error("Error loading models:", err));
  }

  // 3. Static Event Listeners Binding (registered once)
  function bindSettingsControls() {
    // Dictation Flow Mode Selection
    document.querySelectorAll('[data-flow]').forEach(card => {
      card.addEventListener('click', () => {
        const mode = card.getAttribute('data-flow');
        document.querySelectorAll('[data-flow]').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.save_setting('active_mode', mode);
        }
      });
    });

    // Formatting Toggles
    const toggleHandsFree = document.getElementById('toggleHandsFree');
    const toggleAutoPaste = document.getElementById('toggleAutoPaste');
    const toggleRemoveFillers = document.getElementById('toggleRemoveFillers');
    const togglePunctuation = document.getElementById('togglePunctuation');
    const toggleCapitalize = document.getElementById('toggleCapitalize');

    if (toggleHandsFree) {
      toggleHandsFree.addEventListener('change', () => {
        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.save_setting('hands_free_mode', toggleHandsFree.checked);
        }
      });
    }

    if (toggleAutoPaste) {
      toggleAutoPaste.addEventListener('change', () => {
        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.save_setting('auto_paste', toggleAutoPaste.checked);
        }
      });
    }

    if (toggleRemoveFillers) {
      toggleRemoveFillers.addEventListener('change', () => {
        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.save_setting('remove_fillers', toggleRemoveFillers.checked);
        }
      });
    }

    if (togglePunctuation) {
      togglePunctuation.addEventListener('change', () => {
        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.save_setting('format_punctuation', togglePunctuation.checked);
        }
      });
    }

    if (toggleCapitalize) {
      toggleCapitalize.addEventListener('change', () => {
        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.save_setting('auto_capitalize', toggleCapitalize.checked);
        }
      });
    }

    // Hotkey Mode Segmented Control
    document.querySelectorAll('[data-hk-mode]').forEach(btn => {
      btn.addEventListener('click', () => {
        const mode = btn.getAttribute('data-hk-mode');
        document.querySelectorAll('[data-hk-mode]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.save_setting('hotkey_mode', mode);
        }
      });
    });

    // Silence Slider
    const silenceSlider = document.getElementById('silenceSlider');
    const silenceVal = document.getElementById('silenceVal');
    if (silenceSlider && silenceVal) {
      silenceSlider.addEventListener('input', () => {
        silenceVal.textContent = parseFloat(silenceSlider.value).toFixed(4);
      });
      silenceSlider.addEventListener('change', () => {
        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.save_setting('silence_threshold', parseFloat(silenceSlider.value));
        }
      });
    }

    // Audio Device Select
    const deviceSelect = document.getElementById('deviceSelect');
    if (deviceSelect) {
      deviceSelect.addEventListener('change', () => {
        const devId = deviceSelect.value === "" ? null : parseInt(deviceSelect.value, 10);
        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.save_setting('microphone_device_id', devId);
        }
      });
    }

    // Test Mic Button
    const testMicBtn = document.getElementById('testMicBtn');
    const vuMeterFill = document.getElementById('vuMeterFill');
    const vuMeterVal = document.getElementById('vuMeterVal');

    if (testMicBtn) {
      testMicBtn.addEventListener('click', () => {
        testMicBtn.innerHTML = `
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" class="spin"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>
          <span>Listening (2s)...</span>
        `;
        testMicBtn.style.pointerEvents = 'none';

        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.test_microphone().then(level => {
            const pct = Math.min(100, Math.round(level * 400));
            if (vuMeterFill) vuMeterFill.style.width = `${pct}%`;
            if (vuMeterVal) vuMeterVal.textContent = `${level.toFixed(4)} RMS`;
            testMicBtn.innerHTML = `
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              <span>Test Mic (2s)</span>
            `;
            testMicBtn.style.pointerEvents = 'auto';

            setTimeout(() => {
              if (vuMeterFill) vuMeterFill.style.width = '0%';
            }, 2500);
          }).catch(() => {
            testMicBtn.innerHTML = `
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              <span>Test Mic (2s)</span>
            `;
            testMicBtn.style.pointerEvents = 'auto';
          });
        }
      });
    }
  }

  // 4. Preferences & Settings Values Sync
  function loadPreferences() {
    if (!window.pywebview || !window.pywebview.api) return;

    window.pywebview.api.get_settings().then(settings => {
      if (!settings) return;

      // Mode Selection
      document.querySelectorAll('[data-flow]').forEach(card => {
        const mode = card.getAttribute('data-flow');
        card.classList.toggle('active', mode === settings.active_mode);
      });

      // Toggles
      const toggleHandsFree = document.getElementById('toggleHandsFree');
      const toggleAutoPaste = document.getElementById('toggleAutoPaste');
      const toggleRemoveFillers = document.getElementById('toggleRemoveFillers');
      const togglePunctuation = document.getElementById('togglePunctuation');
      const toggleCapitalize = document.getElementById('toggleCapitalize');

      if (toggleHandsFree) toggleHandsFree.checked = Boolean(settings.hands_free_mode);
      if (toggleAutoPaste) toggleAutoPaste.checked = settings.auto_paste !== false;
      if (toggleRemoveFillers) toggleRemoveFillers.checked = settings.remove_fillers !== false;
      if (togglePunctuation) togglePunctuation.checked = settings.format_punctuation !== false;
      if (toggleCapitalize) toggleCapitalize.checked = settings.auto_capitalize !== false;

      // Hotkey Mode Segmented Pill
      document.querySelectorAll('[data-hk-mode]').forEach(btn => {
        const mode = btn.getAttribute('data-hk-mode');
        btn.classList.toggle('active', mode === settings.hotkey_mode);
      });

      // Silence Slider
      const silenceSlider = document.getElementById('silenceSlider');
      const silenceVal = document.getElementById('silenceVal');
      if (silenceSlider && silenceVal) {
        silenceSlider.value = settings.silence_threshold || 0.0028;
        silenceVal.textContent = parseFloat(silenceSlider.value).toFixed(4);
      }
    }).catch(err => console.error("Error loading settings:", err));
  }

  // 5. Audio Devices
  function loadAudioDevices() {
    if (!window.pywebview || !window.pywebview.api) return;

    window.pywebview.api.get_audio_devices().then(devices => {
      const select = document.getElementById('deviceSelect');
      if (!select) return;
      select.innerHTML = '';

      if (!devices || devices.length === 0) {
        select.innerHTML = '<option value="">System Default Microphone</option>';
        return;
      }

      devices.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.id;
        opt.textContent = `${d.name} (${d.channels} ch, ${d.default_samplerate}Hz)${d.is_recommended ? ' • Recommended' : ''}`;
        if (d.is_selected) opt.selected = true;
        select.appendChild(opt);
      });
    }).catch(err => console.error("Error loading audio devices:", err));
  }

  // 6. Permissions
  function loadPermissions() {
    if (!window.pywebview || !window.pywebview.api) return;

    window.pywebview.api.get_permissions().then(perms => {
      if (!perms) return;

      const micBadge = document.getElementById('micStatusBadge');
      const axBadge = document.getElementById('axStatusBadge');
      const permDot = document.getElementById('permDot');

      if (micBadge) {
        micBadge.className = `pill-tag ${perms.microphone_granted ? 'tag-mint' : 'tag-coral'} micro`;
        micBadge.textContent = perms.microphone_granted ? 'Authorized ✓' : 'Denied ⚠️';
      }

      if (axBadge) {
        axBadge.className = `pill-tag ${perms.accessibility_granted ? 'tag-mint' : 'tag-coral'} micro`;
        axBadge.textContent = perms.accessibility_granted ? 'Trusted ✓' : 'Needs Access ⚠️';
      }

      if (permDot) {
        permDot.className = `status-pulse-dot ${perms.microphone_granted && perms.accessibility_granted ? '' : 'restricted'}`;
      }
    }).catch(err => console.error("Error loading permissions:", err));
  }

  // Master Sync
  function loadAllData() {
    loadModelsInfo();
    loadPreferences();
    loadAudioDevices();
    loadPermissions();
  }

  // Bind UI control click/change events once
  bindSettingsControls();

  // Multi-strategy pywebview connection (immediate check + pywebviewready event + 50ms polling loop)
  let connected = false;
  function connectBackend() {
    if (connected) return;
    if (window.pywebview && window.pywebview.api) {
      connected = true;
      loadAllData();
    }
  }

  connectBackend();
  window.addEventListener('pywebviewready', connectBackend);
  window.addEventListener('focus', loadAllData);

  const pollInterval = setInterval(() => {
    if (window.pywebview && window.pywebview.api) {
      connectBackend();
      clearInterval(pollInterval);
    }
  }, 50);
  setTimeout(() => clearInterval(pollInterval), 4000);
});
