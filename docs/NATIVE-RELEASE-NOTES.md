# 0.4.45 — live memory connection and skill registry fixes

- Apply private/shared local memory from Agent settings without restarting the desktop application. Preserve the chat and report validation or connection failures.
- Backport reviewed Gentle Shell registry fixes, preserving tracked-file protections and handling missing Git in verified non-Git workspaces.
- Discover existing Windows Git for the isolated child and recognize the real host home.
- Apply the same fixes to the separate WEG edition.

# ARISE Preview 0.4.44

Stable Core 0.4.42 is published separately after its gates pass. This Preview is published as `native-v0.4.44`; neither channel implies private desktop tools or offline models are bundled.

Built and verified on QA; ARISE Preview is the public prerelease name.

This release adds opt-in Antigravity connection from Agent settings with the pinned bridge 1.3.1. See [Antigravity setup and limits](ANTIGRAVITY.md). It retains private/shared local Engram selection. See [Voice, study and language](VOICE-STUDY-LANGUAGE.md) for behavior and limitations.

Six architecture-specific installers, with the owned Gentle Shell 4.7.0 engine:

| Operating system | x64 | ARM64 |
| --- | --- | --- |
| Windows 11 | `windows-x64-Setup.exe` | `windows-arm64-Setup.exe` |
| Ubuntu 24.04 | `linux-x64.deb` | `linux-arm64.deb` |
| macOS 15 | `macos-x64.pkg` | `macos-arm64.pkg` |

Each filename begins with `ARISE-0.4.44-`. Download the matching installer and
its `.sha256` file. Installation, installed engine/UI, same-version reinstall,
uninstall and preservation checks must pass on all six native runners before
this prerelease is published. Per-target JSON reports accompany the installers.

These core previews include Pi, Gentle Shell, Gentle AI and Engram. Private
ScreenView/InputControl/Forge servers and offline speech models are not included.
Physical microphone, speakers and desktop control are not certified by CI.
Windows ARM64 and macOS do not include Vosk wake listening.

Windows installers are unsigned. macOS applications are ad-hoc signed; the PKG
is unsigned and not notarized. Security policy may block installation. Do not
disable operating-system security. Developer signing remains a release gate.

Close ARISE before installing. Installers use separate preview application
locations but retain the standard ARISE user profile. Back up that profile;
do not run stable and preview against it simultaneously. Uninstalling preserves
settings, accounts and memory. Updates currently require downloading and running
the matching installer; the Windows production updater is disabled in previews.

See [native installation and removal instructions](https://github.com/Maicololiveras/Arise/blob/main/docs/NATIVE-DISTRIBUTIONS.md).
The complete, user-validated Windows x64 release remains
[0.4.37](https://github.com/Maicololiveras/Arise/releases/tag/v0.4.37).
