# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

datas = [
    ('ui', 'ui'),
    ('assets', 'assets'),
    ('settings.example.json', '.'),
]

if os.path.exists('AppIcon.icns'):
    datas.append(('AppIcon.icns', '.'))

binaries = []
hiddenimports = [
    'engine',
    'engine.audio_recorder',
    'engine.transcriber',
    'engine.injector',
    'engine.hotkey_manager',
    'engine.settings_manager',
    'engine.llama_formatter',
    'engine.hands_free',
    'engine.live_streamer',
    'engine.permissions',
    'faster_whisper',
    'ctranslate2',
    'sounddevice',
    'soundfile',
    'pyperclip',
    'pynput',
    'pynput.keyboard',
]

if sys.platform == 'darwin':
    hiddenimports += [
        'pynput.keyboard._darwin',
        'webview.platforms.cocoa',
        'AppKit',
        'Foundation',
        'AVFoundation',
        'ApplicationServices',
        'Quartz',
    ]
elif sys.platform == 'win32':
    hiddenimports += [
        'pynput.keyboard._win32',
        'webview.platforms.winforms',
        'pythonnet',
        'clr',
    ]

for pkg in ['ctranslate2', 'faster_whisper', 'sounddevice', 'soundfile', 'pywebview']:
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception as e:
        print(f"Notice: collect_all for {pkg}: {e}")

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LocalWhisper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file='entitlements.plist' if os.path.exists('entitlements.plist') else None,
    icon='AppIcon.icns' if os.path.exists('AppIcon.icns') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LocalWhisper',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='LocalWhisper.app',
        icon='AppIcon.icns' if os.path.exists('AppIcon.icns') else None,
        bundle_identifier='com.antigravity.localwhisper',
        info_plist={
            'CFBundleName': 'LocalWhisper',
            'CFBundleDisplayName': 'LocalWhisper',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'LSMinimumSystemVersion': '11.0',
            'NSHighResolutionCapable': True,
            'NSMicrophoneUsageDescription': 'LocalWhisper needs access to your microphone to transcribe speech locally.',
            'NSSpeechRecognitionUsageDescription': 'LocalWhisper transcribes speech locally using offline Whisper AI.',
            'NSAccessibilityUsageDescription': 'LocalWhisper uses accessibility features to type transcribed text directly into your active window.',
            'Privacy - Accessibility Usage Description': 'LocalWhisper uses accessibility features to type transcribed text directly into your active window.',
            'LSUIElement': False,
        }
    )

