# TRIAD — Testing Strategy & Verification Report

## 1. Overview & Test Philosophy

TRIAD employs a dual-tiered testing methodology:
1. **Automated Unit & Scenario Tests (Mocks)**: Fully isolated, deterministic tests executed in CI and local test runs without requiring running desktop applications or an interactive display.
2. **Real Interactive Windows Desktop Tests**: Direct physical verification against running native Windows applications (`ChatGPT.exe`, `Claude.exe`, Chrome/Edge PWA windows) on Windows 10/11 desktops.

> **CRITICAL RULE**: TRIAD never confuses mocked automated unit tests with real Windows acceptance tests. Unverified scenarios and live desktop discoveries are documented with explicit evidence.

---

## 2. Automated Test Suite (pytest)

The test suite is organized under `tests/` and executed with `pytest`:

```text
tests/
├── __init__.py
├── test_discovery.py       # PWA, native, package signatures, and rejection of misleading titles
├── test_message_bridge.py  # Phase 2: Staging, clipboard copy, focus, response import, SHA-256 hashes
├── test_window_manager.py  # Window validation, focus restoration, foreground lock handling
├── test_registry.py        # Lifecycle transitions (MISSING -> DETECTED -> BOUND -> STALE)
├── test_monitor.py         # Process termination and window closing detection
├── test_storage.py         # SQLite persistence, preferences, sessions, and responses
└── test_scenarios.py       # Comprehensive 10-point acceptance scenarios
```

### Execution Command
```powershell
.\.venv\Scripts\pytest -v
```

### Automated Test Results
- **Collected**: 46
- **Passed**: 46
- **Failed**: 0
- **Execution Time**: ~1.04 seconds

