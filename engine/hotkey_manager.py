import threading
from typing import Callable, Optional
from pynput import keyboard
import config

class HotkeyManager:
    """
    Cross-platform Global Hotkey Listener.
    Supports both Toggle Mode (tap to start/stop) and Push-to-Talk (hold to speak).
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
        self._listener: Optional[keyboard.GlobalHotKeys] = None
        self._is_down = False
        self._lock = threading.Lock()

    def _handle_hotkey_trigger(self):
        """Invoked when the hotkey combination is activated."""
        if self.mode == "toggle":
            if self.on_toggle:
                self.on_toggle()
        elif self.mode == "push_to_talk":
            with self._lock:
                if not self._is_down:
                    self._is_down = True
                    if self.on_press_down:
                        self.on_press_down()

    def start(self):
        """Starts listening for global hotkeys."""
        # Define hotkeys across platforms
        if config.IS_MACOS:
            hotkey_patterns = {
                '<cmd>+<shift>+<space>': self._handle_hotkey_trigger,
                '<ctrl>+<alt>+<space>': self._handle_hotkey_trigger,
            }
        else:
            hotkey_patterns = {
                '<ctrl>+<shift>+<space>': self._handle_hotkey_trigger,
                '<alt>+<space>': self._handle_hotkey_trigger,
            }

        try:
            self._listener = keyboard.GlobalHotKeys(hotkey_patterns)
            self._listener.start()
            print(f"[HotkeyManager] Global hotkey active: {config.DEFAULT_HOTKEY_DISPLAY}")
        except Exception as e:
            print(f"[HotkeyManager] Could not register global hotkey: {e}")

    def stop(self):
        """Stops the hotkey listener."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
