# ARISE Assistant

![ARISE Assistant animated orb](docs/identity/arise-assistant.gif)

ARISE is a desktop assistant with a movable orb, a compact chat panel, voice,
and a resident engine. It runs Gentle Shell inside its own environment: users
do not need to install Pi, Gentle Shell, Node or Go separately.

![Native ARISE panel](docs/panel.png)

## Install and connect

Use the published Windows installer for the established desktop experience.
Six native core preview installers are also available for Windows, Ubuntu and
macOS on x64 and ARM64. Read their capability limits before choosing a preview.

<!-- arise-downloads:start -->
- **Production 0.4.37:** [Windows installer — 413 MB](https://github.com/Maicololiveras/Arise/releases/download/v0.4.37/ARISE-Setup.exe) · [release and available assets](https://github.com/Maicololiveras/Arise/releases/tag/v0.4.37).
- **QA 0.4.37:** [Windows installer — 413 MB](https://github.com/Maicololiveras/Arise/releases/download/qa-v0.4.37/ARISE-Setup.exe) · [release and available assets](https://github.com/Maicololiveras/Arise/releases/tag/qa-v0.4.37).
<!-- arise-downloads:end -->

### Native installers — 0.4.38 preview

Choose the installer that matches your operating system and CPU. Each includes
ARISE's own Gentle Shell 4.7.0, Pi, Node, Gentle AI and Engram; no separate
Gentle installation is required. Sizes below are approximate decimal MB.

#### Windows 11

| Architecture | Installer | Size | Integrity |
| --- | --- | --- | --- |
| x64 (Intel / AMD) | [Download EXE](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.38/ARISE-0.4.38-windows-x64-Setup.exe) | 178 MB | [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.38/ARISE-0.4.38-windows-x64-Setup.exe.sha256) |
| ARM64 | [Download EXE](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.38/ARISE-0.4.38-windows-arm64-Setup.exe) | 145 MB | [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.38/ARISE-0.4.38-windows-arm64-Setup.exe.sha256) |

Run the EXE and follow Setup. It installs per user and adds a Start menu shortcut.
Remove it through **Installed apps**. Administrator rights are not required.

#### Linux — Ubuntu 24.04

| Architecture | Installer | Size | Integrity |
| --- | --- | --- | --- |
| x64 (amd64) | [Download DEB](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.38/ARISE-0.4.38-linux-x64.deb) | 199 MB | [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.38/ARISE-0.4.38-linux-x64.deb.sha256) |
| ARM64 (aarch64) | [Download DEB](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.38/ARISE-0.4.38-linux-arm64.deb) | 173 MB | [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.38/ARISE-0.4.38-linux-arm64.deb.sha256) |

Install with `sudo apt install ./ARISE-0.4.38-linux-<arch>.deb`, replacing
`<arch>` with `x64` or `arm64`. Open **ARISE Native Preview** from the application
menu. Remove with `sudo apt remove arise-native-preview`. These DEBs target
Ubuntu 24.04 (glibc 2.39); other Linux distributions are not certified.

#### macOS 15

| Architecture | Installer | Size | Integrity |
| --- | --- | --- | --- |
| x64 (Intel) | [Download PKG](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.38/ARISE-0.4.38-macos-x64.pkg) | 169 MB | [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.38/ARISE-0.4.38-macos-x64.pkg.sha256) |
| ARM64 (Apple Silicon) | [Download PKG](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.38/ARISE-0.4.38-macos-arm64.pkg) | 160 MB | [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.38/ARISE-0.4.38-macos-arm64.pkg.sha256) |

Open the PKG and follow Installer. It requires administrator authorization and
installs `/Applications/ARISE Preview.app`. Close the app and move it to Trash
to remove it.

All six installers passed native installation, engine/UI startup, same-version
reinstallation, removal and profile-preservation checks. See the
[release and reports](https://github.com/Maicololiveras/Arise/releases/tag/native-v0.4.38)
and [successful native CI run](https://github.com/Maicololiveras/Arise/actions/runs/42655321028).

**Preview limits:** private desktop MCP servers and offline speech models are
not bundled; physical microphone, speakers and desktop control still need device
acceptance. Windows and PKG installers are unsigned; macOS apps are ad-hoc signed
and not notarized. Do not disable OS security to install them. Vosk wake listening
is unavailable on macOS and Windows ARM64.

Updates are manual: close ARISE and run the newer matching installer. Preview
and stable use separate application locations but share the standard user
profile; back it up and never run both against that profile simultaneously.
Uninstalling preserves settings, accounts and memory. The complete Windows x64
production release above remains the established desktop option.

[Detailed native installation guide](https://github.com/Maicololiveras/Arise/blob/feat/platform-distributions/docs/NATIVE-DISTRIBUTIONS.md)

### First run

1. Install your selected package. For the complete Windows distribution, you
   may instead extract its ZIP and run `Configurar ARISE.cmd` to prepare the
   optional offline model pack.
2. Open **Settings > Agent > Connect account and choose model**. Authenticate
   in the provider's browser flow or enter an API key in the masked field.
   Account selection and model selection stay in ARISE; no terminal is needed.
3. Test a text message. In Voice settings, select input/output devices and use
   the output-only voice test before starting a conversation.
4. Enable local execution or desktop control only for tasks that need them.
   These are separate permissions. Stop revokes control and cancels owned work.

[Windows installation](docs/INSTALL-WINDOWS.md) ·
[Windows/Linux/macOS x64 and ARM64 previews](docs/NATIVE-DISTRIBUTIONS.md) ·
[Complete documentation index](docs/README.md)

## Included engine

| Component | Pinned version |
| --- | --- |
| Gentle Shell | 4.7.0 |
| Pi | 1.5.0 |
| Gentle AI | 4.4.0 |
| Engram | 3.7.0 |
| gentle-engram | 0.7.0 |
| Bundled Node | 24.21.0 |

The engine owns its agent settings, SDK credentials and memory store. Updates
refresh packaged paths while preserving that state. Existing global accounts
and databases are not silently imported. Advanced users may explicitly choose
an external installation. See [owned runtime](docs/owned-gentle-runtime.md).

## Daily use

- Drag the orb to move it. Click to toggle chat; double-click opens it. Enter
  sends a message and Shift+Enter inserts a line.
- The dictation microphone records on the first click and transcribes on the
  second. Text enters the draft for review; it is never sent automatically.
  The waveform control starts a separate voice conversation.
- Gonzalo uses an online synthesis service. ARISE includes its adapter, not a
  redistributable offline Gonzalo model. Fluent playback prepares the next
  phrase while speaking; optional Windows fallback is visibly reported.
- Wake listening is opt-in. Configure phrases, acknowledgement and whether to
  open the panel. A closed microphone cannot detect a wake phrase.
- Desktop operations hide the chat and temporarily hide/dock the orb before
  capture or input. This does not grant permission to control the computer.
- Projects and chats retain separate sessions and local-execution preferences.
  Delegated tasks can ask questions and receive new instructions in the same
  originating chat. Completion still requires verification of the result.
- Gentle commands are discovered from the running engine. Native dialogs keep
  long content scrollable and response controls reachable.

[Accounts, speech and desktop layout](docs/accounts-voice-desktop-qa.md) ·
[Dictation](docs/DICTATION-PARAKEET-QA.md) ·
[Delegation](docs/delegated-terminal-communication.md)

## Distribution and safety boundaries

The stable Windows x64 installer and native core previews have different
capabilities. Preview installers do not include private desktop MCP servers or
offline model packs, and currently update by manually running the matching installer. macOS previews
are not notarized. Consult the platform guide before downloading.

Production follows `main`; Windows QA follows `qa`. Each installer accepts only
its channel's version, release URL, size and SHA-256. Tool distributions have
separate manifests. TLS verification remains enabled, including behind proxies.
A checksum is not an independent code-signing identity.

Pi SDK account storage is separate from Windows DPAPI-backed connection secrets.
Private engine directories are configuration separation, not an OS sandbox.
Never publish `auth.json`, `daemon.json`, pairing codes or credential files.
External actions require their applicable approval; ambiguous delivery is not
retried automatically.

Android/Tailscale remains a controlled companion feature. The PC must remain
available. VPS/Coolify deployment is deferred; it is not part of this release.

## Develop and verify

```bash
npm ci --prefix vendor --ignore-scripts
python -m pip install .
QT_QPA_PLATFORM=offscreen python scripts/test.py
cargo test --locked --manifest-path host/Cargo.toml
```

Windows complete build:

```powershell
.\scripts\Build-Windows.ps1 -WithTools -ReposRoot C:\Repos
```

The source directory must contain `screenview-mcp`, `inputcontrol-mcp`,
`transcripcion-ia` and `forge-mcp`. CI needs the corresponding repository access
in `ARISE_COMPONENTS_TOKEN`; ChatGPT's GitHub connection does not supply it to
Actions. Native preview build instructions are in the platform guide.

Docker runs the integration suite with `docker compose run --build --rm tests`.
Tests use real Pi/Gentle with local provider fixtures, real processes and Qt;
they do not certify a physical microphone, desktop permissions or external
accounts. See [validation evidence](docs/VALIDATION.md) and
[release channels](docs/release-channels.md).

The orb reuses the ARISE renderer identity from
[praxisgenai-harness](https://github.com/Maicololiveras/praxisgenai-harness/blob/main/docs/ARISE-ORB.md).
JetBrains Mono retains its OFL license. Bundled dependencies retain their
respective licenses and attribution.