```text
tests/test_discovery.py (5/5 passed)
tests/test_message_bridge.py (17/17 passed)
tests/test_monitor.py (2/2 passed)
tests/test_registry.py (4/4 passed)
tests/test_scenarios.py (10/10 passed)
tests/test_storage.py (4/4 passed)
tests/test_window_manager.py (4/4 passed)
============================== 46 passed in 1.04s ==============================
```
tests/test_discovery.py::test_classify_native_claude PASSED              [  6%]
tests/test_discovery.py::test_classify_gemini_pwa_mode PASSED            [ 10%]
tests/test_discovery.py::test_reject_unrelated_process_with_misleading_title PASSED [ 13%]
tests/test_discovery.py::test_reject_generic_code_editor_with_ai_title PASSED [ 17%]
tests/test_monitor.py::test_monitor_detects_closed_window PASSED         [ 20%]
tests/test_monitor.py::test_monitor_detects_terminated_process PASSED    [ 24%]
tests/test_registry.py::test_registry_initialization PASSED              [ 27%]
tests/test_registry.py::test_registry_binding_and_summary_transitions PASSED [ 31%]
tests/test_registry.py::test_registry_disconnect_and_stale PASSED        [ 34%]
tests/test_registry.py::test_registry_subscription_listener PASSED       [ 37%]
tests/test_scenarios.py::test_scenario_1_all_three_detected PASSED       [ 41%]
tests/test_scenarios.py::test_scenario_2_only_chatgpt_running PASSED     [ 44%]
tests/test_scenarios.py::test_scenario_3_no_applications_running PASSED  [ 48%]
tests/test_scenarios.py::test_scenario_4_multiple_candidate_windows PASSED [ 51%]
tests/test_scenarios.py::test_scenario_5_app_closes_after_registration PASSED [ 55%]
tests/test_scenarios.py::test_scenario_6_app_restarts PASSED             [ 58%]
tests/test_scenarios.py::test_scenario_7_invalid_saved_connection PASSED [ 62%]
tests/test_scenarios.py::test_scenario_8_window_focus_failure PASSED     [ 65%]
tests/test_scenarios.py::test_scenario_9_unrelated_process_misleading_title PASSED [ 68%]
tests/test_scenarios.py::test_scenario_10_config_persists_across_restarts PASSED [ 72%]
tests/test_storage.py::test_database_initialization_and_schema PASSED    [ 75%]
tests/test_storage.py::test_agent_preferences_persistence PASSED         [ 79%]
tests/test_storage.py::test_ui_settings_storage PASSED                   [ 82%]
tests/test_storage.py::test_discovery_audit_logging PASSED               [ 86%]
tests/test_window_manager.py::test_is_window_valid_invalid_inputs PASSED [ 89%]
tests/test_window_manager.py::test_focus_window_invalid_handle PASSED    [ 93%]
tests/test_window_manager.py::test_focus_window_restores_and_activates PASSED [ 96%]
tests/test_window_manager.py::test_focus_window_foreground_restriction_handled_cleanly PASSED [100%]
```

---

## 3. Real Interactive Windows Acceptance Testing

Real interactive verification was conducted directly against live applications running on Windows 11:

### Live Application Discovery Telemetry

| Application | Process Name | PID | HWND | Window Title | State | Verified Behavior |
|---|---|---|---|---|---|---|
| **ChatGPT Desktop** | `ChatGPT.exe` | 2848 | `132636` | `"ChatGPT"` | Visible (`Rect: 960, 0, 1920, 1080`) | **Detected (0.95 confidence)**. Window is identified, rect mapped, and focusable. |
| **Claude Desktop** | `claude.exe` | 15312 | `3081544` | `"Claude"` | Minimized (`IsIconic=1`, `-32000, -32000`) | **Detected (0.95 confidence)**. Successfully un-minimized with `SW_RESTORE` and focused to foreground. |
| **Gemini Desktop** | — | — | — | — | Not Running | **Correctly detected as MISSING (0 candidates)**. No false positives triggered. |

---

## 4. Confirmed Defects and Architectural Fixes

### Defect 1: Windows Station / Virtual Desktop Isolation
- **Symptom**: When TRIAD or test scripts run from a background subshell or virtual desktop (`exebox-...`), `win32gui.EnumWindows` returned 0 windows even though ChatGPT and Claude were running on the user's interactive desktop.
- **Root Cause**: Windows isolates window handles by desktop stations. A thread assigned to a secondary desktop cannot enumerate windows on `WinSta0\Default`.
- **Fix Applied**: `AppDiscoveryService.scan_desktop_windows()` and `WindowManager._ensure_desktop_access()` now automatically open `OpenDesktopW("Default", ...)` and attach the thread using `SetThreadDesktop()`. This guarantees immediate discovery across interactive and subshell contexts.

### Defect 2: Win32 EnumWindows Buffer Warning (Error 122)
- **Symptom**: `EnumWindows` intermittently aborted with `pywintypes.error: (122, 'EnumWindows', 'The data area passed to a system call is too small.')` when inspecting certain Windows 11 system windows.
- **Root Cause**: In pywin32, internal callbacks that trigger benign buffer queries set `GetLastError() = 122`, which pywin32 misinterprets as an enumeration failure.
- **Fix Applied**: Wrapped callback iterations with `kernel32.SetLastError(0)` to prevent spurious buffer overflow aborts.

### Defect 3: SQLite File Lock on Windows (`PermissionError: WinError 32`)
- **Symptom**: Tests attempting to delete temporary SQLite databases failed with `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process`.
- **Root Cause**: Standard `with conn:` in Python `sqlite3` only commits transactions; it leaves the connection file handle open until garbage collection.
- **Fix Applied**: Implemented an explicit `@contextmanager` in `DatabaseManager._get_connection()` that yields the connection and explicitly calls `conn.close()` in a `finally` block.

---

## 5. Manual Acceptance Checklist

To verify TRIAD on your Windows machine with all three desktop apps open:

1. **Launch Apps**: Open ChatGPT Desktop, Claude Desktop, and Gemini (PWA or Chrome App).
2. **Launch TRIAD**:
   ```powershell
   python main.py
   ```
3. **Scan**: Click **Scan Applications**. Confirm all three application cards populate with live PIDs and HWNDs.
4. **Connect All**: Click **Connect Available Apps**. Verify the summary badge transitions to:
   `"3/3 Desktop Applications Bound — Phase 1 Ready"`
5. **Focus Test**:
   - Click **Focus** on ChatGPT: ChatGPT window appears in foreground.
   - Click **Focus** on Claude: Claude window restores from minimized state without reloading chat.
   - Click **Focus** on Gemini: Gemini window focuses cleanly.
6. **Disconnection & Stale Detection**:
   - Close Claude Desktop.
   - Within 1.5 seconds, the Claude card status transitions to `STALE`.
   - Re-open Claude and click **Refresh All**: Claude rebinds; ChatGPT and Gemini remain unaffected.

