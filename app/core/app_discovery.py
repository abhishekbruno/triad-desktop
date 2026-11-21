import os
import re
from typing import Dict, List, Optional, Tuple
import psutil

try:
    import win32gui
    import win32process
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

from app.models.agent import (
    AgentAppDefinition,
    SUPPORTED_AGENTS,
    WindowCandidate,
)
from app.utils.logging import get_logger

logger = get_logger("discovery")


class AppDiscoveryService:
    """Discovers and identifies running Windows applications corresponding to supported AI agents.

    Identifies:
    1. ChatGPT Desktop (MS Store / WinUI / Electron / PWA)
    2. Claude Desktop (Electron / AppData / PWA)
    3. Gemini Desktop (Standalone PWA / Desktop Wrapper)

    CRITICAL RULES:
    - Never identify an application based only on a vague title substring.
    - Check process executable identity, package metadata, and window characteristics.
    - If identification is ambiguous, mark as candidate for user review.
    - Collect non-sensitive metadata only (HWND, PID, executable name, path, title, state).
    """

    def __init__(self, agent_definitions: Optional[Dict[str, AgentAppDefinition]] = None):
        self.definitions = agent_definitions or SUPPORTED_AGENTS

    def scan_desktop_windows(self) -> List[WindowCandidate]:
        """Enumerates top-level visible desktop windows using Windows APIs."""
        candidates: List[WindowCandidate] = []
        if not HAS_WIN32:
            logger.warning("win32 modules not available. Discovery running in stub/mock mode.")
            return candidates

        def enum_callback(hwnd: int, extra: None) -> bool:
            try:
                if not win32gui.IsWindow(hwnd):
                    return True

                # Must be a top-level visible window or minimized top-level window
                is_visible = bool(win32gui.IsWindowVisible(hwnd))
                is_minimized = bool(win32gui.IsIconic(hwnd))

                # Skip completely hidden windows unless minimized
                if not is_visible and not is_minimized:
                    return True

                title = win32gui.GetWindowText(hwnd).strip()
                if not title:
                    return True

                # Ignore known system/utility classes (tooltips, system tray, etc.)
                class_name = win32gui.GetClassName(hwnd)
                if class_name in (
                    "Progman",
                    "Shell_TrayWnd",
                    "Windows.UI.Core.CoreWindow",
                    "EdgeUiInputTopWndClass",
                ):
                    return True

                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid <= 4:  # System idle / kernel
                    return True

                exec_name, exec_path = self._get_process_info(pid)
                package_name = self._get_package_identity(exec_path)

                candidate = WindowCandidate(
                    hwnd=hwnd,
                    pid=pid,
                    title=title,
                    executable_name=exec_name,
                    executable_path=exec_path,
                    package_name=package_name,
                    is_visible=is_visible,
                    is_minimized=is_minimized,
                )
                candidates.append(candidate)
            except Exception as ex:
                logger.debug("Error processing window %s: %s", hwnd, ex)
            return True

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception as e:
            logger.error("EnumWindows failed: %s", e)

        return candidates

    def _get_process_info(self, pid: int) -> Tuple[str, Optional[str]]:
        """Safely queries executable name and full path without crashing on AccessDenied."""
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            try:
                exe = proc.exe()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                exe = None
            return name, exe
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "unknown", None

    def _get_package_identity(self, exec_path: Optional[str]) -> Optional[str]:
        """Detects Windows Store / MSIX package directory identity if present."""
        if not exec_path:
            return None
        lower_path = exec_path.lower()
        if "windowsapps" in lower_path:
            # Parse package folder name
            parts = exec_path.replace("/", "\\").split("\\")
            for part in parts:
                if "_" in part and any(sig in part.lower() for sig in ["openai", "anthropic", "google"]):
                    return part
        return None

    def _get_process_cmdline(self, pid: int) -> List[str]:
        """Retrieves process command-line arguments to inspect Chromium PWA flags."""
        try:
            proc = psutil.Process(pid)
            return proc.cmdline()
        except (psutil.AccessDenied, psutil.NoSuchProcess, Exception):
            return []

    def classify_window(self, candidate: WindowCandidate) -> Tuple[Optional[str], float, str]:
        """Evaluates a candidate window against all supported agent definitions.

        Returns:
            Tuple of (agent_id or None, confidence_score [0.0 - 1.0], match_reason)
        """
        exec_lower = candidate.executable_name.lower()
        title_lower = candidate.title.lower()

        # Reject generic browser search / tabs (e.g. "search on google: chatgpt")
        misleading_browser_titles = [
            "google search",
            "bing search",
            "duckduckgo",
            " - google chrome",
            " - personal - microsoft​ edge",
            " - work - microsoft​ edge",
            " - mozilla firefox",
        ]
        is_generic_browser_tab = any(m in title_lower for m in misleading_browser_titles)

        for agent_id, defn in self.definitions.items():
            # 1. Native Executable Exact Match (High Confidence)
            for known_exe in defn.known_executables:
                if exec_lower == known_exe.lower():
                    # Double check title doesn't blatantly contradict
                    reason = f"Native executable '{candidate.executable_name}' matched"
                    return agent_id, 0.95, reason

            # 2. Package Identity Match (MS Store / AppX)
            if candidate.package_name:
                pkg_lower = candidate.package_name.lower()
                for pkg_sig in defn.package_family_names:
                    if pkg_sig.lower() in pkg_lower:
                        reason = f"Store package '{candidate.package_name}' matched"
                        return agent_id, 0.95, reason

            # 3. PWA / App-Mode Chromium window match
            # If executable is chrome, msedge, or proxy, check for app mode
            if exec_lower in ("chrome.exe", "msedge.exe", "chrome_proxy.exe", "msedge_proxy.exe"):
                # Check command line flags (e.g. --app=https://...)
                cmdline = self._get_process_cmdline(candidate.pid)
                cmdline_str = " ".join(cmdline).lower()

                for pwa_pattern in defn.pwa_app_patterns:
                    if f"--app=https://{pwa_pattern}" in cmdline_str or f"--app=http://{pwa_pattern}" in cmdline_str or pwa_pattern in cmdline_str:
                        # Verify title matches agent signature
                        if any(sig.lower() in title_lower for sig in defn.known_title_signatures):
                            return agent_id, 0.90, f"Chromium app mode for {pwa_pattern}"

                # If cmdline wasn't accessible, check if title starts cleanly with app name
                # and doesn't have standard multi-tab browser suffix
                if not is_generic_browser_tab:
                    for sig in defn.known_title_signatures:
                        pattern = rf"^{re.escape(sig.lower())}(\s*[-—|•]|$)"
                        if re.search(pattern, title_lower):
                            return agent_id, 0.65, f"Candidate window title '{candidate.title}' in {candidate.executable_name}"

            # 4. Strict title match for standalone wrappers
            if not is_generic_browser_tab:
                for sig in defn.known_title_signatures:
                    if title_lower == sig.lower():
                        return agent_id, 0.70, f"Exact window title match: '{candidate.title}'"

        return None, 0.0, "No supported agent signature identified"

    def discover_candidates(self) -> Dict[str, List[WindowCandidate]]:
        """Scans system and groups identified candidate windows by agent_id."""
        windows = self.scan_desktop_windows()
        grouped: Dict[str, List[WindowCandidate]] = {agent_id: [] for agent_id in self.definitions}

        for win in windows:
            agent_id, confidence, reason = self.classify_window(win)
            if agent_id and confidence >= 0.50:
                win.confidence = confidence
                win.match_reason = reason
                grouped[agent_id].append(win)

        for agent_id, list_cands in grouped.items():
            # Sort highest confidence first
            list_cands.sort(key=lambda c: c.confidence, reverse=True)
            logger.info("Agent %s: found %d candidate windows", agent_id, len(list_cands))

        return grouped

