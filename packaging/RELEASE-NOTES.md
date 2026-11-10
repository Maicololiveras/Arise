# ARISE 0.4.43 Preview

- Allow up to 90 seconds for macOS cold engine startup; the panel waits for the bounded handshake instead of timing out first. Readiness gates remain mandatory.
- Choose ARISE private memory (default) or an already-running shared local Engram server in Settings, independently of the engine.
- Validate the upstream compatibility contract before saving, reconnecting, or creating delegated tasks; reject inherited Engram overrides explicitly.
- Adopt a shared server over a pinned connection without spawning, stopping, migrating or merging its database. Connection loss requires explicit reconnection.
- Show configured, verifying, connected and error states with Spanish/English labels. Connected requires successful memory-tool evidence.
- Preserve the saved private executable for switching back; it is not injected in shared mode.

Shared mode supports the default local endpoint only. It requires a compatible server already running and does not configure Engram Cloud or copy memories. See docs/shared-memory.md.

---

# ARISE 0.4.42 QA

- Add immediate, exact Spanish/English voice controls for speech interruption, microphone mute, task cancellation and graceful application shutdown.
- Separate ending voice from stopping tasks in the chat panel. Starting a new voice conversation explicitly unmutes the microphone.
- Add opt-in, chat-owned study sessions with bounded screenshot intervals, pause/resume/end controls and read-only model turns. Stop, chat changes and shutdown invalidate scheduled observations.
- Add a persistent Spanish/English interface selector that refreshes existing windows and new dialogs without changing drafts, credentials, paths or history content. Future model turns follow the selected language.
- Replace the legacy Android download panel with guided private web-app setup for Android, iPhone and iPad, including read-only Tailscale/authenticator readiness checks.
- Keep current Stable/Preview public feeds and immutable downloads unchanged while QA verification runs. Physical audio, screen capture and phone acceptance are still required.

# ARISE 0.4.41 Preview

Installable mobile web app for iPhone, iPad and Android through the private PC URL. No app-store account, native signing key or store fee is required for this distribution. Pairing and TOTP remain mandatory. No offline task queue, service worker or chat cache is introduced. Native mobile releases are deferred; desktop stable publication remains enabled.

# ARISE 0.4.40 Preview

Stable Core installers now have separate identities on all six desktop targets. Android stable requires a persistent release signature. The initial iPhone/iPad companion is available as source and simulator CI; Apple device distribution is not yet published. CI also fixes UTF-8 documentation reads, Docker README inclusion, and channel-aware Start menu validation.

- Publish stable and Preview installers from main only; keep QA as a fast-forward mirror.
- Read both Windows update channels from separate, validated manifests on main.
- Identify preview installers and the application as ARISE Preview.
- Preserve immutable historical releases and user profiles. Old complete Windows QA clients require one manual Preview reinstall to migrate their legacy branch feed.
- Native core previews retain their documented platform limitations and manual updates.

# ARISE 0.4.38 Native previews

Six native core build targets: Windows, Linux and macOS on x64 and ARM64.
Private desktop MCP servers and offline models are not bundled in these previews.
Native artifacts require their own CI and physical acceptance before promotion.
Preview updates are manual; the Windows x64 feed is disabled in preview archives.
See docs/NATIVE-DISTRIBUTIONS.md for capabilities, requirements and validation.

# ARISE 0.4.37 QA

- Connect provider accounts and select chat models inside Settings using the native Pi/Gentle SDK; no terminal login is required.
- Isolate account operations behind a private renderer capability and keep credentials out of agent/chat events.
- Update the Gonzalo synthesis adapter, support system trust and explicit proxies, and provide an output-only voice test and optional Windows voice fallback.
- Prepare speech one phrase ahead for earlier playback and interruptible, ordered audio without repeating partially spoken replies.
- Configure wake phrases, the spoken acknowledgement and automatic chat opening.
- Clear chat/orb overlays before desktop tools execute, dock in a configurable corner and preserve manual orb dragging.
- Add account, voice and desktop-layout regression coverage. Physical Windows audio, real provider OAuth and hotword QA remain required.

# ARISE 0.4.36 QA

- Bundle Gentle Shell 4.7.0, Pi 1.5.0, pinned native Gentle AI 4.4.0 and Engram 3.7.0. No separate Gentle installation is required.
- Default to an ARISE-owned agent, configuration, credentials and memory store. Preserve external installations and databases; existing accounts require login in the new private environment.
- Update bundled engine paths on relocation/upgrade while preserving owned settings and authentication. Keep explicit external-engine mode for advanced use.
- Adapt Gentle 4.7 dialogs for RPC and propagate the adapted extensions to delegated agents, preserving chat authorization and cancellation.
- Stage and checksum Engram during packaging; use a private session-owned server rather than adopting an unrelated global service.
- Add isolated-runtime, upgrade and real parent/child integration checks; test the frozen Windows bundle without global Node/Gentle on PATH.

