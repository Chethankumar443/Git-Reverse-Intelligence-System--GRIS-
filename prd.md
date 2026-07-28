---
document: prd.md — Product Requirements (distilled, frozen)
supersedes: the original prd.md (round-3 draft) — DELETE the old file
companion_to: DESIGN.md (implementation), CHARTER.md (impact/ethics), trd.md (tech reqs)
rule: this file states WHAT and WHY only. No code. Implementation → DESIGN.md §N.
---

# Git Reverse — Product Requirements Document

## 1. Product overview
Git Reverse is a native Windows desktop app that takes a GitHub repository URL,
analyzes it, and generates a standardized AI "recreation prompt" — the prompt
that would rebuild that codebase from scratch. It replaces a terminal workflow
with a visual, conversation-style dashboard.

## 2. Target users
- Developers reverse-engineering repos into reusable prompts.
- AI power-users generating standardized system prompts from real code.
- Team leads needing an exportable record of which prompt recreates which repo.

## 3. User stories & acceptance criteria
| ID | Story | Acceptance criteria | Impl ref |
|---|---|---|---|
| US1 | Launch from Start Menu, no Python/batch | Single `.exe` install; no console window | DESIGN §12 P4 |
| US2 | Paste URL → see analysis progress | Progress + live log visible; UI never freezes | DESIGN §5.2, §7 |
| US3 | Read generated prompt formatted/highlighted | Streamed into code pane; copy-to-clipboard works | DESIGN §5.3, §6.2 |
| US4 | Export session as PDF or Markdown | Native OS save dialog; styled output | DESIGN §6.6, §6.7 |
| US5 | Browse/resume past sessions from sidebar | Click row → reloads completed view | DESIGN §5.1, §6.4 |
| US6 | Configure keys in Settings (BYOK, any provider) | Keys to OS keyring; "Test" button; provider picker | DESIGN §5.2, §6.2 |
| US7 | Toggle Light/Dark without restart | Runtime theme swap | DESIGN §4.1 |
| US8 | See LLM output stream in real time | Tokens append as they arrive | DESIGN §7 |
| US9 | See source LICENSE + attribution on every result | License surfaced; copyleft advisory; export footer | CHARTER §2.2 |

## 4. Functional requirements
- FR1 Accept a GitHub repo URL; validate format before any network call.
- FR2 Fetch tree, filter ignored dirs, cap file size, analyze structure/deps/language.
- FR3 Stream a recreation prompt from a user-supplied (BYOK) OpenAI-compatible provider.
- FR4 Persist each session (URL, repo, language, file count, prompt, model, time, status).
- FR5 Export to PDF (Geist-styled) and Markdown via native dialogs.
- FR6 Maintain a resumable session history.
- FR7 Store all secrets in the OS credential manager; never in files.
- FR8 Detect and display the analyzed repo's license; warn on copyleft/none; append an
  attribution block to every export (responsible-use requirement; see §6).
- FR9 Provide Light/Dark themes and a configurable default export directory.

## 5. User-observable non-functional expectations
- The UI stays responsive during all network/LLM work (no "not responding").
- The app runs with no prior Python install and no mandatory cloud account
  (free-tier + local provider presets must remain first-class).
- First launch shows a one-screen acceptable-use note (see §6).

## 6. Responsible-use requirement (mandatory, not optional)
Because the core feature can reproduce licensed code, the product MUST:
(a) surface the source license, (b) show a non-blocking copyleft/proprietary advisory,
(c) include source+license+date in every export, (d) never offer to strip attribution,
(e) obtain acceptable-use acceptance at first launch. **The SDG-4 (education) claim in
CHARTER §1.1 is conditional on this section shipping.** Impl: CHARTER §2.2; DESIGN §6.2.

## 7. Out of scope (alpha)
Git write operations, code editing, hosting/CI, multi-user collaboration,
non-Windows platforms, native Anthropic API (OpenAI-compatible proxies only).

## 8. Success / acceptance
A beta is acceptable when US1–US9 pass on a clean Windows install with a BYOK key,
the UI never blocks, exports open correctly, and the license/attribution footer is
present on every PDF/Markdown. Impact framing → CHARTER.md (do not overclaim SDGs).
