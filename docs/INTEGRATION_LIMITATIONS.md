# TRIAD — Integration Limitations & Desktop Realities

## 1. Operating Environment & Technical Realities

TRIAD coordinates three consumer AI desktop applications on Windows:
1. **ChatGPT Desktop** (OpenAI: MS Store / WinUI / Electron)
2. **Claude Desktop** (Anthropic: Electron packaged desktop app)
3. **Gemini Desktop** (Google: Standalone Chromium App / PWA window)

These are standalone desktop clients intended for interactive human use, rather than developer-facing server endpoints or headless services.

---

## 2. Absence of Native Internal APIs

A common misconception in multi-agent orchestration is that local desktop applications provide undocumented REST endpoints, local named pipes, or accessible IPC channels. In reality:

1. **No Local Inbound APIs**: Neither OpenAI, Anthropic, nor Google exposes a local REST, gRPC, or IPC interface within their consumer Windows client builds.
2. **Encrypted Cloud Transport**: All prompt submissions and responses are transmitted directly to proprietary SaaS backends over TLS with certificate validation and anti-bot mitigation.
3. **Encapsulated Execution**: The internal web views (Electron Chromium or WinUI WebView2) run in sandboxed worker processes that do not expose external COM interfaces or command-line execution hooks for chat generation.

---

## 3. Strict Prohibitions & Anti-Patterns

To ensure system stability, security, and compliance with platform terms of service, TRIAD explicitly rejects the following fragile or prohibited techniques:

### Prohibited Techniques Matrix

| Technique | Architectural Risk | Reason for Rejection |
|---|---|---|
| **Memory Injection / Debuggers** (`CreateRemoteThread`, `VirtualAllocEx`) | High (Security & Stability) | Causes crashes, triggers Antivirus/EDR alerts, violates process security boundaries. |
| **Token & Cookie Harvesting** (Reading LevelDB / Cookies from AppData) | Critical (Credential Exposure) | Exposes user authentication credentials in plain text; breaks whenever storage formats update. |
| **Unsupported Window Reparenting** (`SetParent` into TRIAD GUI) | High (Visual Glitches) | Modern hardware-accelerated DirectComposition / Chromium surfaces glitch and lose focus control when reparented. |
| **Silent Background Keystroke Injection** | High (Integrity Loss) | Injects characters into wrong applications if the user switches active windows; causes corrupted prompts. |
| **Web Scraping Reverse-Engineering** | Medium (Fragility) | Obfuscated HTML/CSS classes change weekly, causing catastrophic pipeline failures. |

---

## 4. The Clean Integration Pathway: Safe User-Assisted Bridge

TRIAD operates with total architectural transparency:

### Phase 1: Window Discovery & Focus (Operational)
- Enumerate top-level windows using legitimate Win32 APIs (`EnumWindows`, `GetWindowThreadProcessId`, `GetWindowText`).
- Verify process executable names (`psutil`) and package metadata (`WindowsApps`).
- Restore and bring existing windows to foreground without disrupting ongoing chats or launching duplicate instances.

### Phase 2: User-Assisted Message Exchange Bridge (`MOD-02`)
- **Prompt Preparation**: TRIAD formats the debate prompt with clear markdown instructions and role framing.
- **Controlled Handoff**: The user clicks **Copy & Focus**. TRIAD places the formatted prompt onto the system clipboard and raises the targeted native window.
- **Pasting & Generation**: The user performs standard paste (`Ctrl+V`) and enters the prompt.
- **Controlled Ingestion**: When the response completes, the user copies the response and clicks **Import** in TRIAD.
- **Integrity Tracking**: TRIAD parses the imported text, calculates word count and SHA-256 hash, and marks the round response as sealed.

> **Why this design excels**:
> - **Zero Cost**: Completely eliminates all AI API billing.
> - **Zero Account Risk**: Uses the user's authentic, signed-in session without spoofing or botting.
> - **Reliability**: Immune to UI DOM updates, CSS class changes, or backend API deprecations.
> - **Total Transparency**: The user retains full visibility into what is sent and received.

---

## 5. Future Evaluation: Windows UI Automation (Accessibility)

For future roadmap phases (Phase 2B / Phase 3), TRIAD will evaluate **Windows UI Automation (UIA)**:
- UIA is Microsoft's supported accessibility framework designed for screen readers and assistive technology.
- If enabled with explicit user authorization, UIA can detect the accessibility input element (`ControlType.Edit`) and document root (`ControlType.Document`) to streamline prompt insertion.
- Any UIA automation will remain opt-in, non-invasive, and maintain the human operator as the final arbiter.
