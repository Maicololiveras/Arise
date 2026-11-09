# QA 0.4.35: open issue review

Historical version-specific record. Current setup is documented in
[INSTALL-WINDOWS.md](INSTALL-WINDOWS.md); platform previews are described in
[NATIVE-DISTRIBUTIONS.md](NATIVE-DISTRIBUTIONS.md).

## Delivered changes

- **#11:** Added `GENTLE-NPM-RECOVERY.md`, linked from both Windows setup guides.
  It separates npm installation, launcher startup, detection and RPC validation,
  records audited package constraints, and does not claim a verified `--link`
  procedure or a clean-PC npm installation matrix.
- **#10 (partial):** Preserve the microphone's full default format tuple. A
  separately advertised float format does not prove support at that default
  rate/channel count. Distinguish device opening from stream failures and expose
  separate model-loading/transcription errors. This fixes a format-selection
  defect; the reported hardware failure is not yet confirmed resolved.
- **#10 (partial):** The chat menu's dictation history records model/runtime
  attempts, destination root, bounded progress, completion, cancellation and
  sanitized error codes. The local JSON retains at most 100 events and coalesces
  progress. It stores no audio, drafts, transcripts or native stderr. This is
  Parakeet history, not a unified history of all voice providers.
- **#10 (partial):** Gray dictation microphone on the left; blue waveform button
  on the right starts the existing voice-conversation service. Dictation places
  text in the draft only. The conversation button is disabled while dictation
  owns the microphone. Settings explain that Parakeet uses the system default
  input and does not use the conversation's Whisper/Vosk settings.
- **QA publication:** 0.4.34's Docker job passed its tests but rejected the
  Windows-only certificate-store skip. The runner now permits that exact test
  and reason on non-Windows only. It still rejects unrelated unexpected skips.

## Existing InputControl fix (#8)

The public manifest now points to
`herramientas-inputcontrol-v0.2.1-0cc432d59ba5` from InputControl master.
Archive SHA-256: `4e011966adeea05d82e0961ad47d71861f23259336c4b043dab422014a72fcc2`.
The frozen overlay self-launches rather than requiring an external Python.
The native Windows indicator smoke test passed in the component CI; it is not
an observe/action/verification/revocation test on the affected user's desktop.
Keep the issue open for that remaining acceptance evidence.

## Remaining work

- **#3:** macOS/Linux/mobile roadmap. Automated companion coverage does not
  certify native applications, distribution or physical mobile-to-PC control.
  VPS/Coolify remains deferred.
- **#7:** Clean/second-PC installation and the complete desktop loop without
  historical OpenCode configuration need a sanitized Windows report.
- **#8:** Validate the published executable on the affected PC, with a visible
  indicator and an innocuous action followed by verification and revocation.
- **#10:** Validate real Windows dictation and conversation separately. Do not
  treat a fake audio stream or an independent WinMM capture as application proof.
  Review all-provider download history and project-scoped Engram retrieval.

Gentle's `assets/orchestrator-memory.md` and `extensions/gentle-ai.ts` instruct
resume via `mem_context`, project/feature-scoped `mem_search`, full observations,
and reconciliation against current files. ARISE loads Gentle's extensions but
has no separately validated proactive cross-project retrieval contract. This
release does not add global memory search, remap projects, or alter old memories.
A future implementation must resolve the selected project's identity, reject
ambiguous home-directory Git roots and test project switches and stale records.

## Validation

Worker/session tests use simulated native audio and recognizers; Qt tests use
real subprocesses with protocol fixtures. They cover format retention, distinct
opening/stream errors, draft-only insertion, cancellation, microphone ownership,
and persistent history without private contents. Manual offscreen UI inspection
checks that the two audio controls remain visible at a 420-pixel panel width.
These checks do not certify a physical microphone, speech accuracy or Windows
permissions. Native build and installer results belong to the QA workflow for
the published commit.
