# Install ARISE on Windows

<!-- arise-published-platforms:start -->
## Downloads

Choose your system and channel. Each link points to a published installer; versions can differ by platform.

| Operating system | Architecture | Stable | ARISE Preview | Installation |
| --- | --- | --- | --- | --- |
| Windows 11 | x64 | <!-- arise-windows-stable -->[Complete 0.4.37](https://github.com/Maicololiveras/Arise/releases/download/v0.4.37/ARISE-Setup.exe) · [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/v0.4.37/ARISE-Setup.exe.sha256)<!-- /arise-windows-stable --> | <!-- arise-windows-preview -->[Complete 0.4.37](https://github.com/Maicololiveras/Arise/releases/download/qa-v0.4.37/ARISE-Setup.exe) · [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/qa-v0.4.37/ARISE-Setup.exe.sha256)<!-- /arise-windows-preview --><br>[Core 0.4.39](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.39/ARISE-0.4.39-windows-x64-Setup.exe) · [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.39/ARISE-0.4.39-windows-x64-Setup.exe.sha256) | [Install →](https://github.com/Maicololiveras/Arise/blob/main/README.md#install-windows) |
| Windows 11 | ARM64 | Not released | [Core 0.4.39](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.39/ARISE-0.4.39-windows-arm64-Setup.exe) · [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.39/ARISE-0.4.39-windows-arm64-Setup.exe.sha256) | [Install →](https://github.com/Maicololiveras/Arise/blob/main/README.md#install-windows) |
| Linux · Ubuntu 24.04 | x64 | Not released | [Core 0.4.39](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.39/ARISE-0.4.39-linux-x64.deb) · [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.39/ARISE-0.4.39-linux-x64.deb.sha256) | [Install →](https://github.com/Maicololiveras/Arise/blob/main/README.md#install-linux) |
| Linux · Ubuntu 24.04 | ARM64 | Not released | [Core 0.4.39](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.39/ARISE-0.4.39-linux-arm64.deb) · [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.39/ARISE-0.4.39-linux-arm64.deb.sha256) | [Install →](https://github.com/Maicololiveras/Arise/blob/main/README.md#install-linux) |
| macOS 15 | Intel x64 | Not released | [Core 0.4.39](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.39/ARISE-0.4.39-macos-x64.pkg) · [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.39/ARISE-0.4.39-macos-x64.pkg.sha256) | [Install →](https://github.com/Maicololiveras/Arise/blob/main/README.md#install-macos) |
| macOS 15 | Apple Silicon ARM64 | Not released | [Core 0.4.39](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.39/ARISE-0.4.39-macos-arm64.pkg) · [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/native-v0.4.39/ARISE-0.4.39-macos-arm64.pkg.sha256) | [Install →](https://github.com/Maicololiveras/Arise/blob/main/README.md#install-macos) |
| Android 8+ | Mobile companion | Not released | [0.2.0-qa](https://github.com/Maicololiveras/Arise/releases/download/android-qa-v0.2.0-qa/ARISE-Android-QA.apk) · [SHA-256](https://github.com/Maicololiveras/Arise/releases/download/android-qa-v0.2.0-qa/ARISE-Android-QA.apk.sha256) | [Install →](https://github.com/Maicololiveras/Arise/blob/main/README.md#install-android) |
| iOS / iPadOS | Mobile companion | Not released | Not released | [Install →](https://github.com/Maicololiveras/Arise/blob/main/README.md#install-ios) |

**Stable** is the established release channel. **ARISE Preview** is for testing newer builds.

**Complete** and **Core** are different packages: Core previews include the integrated agent engine, but exclude private desktop MCP servers and offline speech models. A higher Core version does not imply feature parity with Complete.

“Not released” means no installer is currently published for that platform and channel. iOS is separate from macOS.

<!-- arise-published-platforms:end -->


The established installer targets Windows x64. For Windows ARM64 use the
separate [native preview guide](NATIVE-DISTRIBUTIONS.md); do not assume the x64
complete package is a native ARM64 distribution.

## Install or upgrade

Download the installer from the [production release](https://github.com/Maicololiveras/Arise/releases/latest)
or an explicitly selected QA release. Run `ARISE-Setup.exe` as your normal user.
To upgrade, select the existing installation directory. The installer stops
owned processes and preserves application data.

The optional `ARISE-Windows-Complete.zip` includes the installer and offline
model pack. Extract everything and run `Configurar ARISE.cmd`; keep its files
together. A normal update does not require downloading the model pack again.

ARISE includes Node, Pi, Gentle Shell 4.7.0, native Gentle AI and Engram. The
complete Windows package also supplies its Python/media tooling. Users do not
need a global Gentle, npm or Go installation. Git/Bash and project-specific
compilers may still be needed for coding tasks.

## First run

1. Keep the default integrated engine.
2. Open **Settings > Agent > Connect account and choose model**. Complete the
   provider's browser/device flow or enter a supported API key, then select a model.
3. Send a text message. A selected model does not prove account entitlement.
4. In Voice settings, select devices and test output. Configure dictation and
   conversation separately; see [voice](VOICE-MODELS.md).
5. Inspect real tool capabilities. Download/repair supported managed tools if
   needed; authorize local execution and desktop control separately per chat.
6. Test Stop before using desktop automation for substantive work.

No terminal login is required for agent accounts. A chat subscription does not
supply a paid realtime voice API key. Existing global Pi authentication is not
copied into ARISE's private agent.

## Optional private repository access

Private Transcription or source-based tool provisioning requires a GitHub account
with access to those repositories. Public managed tool packages use their own
published manifests. GitHub access is independent of the model account.

If CLI authentication is needed, the Windows package includes `gh`:

```powershell
$gh = Join-Path $env:LOCALAPPDATA 'Programs\ARISE\bundle\gh\gh.exe'
& $gh auth login --hostname github.com --git-protocol https --web
& $gh auth status --hostname github.com
```

Adjust the installation path if necessary. Never share tokens. Repository
access and an MCP catalog are not permission to capture or control the desktop.

## Recovery

Restart ARISE after changing PATH. Prefer repairing the integrated installation
before selecting an external engine. External mode must be selected explicitly;
its package directory, launcher and agent home are distinct paths. See
[npm recovery](GENTLE-NPM-RECOVERY.md) and [Engram recovery](ENGRAM-RECOVERY-QA.md).

For certificate failures, have the network administrator repair the trusted CA
chain. Do not disable TLS verification. For PortAudio errors, test the selected
input/output and Windows microphone permissions; installing an agent package
cannot repair an unavailable device.

[Update behavior](UPDATES.md) · [Windows acceptance checklist](WINDOWS-CHECK.md)
