import threading
import time
from typing import Callable, Optional
from pynput import keyboard
import config

def is_right_option(key) -> bool:
    """Matches Right Option (macOS) / Right Alt / AltGr (Windows/Linux)."""
    if key == keyboard.Key.alt_r:
        return True
    name = getattr(key, 'name', '')
    if name in ('alt_r', 'alt_gr'):
        return True
    return False

def is_cmd(key) -> bool:
    return key in (keyboard.Key.cmd, getattr(keyboard.Key, 'cmd_l', None), getattr(keyboard.Key, 'cmd_r', None))

def is_ctrl(key) -> bool:
    return key in (keyboard.Key.ctrl, getattr(keyboard.Key, 'ctrl_l', None), getattr(keyboard.Key, 'ctrl_r', None))

def is_shift(key) -> bool:
    return key in (keyboard.Key.shift, getattr(keyboard.Key, 'shift_l', None), getattr(keyboard.Key, 'shift_r', None))

class HotkeyManager:
    """
    Cross-platform Global Hotkey Listener.
    Primary shortcut: Right Option / Right Alt key.
    Supports both Toggle Mode (tap to start/stop) and Push-to-Talk (hold to speak).
    Also supports Cmd+Shift+Space / Ctrl+Shift+Space as a secondary combination.
    """

    def __init__(
        self,
        on_toggle: Optional[Callable[[], None]] = None,
        on_press_down: Optional[Callable[[], None]] = None,
        on_release: Optional[Callable[[], None]] = None,
        mode: str = config.HOTKEY_MODE
    ):
        self.on_toggle = on_toggle
        self.on_press_down = on_press_down
        self.on_release = on_release
        self.mode = mode  # "toggle" or "push_to_talk"
        self._listener: Optional[keyboard.Listener] = None
        self._alt_r_down = False
        self._combo_down = False
        self._currently_pressed = set()
        self._lock = threading.Lock()
        self._last_toggle_time = 0.0

    def _trigger_toggle(self):
        now = time.time()
        # Debounce to prevent accidental double toggles
        if now - self._last_toggle_time < 0.28:
            return
        self._last_toggle_time = now
        if self.on_toggle:
            self.on_toggle()

    def _trigger_press_down(self):
        with self._lock:
            if self.on_press_down:
                self.on_press_down()

    def _trigger_release(self):
        with self._lock:
            if self.on_release:
                self.on_release()

    def _on_press(self, key):
        self._currently_pressed.add(key)

        # 1. Primary: Right Option / Right Alt single key
        if is_right_option(key):
            if not self._alt_r_down:
                self._alt_r_down = True
                if self.mode == "toggle":
                    self._trigger_toggle()
                elif self.mode == "push_to_talk":
                    self._trigger_press_down()
            return

        # 2. Secondary fallback combo: Cmd+Shift+Space (macOS) or Ctrl+Shift+Space (Windows)
        has_mod = any(is_cmd(k) for k in self._currently_pressed) if config.IS_MACOS else any(is_ctrl(k) for k in self._currently_pressed)
        has_shift = any(is_shift(k) for k in self._currently_pressed)
        if key == keyboard.Key.space and has_mod and has_shift:
            if not self._combo_down:
                self._combo_down = True
                if self.mode == "toggle":
                    self._trigger_toggle()
                elif self.mode == "push_to_talk":
                    self._trigger_press_down()

    def _on_release(self, key):
        if key in self._currently_pressed:
            self._currently_pressed.discard(key)

        if is_right_option(key):
            if self._alt_r_down:
                self._alt_r_down = False
                if self.mode == "push_to_talk":
                    self._trigger_release()

        if key == keyboard.Key.space or not (any(is_cmd(k) or is_ctrl(k) for k in self._currently_pressed) and any(is_shift(k) for k in self._currently_pressed)):
            if self._combo_down:
                self._combo_down = False
                if self.mode == "push_to_talk":
                    self._trigger_release()

    def start(self):
        """Starts listening for global hotkeys."""
        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self._listener.daemon = True
            self._listener.start()
            print(f"[HotkeyManager] Global shortcut active: {config.DEFAULT_HOTKEY_DISPLAY} (Right Option)", flush=True)
        except Exception as e:
            print(f"[HotkeyManager] Could not register global hotkey: {e}", flush=True)

    def stop(self):
        """Stops the hotkey listener."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
