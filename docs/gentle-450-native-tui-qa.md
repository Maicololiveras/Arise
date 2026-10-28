# Gentle Shell 4.5.0 and native TUI installation — QA

## Versions are separate

- ARISE's normal bundled integration: `gentle-pi@4.5.0` and Pi `1.4.0`, pinned
  in vendor/package.json and package-lock.json. Shell requires Pi >=1.2.0.
- Its native Gentle AI pin is **4.3.1**. A Shell version is not a native version.
- Official Windows wizard: 4.5.0 ZIP, SHA256
  `46b3008e3cac37d317b6c17ec663bfa002023ac12a4d147c53e189098b1dfa5e`.
- The native TUI's Stable composition is controlled by Gentle AI, not ARISE's
  npm pin. The report records the version the installed Shell actually returns;
  do not assume that selecting Stable there means Shell 4.5.0.

## Normal integration

The existing Configure Gentle action remains available and reuses a detected
installation first. Updating the bundle does not force an existing user-managed
Gentle installation to upgrade. The wizard downloads have fixed integrity and
retain upstream confirmations. The storage diagnostic adapter now preserves the
4.5 upstream `prerequisiteProcessCause` in addition to ARISE's detailed checks.

The launcher integration is tested against the real 4.5 package for isolated,
linked and custom homes, with the RPC arguments and interactive-host flag.
The 4.5 unified profiles/model screen has a separate RPC adapter. It uses the
upstream store/action loop for profile creation, selection, saving, session use
and guarded global defaults. Model efforts follow the live catalog when known;
unknown metadata is disclosed. Editing all subagents does not silently change
the orchestrator. The old `/gentle:models` command is no longer registered by 4.5;
model editing now lives inside `/gentle:profiles`, matching upstream.
The visual terminal tabs are represented as native selection dialogs, not copied
terminal rendering. The terminal remains available for operations outside this
native subset. A new version must pass structural adapter checks before use.

## Alternative native TUI

Settings > **Alternative: install from Gentle AI TUI · QA**:

1. Read the limitation and explicitly choose to continue.
2. Choose the bundled, officially verified native binary or explicitly select
   an installed `gentle-ai.exe` stable 4.3.1+. Cancel at either picker does nothing.
3. ARISE opens the binary's main TUI in a real separate console, as an ordinary
   non-elevated user. Select Gentle Shell and review its destination, profile,
   channel and plan; confirm in Gentle itself. No `--confirm` value is invented.
4. For this first integration use the TUI's standard destination:
   `%LOCALAPPDATA%\gentle-shell\install`. Custom targets are not auto-discovered.
5. Finish and exit the TUI so ARISE can check its exit and the installed target.
   A zero exit alone is NOT success. A missing target, mismatched supervisor hash,
   refused owned launch or missing version response is a failure.
6. ARISE checks `supervisor.exe shell launch TARGET gentle-shell --version` and
   writes a bounded diagnostic to ARISE's `installers/gentle-native-*/result.json`.
   It does not redirect the TUI's screen to a log or capture passwords.

If the native binary is not installed, use the new complete QA bundle (whose
build installs Gentle AI through its official source-verifying installer), or
install it using the official documented Go route and select that executable:

```powershell
go install github.com/gentleman-programming/gentle-ai/v4/cmd/gentle-ai@v4.3.1
```

This route requires a suitable Go toolchain. The upstream 4.3.1 release does NOT
provide an official Windows executable ZIP; ARISE must not invent a download
URL or install an unverified third-party Windows binary.

## Why native installation is not automatically adopted

The v4.3.1 Windows supervisor constructs a sanitized environment and does not
forward ARISE_URL, ARISE_TOKEN, ARISE_CODE_ENABLED, session identifiers or provider
credentials. ARISE's extension needs that context to apply per-chat permissions
and connect its bridge. Directly starting the private Node to recover it would
skip the native supervisor's checks. This implementation does neither that nor
changes the supervisor/ACLs/settings to make the checks pass.

The result explicitly says `connected: false` even when `launcher_verified` is
true. It preserves ARISE's existing configuration/connection. A future native
host bridge must support explicit, scoped context transmission through a
supported upstream interface before this can become a complete ARISE engine.
It must test RPC events, tools, authorizations, stop and chat isolation.

The normal wizard remains the usable ARISE integration path. This alternative
lets the user test whether native installation succeeds on PCs where bootstrap
failed, without calling an independent Shell installation a working ARISE chat.

## Validation and pending checks

Automated tests cover version refusal, selected executable validation, missing
files, modified supervisor, refused launch, fresh-console argv (including spaces
and metacharacters), no bridge token inheritance and no engine/config mutation.
The real 4.5 installer ZIP is downloaded, SHA256-checked and adapted during tests
of build preparation. Python and JavaScript syntax are checked.

Still requires a real Windows 11 x64 test: visible TUI, user cancellation,
installation from a clean PC, privilege/ACL refusals, launcher verification and
comparison of the diagnostic with a previously failing PC. A Linux unit test or
Windows CI build is not that acceptance test. Never claim this fixes the prior
ACL/pnpm failures until that exact computer succeeds.

References checked at 2026-10-28:
- https://github.com/Gentleman-Programming/gentle-shell/releases/tag/v4.5.0
- https://github.com/Gentleman-Programming/gentle-ai/releases/tag/v4.3.1
- https://github.com/Gentleman-Programming/gentle-ai/blob/v4.3.1/internal/shellinstaller/user_install_windows.go
- https://github.com/Gentleman-Programming/gentle-ai/blob/v4.3.1/internal/shellinstaller/user_launch_windows.go

Validation record: 232 tests executed, 226 passed and 6 Windows-dependent checks
skipped on this Linux host. The real Pi 1.4 process exercised profile creation,
session application, routing save and local commands without extra model calls.
Qt settings rendered at 760x650 and the native-installer button dispatched to its
handler. The official signed Linux Gentle AI 4.3.1 binary installed and returned
`gentle-ai 4.3.1`; this does not qualify Windows source builds or native TUI use.
