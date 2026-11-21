# TRIAD Development Roadmap

This document outlines the phased engineering milestones for the TRIAD Local AI Consensus Workspace.

## Phase 1: Native Desktop Application Discovery and Connection (Current)
- Windows application discovery service targeting ChatGPT Desktop, Claude Desktop, and Gemini Desktop.
- Non-sensitive process and window inspection (HWND, PID, executable name, window title, state).
- Multi-window candidate resolution with interactive user selection.
- Foreground window restoration and focus respecting Windows foreground lock constraints.
- Real-time connection monitoring detecting process exits and window invalidations.
- Local SQLite database preserving user preferences without storing transient runtime IDs or session data.

## Phase 2: User-Controlled Message Exchange (Planned)
- Safe, user-authorized dispatch of prompts to selected native application windows.
- Structured clipboard and accessibility-based interface bridges.
- Visual inspection of outbound messages prior to manual or automated dispatch.

## Phase 3: Multi-Agent Discussion Engine (Planned)
- Orchestration round engine exchanging intermediary responses across the three participants.
- Cross-examination rounds where each model evaluates perspectives from the other two.
- Configurable reasoning loops and termination criteria.

## Phase 4: Consensus and Majority Voting (Planned)
- Semantic similarity comparison and claim alignment verification.
- Detection of unanimous agreement, majority consensus (2-out-of-3), and unresolved dissents.
- Synthesis of consensus summaries highlighting converging facts and distinct viewpoints.

## Phase 5: Shared Workspace and History (Planned)
- Local session ledger recording full deliberation histories.
- Export options (Markdown, JSON, HTML).
- Privacy-first on-disk encryption for archived deliberations.

## Phase 6: Optimization, Hardening, and Packaging (Planned)
- Production PyInstaller bundling for standalone Windows distribution.
- Automated CI testing matrix across Windows OS releases.
- Performance optimization ensuring minimal CPU and memory overhead during idle monitoring.

