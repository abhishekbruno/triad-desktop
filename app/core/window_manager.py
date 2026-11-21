from typing import Any, Dict, Optional, Tuple
from app.utils.logging import get_logger

try:
    import win32api
    import win32con
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

logger = get_logger("window_manager")


class WindowManager:
    """Safely manages native Windows application windows.

    Capabilities:
    - Validates window handles (HWND)
    - Restores minimized windows
    - Brings registered application windows to the foreground
    - Handles Windows foreground lock restrictions gracefully
    - Never destroys active conversations or closes applications
    """

    @staticmethod
    def _ensure_desktop_access() -> None:
        """Ensures calling thread has access to interactive desktop."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            h_default = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if h_default:
                user32.SetThreadDesktop(h_default)
        except Exception:
            pass

    @staticmethod
    def is_window_valid(hwnd: Optional[int]) -> bool:
        """Verifies whether an HWND currently references a valid top-level window."""
        if not hwnd or hwnd <= 0:
            return False
        if not HAS_WIN32:
            return False
        WindowManager._ensure_desktop_access()
        try:
            return bool(win32gui.IsWindow(hwnd))
        except Exception:
            return False

    @staticmethod
    def get_window_state(hwnd: int) -> Dict[str, Any]:
        """Inspects non-sensitive state of a window."""
        if not HAS_WIN32 or not WindowManager.is_window_valid(hwnd):
            return {"valid": False}
        WindowManager._ensure_desktop_access()
        try:
            is_visible = bool(win32gui.IsWindowVisible(hwnd))
            is_minimized = bool(win32gui.IsIconic(hwnd))
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return {
                "valid": True,
                "hwnd": hwnd,
                "pid": pid,
                "title": title,
                "is_visible": is_visible,
                "is_minimized": is_minimized,
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    @staticmethod
    def focus_window(hwnd: int) -> Tuple[bool, str]:
        """Restores and brings the specified window to foreground.

        Respects Windows foreground lock restrictions:
        - If Windows allows foreground transfer, the window becomes active.
        - If restricted, returns a clear status message instead of attempting unauthorized bypasses.
        """
        if not HAS_WIN32:
            return False, "Windows API (pywin32) is not available on this platform."

        WindowManager._ensure_desktop_access()
        if not WindowManager.is_window_valid(hwnd):
            return False, f"Window handle {hwnd} is invalid or has been closed."

        try:
            # 1. Restore if minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            # 2. Handle foreground thread attachment
            current_thread_id = win32api.GetCurrentThreadId()
            target_thread_id, _ = win32process.GetWindowThreadProcessId(hwnd)
            attached = False

            if current_thread_id != target_thread_id:
                try:
                    win32process.AttachThreadInput(current_thread_id, target_thread_id, True)
                    attached = True
                except Exception as attach_err:
                    logger.debug("AttachThreadInput info: %s", attach_err)

            try:
                win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)
                return True, "Window focused successfully."
            except Exception as fg_err:
                msg = (
                    f"Windows foreground restriction prevented instant focus ({fg_err}). "
                    "Window taskbar icon may be flashing."
                )
                logger.warning(msg)
                return False, msg
            finally:
                if attached:
                    try:
                        win32process.AttachThreadInput(current_thread_id, target_thread_id, False)
                    except Exception:
                        pass

        except Exception as e:
            err_msg = f"Failed to focus window: {e}"
            logger.error(err_msg)
            return False, err_msg

