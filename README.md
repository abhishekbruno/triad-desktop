# TRIAD — Local AI Consensus Workspace

[![TRIAD CI](https://github.com/abhishekbruno/triad-desktop/actions/workflows/ci.yml/badge.svg)](https://github.com/abhishekbruno/triad-desktop/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python: 3.12+](https://img.shields.io/badge/Python-3.12+-teal.svg)](https://www.python.org/)
[![Platform: Windows 10/11](https://img.shields.io/badge/Platform-Windows_64--bit-darkblue.svg)](https://www.microsoft.com/windows)

TRIAD is a zero-additional-cost, privacy-first Windows desktop workspace designed to coordinate three independent desktop AI applications: **ChatGPT Desktop**, **Claude Desktop**, and **Gemini Desktop**.

Instead of incurring recurring monthly bills for paid external APIs, relying on cloud proxy servers, or requiring high-end local GPUs for local models, TRIAD coordinates the three native desktop applications already signed in on your computer. Through a structured multi-round deliberation protocol, TRIAD synthesizes consensus, isolates disagreements, and compiles minority objections—all running completely locally.

---

## The 14 Core Capabilities

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TRIAD WORKSPACE ENGINE                             │
├──────────────────────────────┬──────────────────────────────┬───────────────┤
│ 1. Unified AI Workspace      │ 6. Disagreement Map          │ 11. Human     │
│ 2. Independent Reasoning     │ 7. Claim & Evidence Check    │     Override  │
│ 3. Cross-Model Debate Engine │ 8. Shared Reasoning Memory   │ 12. Session   │
│ 4. Consensus & Majority Vote │ 9. Minority Reports          │     Replay    │
│ 5. Devil's Advocate Mode     │ 10. Smart Stopping Rules     │ 13. Discussion│
│                              │                              │     Export    │
│                              │                              │ 14. 5 Modes   │
└──────────────────────────────┴──────────────────────────────┴───────────────┘
```

1. **Unified AI Workspace**: A single command center for coordinating ChatGPT, Claude, and Gemini on Windows.
2. **Independent First-Round Reasoning**: Guarantees that each model produces its initial answer in isolation before seeing peer arguments, eliminating anchoring bias.
3. **Cross-Model Debate Engine**: Synthesizes structured critique prompts where models challenge each other's assumptions and methodology.
4. **Consensus and Majority Voting**: Deterministic voting calculus supporting **3/3 Unanimous**, **2/3 Majority**, or **No Consensus**.
5. **Devil's Advocate Mode**: Automatically stress-tests emerging consensus by assigning an adversarial critique role to a dissenter or rotating participant.
6. **Disagreement Map**: Visual matrix highlighting which models support or oppose specific claims and where concessions were made.
7. **Evidence & Claim Verification**: Extracts atomic claims and tracks supporting arguments without mistaking high model confidence for factual proof.
8. **Shared Reasoning Memory**: Local SQLite ledger recording the complete deliberation history, candidate proposals, and ballots.
9. **Minority Reports**: Mandatory preservation and presentation of dissenting viewpoints on 2/3 majority votes.
10. **Smart Stopping Rules**: Automatic detection of semantic convergence, debate stagnation, and strict round ceilings.
11. **Human Override**: Total operator authority to overrule verdicts, adjudicate ambiguous proposals, or inject supplemental rounds.
12. **Session Replay**: Interactive chronological timeline showing how positions shifted across rounds.
13. **Discussion Export**: Standalone export to Markdown, structured JSON, and printable HTML.
14. **Multiple Reasoning Modes**: Tailored deliberation modes: *Quick Consensus*, *Deep Debate*, *Research Council*, *Code Review Council*, and *Creative Council*.

---

## Four-Tier Architecture

TRIAD is engineered with strict separation of concerns across four tiers:

1. **Presentation Layer**: Dark-themed PySide6 desktop interface featuring telemetry cards, session timeline, disagreement map, and voting dashboards.
2. **Reasoning Coordination Layer**: Headless, platform-independent deliberation state machine managing debate rounds, Devil's Advocate challenges, candidate equivalence, and voting calculus.
3. **Integration Layer**: Legitimate Win32 application discovery and window management, coupled with a safe user-assisted clipboard bridge.
4. **Persistence Layer**: Versioned local SQLite database (`%LOCALAPPDATA%/TRIAD/triad_workspace.db`) storing sessions, claims, ballots, and audit logs.

For comprehensive architectural specifications, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Current Status: Phase 1 Operational

TRIAD is built under a strict phased gating model:

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | **Native Desktop Application Discovery & Focus** | **COMPLETED & OPERATIONAL** |
| **Phase 2** | User-Controlled Message Exchange Bridge | Planned (Next) |
| **Phase 3** | Reasoning Session & Cross-Model Debate Engine | Planned |
| **Phase 4** | Deterministic Consensus & Disagreement Mapping | Planned |
| **Phase 5** | Shared Memory, Session Replay & Export | Planned |
| **Phase 6** | Production Hardening, Packaging & CI Matrix | Planned |

> **Phase 1 Scope**: Discovers, registers, monitors, and focuses existing ChatGPT, Claude, and Gemini desktop windows. Phase 1 does not extract conversations, submit prompts automatically, or contact paid external APIs.

See [docs/ROADMAP.md](docs/ROADMAP.md) for the complete multi-phase development plan.

---

## Architectural Documentation

Detailed technical design specifications are available in the `docs/` directory:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): Four-tier architecture, 14 architectural modules (MOD-01 through MOD-14), module dependencies, and security boundaries.
- [docs/CONSENSUS_PROTOCOL.md](docs/CONSENSUS_PROTOCOL.md): Mathematical voting calculus, structured ballot schema, Devil's Advocate rules, and Minority Report protocols.
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md): Relational SQLite schema, Entity-Relationship diagram, migrations, and JSON export specifications.
- [docs/INTEGRATION_LIMITATIONS.md](docs/INTEGRATION_LIMITATIONS.md): Technical realities of Windows desktop AI applications, why internal APIs do not exist, and the user-assisted bridge design.
- [docs/ROADMAP.md](docs/ROADMAP.md): Phased roadmap, acceptance criteria, and quality gates.

---

## Technology Stack

- **Runtime**: Python 3.12+ (64-bit Windows)
- **GUI Framework**: PySide6 (Qt 6)
- **Windows APIs**: `pywin32` (`win32gui`, `win32process`, `win32api`, `win32con`)
- **Process Inspection**: `psutil`
- **Persistence**: SQLite 3 (Python standard library)
- **Testing**: `pytest`, `pytest-mock` (29 automated unit and scenario tests)
- **Packaging**: `pyinstaller` (Windows standalone binary)

---

## Quick Start (Phase 1 Desktop Application)

### 1. Prerequisites
- Windows 10 or Windows 11 (64-bit)
- Python 3.12 or newer
- ChatGPT Desktop, Claude Desktop, and/or Gemini Desktop installed

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/abhishekbruno/triad-desktop.git
cd triad-desktop

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run the Desktop Workspace
```powershell
python main.py
```

### 4. Run Automated Tests
```powershell
pytest -v
```

### 5. Build Standalone Executable
```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1 -Clean
```
The compiled standalone binary will be generated in `dist\TRIAD\TRIAD.exe`.

---

## Privacy & Security Guarantees

- **100% Local**: No telemetry, analytics, or session payloads leave your workstation.
- **Zero Credential Harvesting**: Never accesses, reads, or stores passwords, tokens, cookies, or account sessions.
- **Untrusted Input Model**: All model responses are treated as untrusted strings wrapped in delimiter envelopes, preventing prompt injection.
- **Safe Process Boundaries**: Does not inject DLLs, attach debuggers, or violate application memory.

---

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
