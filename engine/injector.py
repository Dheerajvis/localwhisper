import sys
import time
import threading
import pyperclip
import config

class TextInjector:
    """
    Injects transcribed text directly at the cursor position in the active text box.
    Uses native Cocoa NSPasteboard and Quartz CGEventPostToPid / CGEventPost.
    Completely avoids AppleScript and System Events to eliminate Error 1002 and automation popups.
    """

    def __init__(self):
        self.last_target_app = None
        self.last_target_app_name = None
        self.last_target_hwnd = None
        self._last_typed_time = 0.0
        self._last_typed_text = ""
        self._start_app_tracker()

    def reset(self):
        """Resets typing tracking for a new recording session."""
        self._last_typed_time = 0.0
        self._last_typed_text = ""

    def _start_app_tracker(self):
        """Continuously monitors frontmost application in background every 50ms."""
        if config.IS_MACOS:
            def track_mac():
                from AppKit import NSWorkspace
                ws = NSWorkspace.sharedWorkspace()
                while True:
                    try:
                        app = ws.frontmostApplication()
                        if app:
                            bundle = (app.bundleIdentifier() or "").lower()
                            name = (app.localizedName() or "").lower()
                            if "localwhisper" not in bundle and "python" not in bundle and "localwhisper" not in name:
                                self.last_target_app = app
                                self.last_target_app_name = app.localizedName()
                    except Exception:
                        pass
                    time.sleep(0.05)

            tracker_thread = threading.Thread(target=track_mac, daemon=True)
            tracker_thread.start()

        elif config.IS_WINDOWS:
            def track_win():
                import ctypes
                user32 = ctypes.windll.user32
                my_pid = os.getpid()
                while True:
                    try:
                        hwnd = user32.GetForegroundWindow()
                        if hwnd:
                            pid = ctypes.c_ulong()
                            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                            if pid.value != my_pid:
                                self.last_target_hwnd = hwnd
                    except Exception:
                        pass
                    time.sleep(0.05)

            tracker_thread = threading.Thread(target=track_win, daemon=True)
            tracker_thread.start()

    def capture_target_app(self):
        """Explicitly capture current active application."""
        if config.IS_MACOS:
            try:
                from AppKit import NSWorkspace
                app = NSWorkspace.sharedWorkspace().frontmostApplication()
                if app:
                    bundle = (app.bundleIdentifier() or "").lower()
                    name = (app.localizedName() or "").lower()
                    if "localwhisper" not in bundle and "python" not in bundle and "localwhisper" not in name:
                        self.last_target_app = app
                        self.last_target_app_name = app.localizedName()
            except Exception:
                pass
        elif config.IS_WINDOWS:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()
                if hwnd:
                    pid = ctypes.c_ulong()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value != os.getpid():
                        self.last_target_hwnd = hwnd
            except Exception:
                pass

    @staticmethod
    def is_accessibility_trusted() -> bool:
        """Checks if process has Accessibility permissions."""
        if not config.IS_MACOS:
            return True
        try:
            from ApplicationServices import AXIsProcessTrusted
            return bool(AXIsProcessTrusted())
        except Exception:
            return False

    @staticmethod
    def prompt_accessibility_if_needed():
        """Triggers macOS system prompt for Accessibility once if not trusted."""
        if config.IS_MACOS:
            try:
                from ApplicationServices import (
                    AXIsProcessTrusted,
                    AXIsProcessTrustedWithOptions,
                    kAXTrustedCheckOptionPrompt
                )
                if not AXIsProcessTrusted():
                    AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
            except Exception:
                pass

    @staticmethod
    def open_accessibility_settings():
        """Opens macOS System Settings directly to Privacy & Security -> Accessibility, or Windows Settings."""
        if config.IS_MACOS:
            import subprocess
            try:
                subprocess.run([
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
                ])
            except Exception as e:
                print(f"[TextInjector] Could not open System Settings: {e}", flush=True)
        elif config.IS_WINDOWS:
            import os
            try:
                os.system("start ms-settings:privacy-microphone")
            except Exception as e:
                print(f"[TextInjector] Could not open Windows Settings: {e}", flush=True)

    def inject_text(self, text: str, auto_paste: bool = config.AUTO_PASTE_ENABLED) -> tuple:
        """
        Copies text to clipboard and pastes it into the active target window.
        Returns: (success: bool, status_reason: str)
        """
        if not text or not text.strip():
            return False, "empty_text"

        cleaned_text = text.strip()
        print(f"[TextInjector] Putting text on clipboard: \"{cleaned_text}\"", flush=True)

        # 1. Put transcribed text into system clipboard using Cocoa NSPasteboard + pyperclip
        copied = False
        if config.IS_MACOS:
            try:
                from AppKit import NSPasteboard, NSPasteboardTypeString
                pb = NSPasteboard.generalPasteboard()
                pb.clearContents()
                pb.setString_forType_(cleaned_text, NSPasteboardTypeString)
                copied = True
            except Exception:
                pass

        if not copied:
            try:
                pyperclip.copy(cleaned_text)
                copied = True
            except Exception as e:
                print(f"[TextInjector] Clipboard error: {e}", flush=True)
                return False, "clipboard_error"

        if not auto_paste:
            return True, "copied_only"

        # 2. Focus target application and trigger paste
        if config.IS_MACOS:
            return self._paste_macos()
        else:
            return self._paste_windows()

    def _paste_macos(self) -> tuple:
        """Refocuses active application and executes native Quartz Cmd+V without System Events."""
        from AppKit import NSWorkspace
        ws = NSWorkspace.sharedWorkspace()

        target_app = self.last_target_app
        target_name = self.last_target_app_name or (target_app.localizedName() if target_app else None)

        if not target_app:
            front = ws.frontmostApplication()
            if front:
                bundle = (front.bundleIdentifier() or "").lower()
                name = (front.localizedName() or "").lower()
                if "localwhisper" not in bundle and "python" not in bundle and "localwhisper" not in name:
                    target_app = front
                    target_name = front.localizedName()

        print(f"[TextInjector] Refocusing target app: '{target_name}'...", flush=True)

        # 1. Cocoa-level App Activation
        if target_app is not None:
            try:
                # 3 = NSApplicationActivateAllWindows | NSApplicationActivateIgnoringOtherApps
                target_app.activateWithOptions_(3)
                target_pid = target_app.processIdentifier()
                t0 = time.time()
                while time.time() - t0 < 0.25:
                    curr = ws.frontmostApplication()
                    if curr and curr.processIdentifier() == target_pid:
                        break
                    time.sleep(0.01)
            except Exception as e:
                print(f"[TextInjector] Activation warning: {e}", flush=True)
        else:
            time.sleep(0.05)

        # 2. Check if Accessibility is trusted
        trusted = self.is_accessibility_trusted()
        if not trusted:
            print("[TextInjector] Accessibility is NOT enabled in System Settings. Keystroke simulation blocked by macOS.", flush=True)
            self.prompt_accessibility_if_needed()
            return False, "needs_accessibility"

        # 3. Native Quartz CGEvent keystroke injection (ANSI Keycode 9 = 'v')
        try:
            from Quartz import (
                CGEventCreateKeyboardEvent,
                CGEventSetFlags,
                CGEventPost,
                CGEventPostToPid,
                kCGHIDEventTap,
                kCGEventFlagMaskCommand
            )

            time.sleep(0.04)

            # Create Cmd+V keydown and keyup events
            v_down = CGEventCreateKeyboardEvent(None, 9, True)
            CGEventSetFlags(v_down, kCGEventFlagMaskCommand)
            v_up = CGEventCreateKeyboardEvent(None, 9, False)
            CGEventSetFlags(v_up, kCGEventFlagMaskCommand)

            # Single paste execution: Post to target PID or fallback to HID tap (NEVER BOTH)
            pasted_via_pid = False
            if target_app:
                try:
                    pid = target_app.processIdentifier()
                    CGEventPostToPid(pid, v_down)
                    time.sleep(0.02)
                    CGEventPostToPid(pid, v_up)
                    pasted_via_pid = True
                except Exception as e:
                    print(f"[TextInjector] PostToPid notice: {e}", flush=True)

            if not pasted_via_pid:
                CGEventPost(kCGHIDEventTap, v_down)
                time.sleep(0.02)
                CGEventPost(kCGHIDEventTap, v_up)

            print(f"[TextInjector] Successfully injected single Cmd+V into '{target_name}'.", flush=True)
            return True, "success"
        except Exception as e:
            print(f"[TextInjector] Quartz CGEvent error: {e}", flush=True)
            return False, "event_error"

    def _paste_windows(self) -> tuple:
        """Simulates Ctrl+V on Windows into the active target application."""
        try:
            if self.last_target_hwnd:
                import ctypes
                try:
                    ctypes.windll.user32.SetForegroundWindow(self.last_target_hwnd)
                    time.sleep(0.04)
                except Exception:
                    pass

            from pynput.keyboard import Controller, Key
            kb = Controller()
            with kb.pressed(Key.ctrl):
                kb.press('v')
                kb.release('v')
            print(f"[TextInjector] Windows Ctrl+V simulated.", flush=True)
            return True, "success"
        except Exception as e:
            print(f"[TextInjector] Windows paste error: {e}", flush=True)
            return False, "windows_error"

    def type_text_at_cursor(self, text: str) -> tuple:
        """
        Directly types text at the active cursor position using native Quartz Unicode events.
        Does NOT touch or overwrite the system clipboard.
        """
        if not text or not text.strip():
            return False, "empty_text"

        cleaned_text = text.strip()

        # If previous typing occurred recently and didn't end with space/newline,
        # and current text doesn't start with space/punctuation, prepend a space.
        now = time.time()
        punctuation_starters = {'.', ',', '!', '?', ';', ':', ')', ']', '}', '-'}
        if (
            self._last_typed_time > 0
            and (now - self._last_typed_time) < 10.0
            and self._last_typed_text
            and not self._last_typed_text.endswith((' ', '\n', '\t'))
            and cleaned_text[0] not in punctuation_starters
        ):
            cleaned_text = " " + cleaned_text

        trusted = self.is_accessibility_trusted()
        if not trusted:
            print("[TextInjector] Accessibility is NOT enabled. Keystroke simulation blocked.", flush=True)
            self.prompt_accessibility_if_needed()
            return False, "needs_accessibility"

        if config.IS_MACOS:
            success, reason = self._type_unicode_macos(cleaned_text)
        else:
            success, reason = self._type_windows(cleaned_text)

        if success:
            self._last_typed_time = time.time()
            self._last_typed_text = cleaned_text

        return success, reason

    def _type_unicode_macos(self, text: str) -> tuple:
        """Types unicode string directly into active cursor via Quartz CGEventKeyboardSetUnicodeString."""
        try:
            # Ensure target application has focus if localwhisper or python was clicked
            if self.last_target_app is not None:
                try:
                    from AppKit import NSWorkspace
                    ws = NSWorkspace.sharedWorkspace()
                    front = ws.frontmostApplication()
                    if front is not None and front.processIdentifier() != self.last_target_app.processIdentifier():
                        bundle = (front.bundleIdentifier() or "").lower()
                        name = (front.localizedName() or "").lower()
                        if "localwhisper" in bundle or "python" in bundle or "localwhisper" in name:
                            self.last_target_app.activateWithOptions_(3)
                            time.sleep(0.015)
                except Exception:
                    pass

            from Quartz import (
                CGEventCreateKeyboardEvent,
                CGEventKeyboardSetUnicodeString,
                CGEventPost,
                kCGHIDEventTap
            )

            # Split into chunks of max 20 UTF-16 code units for Quartz buffer safety
            chunk_size = 20
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i + chunk_size]
                down = CGEventCreateKeyboardEvent(None, 0, True)
                CGEventKeyboardSetUnicodeString(down, len(chunk), chunk)
                CGEventPost(kCGHIDEventTap, down)
                time.sleep(0.002)

                up = CGEventCreateKeyboardEvent(None, 0, False)
                CGEventKeyboardSetUnicodeString(up, len(chunk), chunk)
                CGEventPost(kCGHIDEventTap, up)
                time.sleep(0.002)

            print(f"[TextInjector] Live typed {len(text)} chars directly at cursor: \"{text}\"", flush=True)
            return True, "success"
        except Exception as e:
            print(f"[TextInjector] Quartz Unicode typing error: {e}", flush=True)
            return False, "event_error"

    def _type_windows(self, text: str) -> tuple:
        """Types string on Windows via pynput into target application."""
        try:
            if self.last_target_hwnd:
                import ctypes
                try:
                    ctypes.windll.user32.SetForegroundWindow(self.last_target_hwnd)
                    time.sleep(0.04)
                except Exception:
                    pass

            from pynput.keyboard import Controller
            kb = Controller()
            kb.type(text)
            return True, "success"
        except Exception as e:
            print(f"[TextInjector] Windows type error: {e}", flush=True)
            return False, "windows_error"
