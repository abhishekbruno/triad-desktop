# TRIAD — Local AI Consensus Workspace

TRIAD is a zero-additional-cost local desktop workspace engineered for Windows to coordinate three independent AI applications: **ChatGPT Desktop**, **Claude Desktop**, and **Gemini Desktop**.

The goal of the project is to allow a user to enter one prompt into a unified desktop workspace, gather responses from the three participating desktop AI applications, facilitate multi-model reasoning rounds, and synthesize consensus—all without requiring paid external APIs or hosted inference services.

---

## Phase 1 Scope

This repository implements **Phase 1: Native Desktop Application Connection**.

Phase 1 focuses exclusively on discovering, identifying, registering, monitoring, and focusing the three existing native application windows:

- **Desktop Discovery**: Identifies running native instances of ChatGPT, Claude, and Gemini using Windows APIs (`pywin32`) and process inspection (`psutil`).
- **Identity Verification**: Uses executable verification, package metadata, and window characteristics rather than fragile title substring matching.
- **Window Management**: Restores and focuses existing windows without interrupting active conversations or opening duplicate instances.
- **Connection Monitoring**: Continuously detects application lifecycle changes (process terminations, closed windows, restarts).
- **Dark-Themed UI**: Built with PySide6, featuring dedicated status cards, telemetry indicators, and global controls.
- **Local Persistence**: Stores user configuration and discovery audits in a local SQLite database without persisting transient runtime handles (HWND/PID) or private user data.

> **Note**: Phase 1 does not extract chat transcripts, automate keyboard input, or communicate with external AI APIs.

---

## Technology Stack

- **Runtime**: Python 3.12+ (64-bit Windows)
- **GUI Framework**: PySide6 (Qt 6)
- **Windows APIs**: `pywin32` (`win32gui`, `win32process`, `win32api`, `win32con`)
- **Process Inspection**: `psutil`
- **Persistence**: SQLite 3 (Python standard library)
- **Test Framework**: `pytest`, `pytest-mock`
- **Packaging**: `pyinstaller`

---

## Project Structure

```text
triad-desktop/
├── app/
│   ├── core/                  # Discovery, window manager, registry, monitor
│   │   ├── agent_registry.py
│   │   ├── app_discovery.py
│   │   ├── connection_monitor.py
│   │   └── window_manager.py
│   ├── models/                # Dataclasses and enums
│   │   └── agent.py
│   ├── storage/               # SQLite persistence and audit log
│   │   └── database.py
│   ├── ui/                    # PySide6 windows, cards, dialogs, styling
│   │   ├── agent_card.py
│   │   ├── main_window.py
│   │   ├── styles.qss
│   │   └── window_picker_dialog.py
│   └── utils/                 # Structured logging
│       └── logging.py
├── docs/
│   └── ROADMAP.md             # Development roadmap (Phases 1–6)
├── tests/                     # Unit and integration tests
├── build.ps1                  # Packaging script for PyInstaller
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── .gitignore
├── LICENSE
└── README.md
```

---

## Getting Started

### Prerequisites

- Windows 10 or Windows 11 (64-bit)
- Python 3.12 or newer

### Setup Instructions

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/abhishekbruno/triad-desktop.git
   cd triad-desktop
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Launch the application:**
   ```powershell
   python main.py
   ```

---

## Running Automated Tests

Run the full test suite with:

```powershell
pytest -v tests/
```

The test suite validates:
- Multi-app discovery and classification
- Ambiguous window disambiguation and user picker flows
- Window focus and minimization restoration logic
- Windows foreground restriction handling
- Agent lifecycle transitions (`MISSING` → `DETECTED` → `BOUND` → `STALE`)
- Persistence across application restarts

---

## Building Executable

To package a standalone Windows executable:

```powershell
.\build.ps1
```

The resulting binary will be created in `dist/TRIAD.exe`.

---

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

