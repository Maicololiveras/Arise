# ARISE 0.4.55 — Agent controls in the chat header

Choose profiles, models, reasoning effort or account sign-in from the desktop chat. Model and effort choices come from the active Gentle session and persist per chat. Manual engine fields are collapsed in Settings.

# ARISE 0.4.54 — Gentle Shell required for the main chat

The main chat verifies the extension commands for Gentle status, customization and profiles before accepting prompts. If verification fails the process is closed and ARISE directs the user to repair the integrated engine. The ARISE identity and chat-scoped permissions remain active.

# ARISE 0.4.53 — Verified Gentle Shell delegation

Local Windows delegations load the integrated Gentle Shell extensions and verify the command catalog before sending the task. The parent chat receives an error if Gentle Shell did not load.

# ARISE 0.4.52 — Workspace attachments

Copy files from the desktop composer into the active workspace, review their paths before sending, and keep drafts separate when switching chats.

# ARISE 0.4.51 — Gentle Shell 4.9.0

The integrated agent uses Gentle Shell 4.9.0, Pi 1.5.2 and Gentle AI 4.6.0.

# ARISE 0.4.50 — Resident desktop event connection

A dedicated reader delivers engine events over a reusable authenticated loopback socket. Ordinary prompts reuse known session state. See [Desktop transport](../docs/DESKTOP-TRANSPORT.md).

# ARISE 0.4.49 — Recoverable desktop chat

Read a full reply as it streams, browse older messages by page, and recover the active chat after the event buffer rolls over. Chat capabilities show the permission mode, profile and job count reported by compatible Gentle hosts. See [Desktop chat](../docs/DESKTOP-CHAT.md).

# ARISE 0.4.48 — Progressive chat and optional voice controls

Read-only Desktop RPC discovery, progressive reply preview, local vocabulary, conservative name correction, opt-in sentence playback and private transcription. See docs/VOICE-PREVIEW.md.

# ARISE 0.4.47 — Local voice performance

- Add bounded, content-free local voice stage timings in runtime status.
- Trim only excess endpoint silence while preserving the configured pause.
- Reuse the Gonzalo bridge across response chunks and close it on exit.
- Document future voice and cross-chat phases in docs/VOICE-ROADMAP.md.
- Desktop microphone/provider latency acceptance is still required.

# ARISE 0.4.46 — Engine, web tools and voice recognition

- Bundle Gentle Shell 4.8.0, Pi 1.5.2, Gentle AI 4.5.0, Engram 3.7.2 and gentle-engram 0.8.0.
- Bundle pi-web-access 0.48.0 in the private agent home for web search and extraction.
- Keep the upstream 4.8 registry implementation instead of applying the 4.7 backport.
- Show a submitted message before waiting for a cold engine startup.
- Separate Whisper transcription language from UI language; offer automatic detection.
- Recognize greeting-scoped variants of Arise without changing ordinary “a raíz” text.
- Document the JARVIS-inspired behavior targets and remaining acoustic/latency validation.
