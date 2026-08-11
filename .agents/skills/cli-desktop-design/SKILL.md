---
name: cli-desktop-design
description: Design and build professional, clean, minimal desktop applications, dev tools, and CLI entry points with restrained branding, high information density, and a calm, confident interaction model (style of Yoink, gh, Stripe CLI, Vercel, Raycast).
---

# Developer Desktop App & CLI Tool Design Protocol

This skill governs the design, typography, layout, interactive flow, and copy style for developer desktop applications, CLI tools (`bin` entrypoints), and developer platform interfaces.

---

## 1. Aesthetic Philosophy: Calm, Confident Restraint

Best-in-class developer tools (Vercel, GitHub CLI, Stripe CLI, Raycast, Yoink, Linear) do not compete for attention. They get out of the way and display complex information with precision.

### Core Visual Defaults
- **Palette**: Near-black ink (`#171717`), light canvas (`#fafafa`), crisp white elevated panels (`#ffffff`), hairline borders (`1px solid #ebebeb`).
- **Accent Color**: Single functional blue accent (`#0070f3`) reserved exclusively for focus states, primary links, and active progress.
- **Chrome**: Zero visual clutter. Flat elevation with hairline borders instead of drop shadows. Floating menus use whisper soft micro-shadows (`0 8px 32px rgba(0,0,0,0.08)`).
- **Typography**: Dual-font hierarchy:
  - **Display & UI**: Geometric sans (`Geist`, `Inter`) with tight negative letter-spacing (`-0.03em` to `-0.05em` on headings) and OpenType features `font-feature-settings: "ss01" on, "ss02" on`.
  - **Data, Logs & Eyebrows**: Monospace (`Geist Mono`, `JetBrains Mono`) for code, tokens, line numbers, hashes, and section eyebrows.

---

## 2. Desktop Ergonomics & Information Density

Desktop applications are tools for work, not marketing landing pages.

### Layout Principles
1. **App Shell Grid**: Fixed viewport height (`100dvh`), zero root scrolling. Split into a persistent drag topbar, a fixed-width sidebar (`200px - 240px`), and a main workspace pane.
2. **Dense Data Cells**: Multi-column metadata grids (`2-up`, `3-up`, `4-up` hairline cell blocks) for instant scannability.
3. **Split Panes**: Left/Right or Top/Bottom split panes for simultaneous input/output viewing (e.g. pipeline steps + live terminal log).
4. **Keyboard-First Controls**:
   - `⌘K` / `Ctrl+K`: Global command palette.
   - `Esc`: Dismiss modals and drawers.
   - `Enter`: Submit form / run action.
   - `Ctrl+Enter`: Multiline submit.

---

## 3. Terminal & CLI Output Standards

When rendering CLI output, logs, spinners, or interactive pickers:

- **Status Banners**:
  - `[OK]`: Green (`#16a34a`) for completed stages and clean assertions.
  - `[INFO]`: Blue (`#0070f3`) for pipeline status and environment updates.
  - `[WARN]`: Amber (`#d97706`) for non-blocking notices and rate warnings.
  - `[ERR]`: Red (`#dc2626`) for execution failures with exact tracebacks.
- **Spinners & Progress**: Smooth continuous spinners without flicker. Minimum `400ms` step timer to avoid visual jitter during fast lookups.
- **Tables & Alignment**: Right-align numbers, left-align names, mono-font hashes/timestamps.

---

## 4. Copy & Tone Guidelines

- **Active Verbs**: Use direct, action-oriented button copy ("Reverse Repo", "Export PDF", "Save Key", "Test Connection").
- **No Fluff / No Jargon Clichés**: Avoid marketing buzzwords ("Seamless", "Unleash", "Next-Gen", "Elevate"). State what the tool does plainly.
- **Transparent Errors**: State what failed, why it failed, and the exact command or setting to fix it.

---

## 5. Security & Responsible Science Defaults

- **OS Keyring Integration**: API keys must be stored in OS Credential Manager (`keyring` / Keychain), never printed in logs or plain config files.
- **License Compliance**: Surface open-source license badges (`SPDX`) and auto-append attribution blocks to exported artifacts.