# ARISE 0.4.35 QA

- Preserve the microphone's complete default audio format instead of combining it with a separately advertised sample format.
- Distinguish stream opening, recording, model loading and transcription failures. Add a bounded local dictation/download history without audio or transcript logging.
- Separate the draft dictation microphone from the blue voice-conversation button and clarify their independent model settings.
- Document the optional npm recovery path and its validation limits.
- Unblock Linux CI by allowing only the native Windows TLS test to skip there; Windows still runs it.
- Physical dictation and clean-PC desktop control validation remain pending (#10, #7, #8). Cross-project Engram retrieval is not changed in this release.

# ARISE 0.4.34 QA

- Use Windows native certificate validation for application updates, public
  tool downloads and Python GitHub requests. Preserve certificate and hostname
  verification, HTTPS-only redirects and installer/package SHA-256 checks.
- Package the native trust-store adapter with the Windows executable.
- Show actionable guidance when a download certificate is not trusted. A proxy
  CA must already be trusted by Windows; ARISE never installs certificates or
  disables TLS verification automatically.

# ARISE 0.4.33 QA

- Check managed ScreenView, InputControl and Forge releases at startup; update
  changed packages with hash validation and rollback on activation failure.
  Private Transcription updates require existing repository access.
- Keep delegated terminals connected to their originating chat for questions,
  replies and new instructions. A completed turn no longer ends the task.
- Scroll long agent questions and delegation approvals while keeping response
  controls and Accept/Reject buttons visible.
- Preserve disabled tools, working custom MCP commands and existing permissions.
- The InputControl indicator fix has its own component release;
  ARISE can acquire it only after the corrected binary is published.

# ARISE 0.4.32 QA

- Download pinned Parakeet models/runtimes from ARISE's GitHub release for networks that block direct Hugging Face/npm access.
- Maintain an independent distribution branch with upstream sources, reviewed hashes and verification before/after upload.
- Preserve TLS and integrity checks; networks must allow GitHub and its release asset CDN.
- Retry from the microphone or use the local dictation repair action for invalid previous installs.

# ARISE 0.4.31 QA

- Click the panel microphone to record, then microphone ↑ to stop and transcribe into the draft. Review/send remains manual.
- Adapt Gentle Shell 4.5.1 Parakeet with verified component downloads and a separate worker.
- Preserve drafts, undo, cancellation and chat-generation isolation.
- Use the system default input; initial model preparation is about 670 MB plus runtime. Windows x64 requires Node 22+ and Visual C++ Runtime.
- Qt/protocol checks use simulated audio; physical capture and Spanish accuracy remain separate acceptance. Android and VPS/Coolify are unchanged.

# ARISE 0.4.30 QA

- Prepare private Tailscale Serve from Windows, with chat-pairing QR and persistent local port. Reject replacement of unrelated Serve services and do not enable Funnel.
- Add DPAPI-protected TOTP, expiry, replay rejection, persistent attempt limits, revocation and at most 30-day mobile access. Configure Tailscale-provider MFA separately.
- Android 0.2.0 QA adds QR scanning, Tailscale access and collapsed advanced-listening settings.
- Record up to 29 seconds on mobile for PC transcription into a draft; synthesize playback with an installed Windows voice. Accept up to four PNG/JPEG images.
- Explicitly resume a linked chat only when the PC is idle; protected approvals need the authenticator and do not expand agent permissions.
- VPS/Coolify, passkeys, push, document attachments and stable Android signing remain deferred.

# ARISE 0.4.29 QA

- Default the greeting name to the PC username instead of a fixed Maix value.
- Allow an override in Agent settings; an empty value restores automatic detection. Saving reconnects Pi to apply the preference.

# ARISE 0.4.28 QA

- Reinstall official stable Engram from settings, checking SHA-256 and executable version before adopting its explicit path.
- Reuse the official LocalAppData binary when inherited PATH omits it, without global PATH changes or memory deletion.
- Detect npm Gentle packages and official agent homes; resolve Pi from package metadata, including dist/bundle/cli.js.
- Keep explicit Gentle/Pi updates in the official wizard, without bypassing ACL/TLS or terminating unrelated Engram servers.
- A verified download is not proof of memory-provider selection; check mem_doctor afterward.

# ARISE 0.4.27 QA

- Android 0.1.1 QA reuses the original orb frame in launcher, setup and overlay.
- Check bounded public version metadata on opening settings or request; confirm before APK download and let Android authorize installation.
- Constrain APK links to repository releases and publish before advertising updates.
- Respect system bars. Debug signing may require reinstalling/re-pairing; no promise of in-place upgrades or absence of Play Protect warnings.

# ARISE 0.4.26 QA

- Wake an idle parent agent when a delegated terminal finishes so it can inspect/verify the public result.
- While the parent is active, queue through Pi prompt/followUp and verify receipt. Errors remain visible without automatic resend.
- Prevent duplicate notifications and wrong-chat delivery; do not reconnect stopped, switched or unauthorized jobs.
- Real Pi/Gentle with a fixture provider reproduced and verified notification behavior; physical/provider/document acceptance remained separate.

# ARISE 0.4.25 QA

- Add a QR/link for downloading the Android QA APK, without pairing secrets.
- Publish the QA APK only after tests, lint and build.
- Retain private Tailscale pairing; APK overlays do not run on iPad, which uses the web client.
- Debug signing and physical Android acceptance remain limitations.

# ARISE 0.4.24 QA

- Pin Gentle Shell 4.5.0, Pi 1.4.0 and Gentle AI 4.3.1 with the verified official installer.
- Adapt unified profiles/models while retaining upstream approvals.
- Offer the native Gentle AI TUI as an advanced external installer; preserve ARISE's working engine.
- A verified independent CLI is not automatically an ARISE RPC engine: the inspected supervisor did not forward the required context.
- Include experimental connections/reminders/mobile features with explicit setup and approval. Real external accounts/devices and affected-PC TUI installation remain separate checks.

# ARISE 0.4.23 QA

- Add a compact, searchable, scrollable session command palette.
- Match case/accent-insensitively; Enter selects, Escape closes and arrows navigate.
- Close on reload/chat switch and reject stale catalogs while retaining runtime approvals.

# ARISE 0.4.22 QA

- Realtime OpenAI/Gemini voice acknowledges accepted tasks without waiting for completion; query, correct or cancel by chat-owned ID.
- New requests do not silently steer an active task; stale results do not reach another chat.
- Preserve local voice and existing approvals; real provider/audio quality remains on-device acceptance.
- Add early version consistency checks across application, installer, bundle and release notes.

# ARISE 0.4.21 QA

- Show connection/tool-loading notices in a quiet fixed-height line below input, outside conversation history.
- Preserve full text in tooltip/accessibility without moving chat or stealing focus.
- Clear on chat switch; errors and approvals stay visibly distinct.

# ARISE 0.4.20 QA

- Pin Gentle Shell 4.3.0 and its official installer with compatible Pi 1.2.0.
- Preserve isolated/linked/custom homes, interactive RPC, approvals, chat isolation and Stop.
- Leave Gentle's session scratch/artifact lifecycle to its runtime.
- Windows CI and affected-PC installation remain separate; this does not certify resolution of entry-storage.

# ARISE 0.4.19 QA

- Compact activity and Stop controls; Alt+Q restores the last prompt without sending or overwriting a draft.
- Add explicitly approved, chat-owned Gentle terminal delegation with results/cancellation.
- Bound installer ancestry queries and guard PID cycles/reuse with shutdown diagnostics.
- Windows installer/visible-terminal acceptance is tracked separately in the historical QA record.

# ARISE 0.4.18 QA

- Scroll release notes while keeping update buttons outside the scroll area.
- Fit initial dialog size to available space with wrapping and no horizontal scroll.
- Require explicit Install; Close, Later and Escape never install.
- Validate Qt at 340×440 offscreen; native Windows acceptance remains separate.

# ARISE 0.4.17 QA

- Recover an existing official private Gentle runtime and its Node/Pi/home without invoking global pnpm.
- Reject incomplete/ambiguous installs and verify native integrity and RPC before adoption.
- Install MCP 1.x in private Transcription Python for FastMCP compatibility.
- Initial entry-storage and physical PortAudio -9996 failures are not proven fixed by discovery alone.

# ARISE 0.4.16 QA

- Transport pnpm validation via PowerShell EncodedCommand and classify I/O failures without exposing raw stderr.
- Test the real Forge Edge adapter instead of inferring availability from the legacy bridge.
- Identify PortAudio direction/code and missing transcription modules without silently changing devices or voices.
- Preserve affected-PC acceptance rather than declaring a root cause from CI.

# ARISE 0.4.15 QA

- Recognize the narrowly defined pnpm v11 junction while validating its target/ancestors; retain denial of other links and untrusted write access.
- Install tools independently so a failed Transcription package does not discard verified desktop components.
- Distinguish audio-device opening from invalid Vosk models; no silent model download or voice substitution.
- Physical affected-PC audio remained unverified.

# ARISE 0.4.14 QA

- Keep session continuity across messages and unrelated settings, with chat-scoped history and controlled shutdown.
- Expose actual capabilities and require per-chat local execution separately from desktop control.
- Create/read verified DOCX without desktop automation; templates support append-only content.
- Show bounded public tool/subagent activity without private reasoning or invented progress.
- Stop background child processes without automatic restart. Real Pi/Gentle fixtures, DOCX and Qt tests do not certify the user's physical Windows devices, production provider or WEG template.
