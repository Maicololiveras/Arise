# Native distribution previews

Windows x64 0.4.37 is the user-validated desktop baseline. Version 0.4.38 adds
build recipes for six native core previews. A recipe is not a published or
validated download: use an artifact only after its native CI job succeeds.
Production Windows installation remains documented in [INSTALL-WINDOWS.md](INSTALL-WINDOWS.md).

| Target | Native build runner | Artifact | Minimum baseline |
| --- | --- | --- | --- |
| Windows x64 | windows-latest | Portable ZIP | Windows 11 x64 |
| Windows ARM64 | windows-11-arm | Portable ZIP | Windows 11 ARM64 |
| Linux x64 | ubuntu-24.04 | tar.gz | Ubuntu 24.04, glibc 2.39 |
| Linux ARM64 | ubuntu-24.04-arm | tar.gz | Ubuntu 24.04, glibc 2.39 |
| macOS x64 | macos-15-intel | ZIP containing ARISE.app | macOS 15 |
| macOS ARM64 | macos-15 | ZIP containing ARISE.app | macOS 15 |

The target must match the computer. ARM64 packages are compiled on ARM64 runners,
not x64 packages relabeled for emulation. Node and Python architecture are checked
before packaging. Bundled manifests reject adoption on a different target.

## Included and excluded

All successful previews contain the Qt UI, Rust process host, Node 24.21.0,
Pi 1.5.0, Gentle Shell 4.7.0, verified Gentle AI 4.4.0, Engram 3.7.0,
gentle-engram 0.7.0 and the online Gonzalo adapter. Engine packages and memory
are owned by ARISE; a global Gentle installation is unnecessary.

These are **core previews**, not equivalents of the complete Windows installer.
Private ScreenView/InputControl/Forge MCP servers and offline speech models are
not bundled. Compatible external MCP servers can be configured explicitly.
Desktop control, screen recording, native global shortcuts and microphone/device
behavior need separate acceptance on each target. Wayland may restrict capture
and input injection; macOS requires system permissions for those operations.

Vosk 0.3.45 is available in Windows x64 and Linux builds, but requires a separate
compatible model. Its pinned release has no macOS or Windows ARM64 wheel. Wake
listening is unavailable there; do not enable it expecting the Windows behavior.
Other dictation engines require their own supported runtime. Gonzalo is online;
its model is not embedded. Miniaudio decodes the returned audio in the preview.
Windows system-voice fallback is Windows-only.

## Install and run

Download the artifact from the successful **Native distribution previews** job
for your target. Extract the outer Actions artifact, verify the included SHA-256
against the application archive, then extract the entire application archive.
Keep the executable, internal libraries and bundle together.

- Windows: run `ARISE/ARISE.exe`.
- Linux: install `libportaudio2`, `libegl1`, `libopengl0`, `libxcb-cursor0` and
  `libxkbcommon-x11-0` using your distribution's package manager, then run
  `./ARISE/ARISE` in a graphical session.
- macOS: extract the ZIP and open `ARISE.app`. Preview apps are ad-hoc signed,
  not Developer ID signed or notarized. Enterprise policy or Gatekeeper may
  block them. Do not disable system security globally to run a preview.

Connect a provider in **Settings > Agent > Connect account and choose model**.
No Pi terminal is required. Account credentials belong to the private SDK store;
this is not an additional encrypted vault. Windows DPAPI-backed integrations
are not automatically portable to other systems.

## Data and updates

| System | Default data directory |
| --- | --- |
| Windows | `%LOCALAPPDATA%\ARISE-Orb` |
| Linux | `$XDG_DATA_HOME/ARISE-Orb`, default `~/.local/share/ARISE-Orb` |
| macOS | `~/Library/Application Support/ARISE-Orb` |

Use `--data-dir` for an isolated test profile. Close ARISE before backing up or
replacing an installation. Preserve the data directory; do not copy credentials
between users or operating systems.

Preview archives currently require manual replacement. Their embedded marker
disables the Windows installer update feed, preventing a Linux, macOS or ARM64
preview from downloading the production x64 installer. Automatic per-target
updates and signed/notarized installers remain release gates, not completed features.

## Build and acceptance

Run `python -m pip install '.[build,portable]'`, then
`python scripts/build_native.py --target <target>` on a matching native machine
with Node 24.21.0, Go 1.25.14 and Rust 1.90.0. The workflow supplies these tools.
The official Gentle installer verifies native binary provenance; Engram archives
are pinned by SHA-256. TLS checks remain enabled.

Every archive is created only after the frozen daemon starts, real bundled
Pi/Gentle connects, private memory tools register and Qt renders an offscreen
image. The smoke report explicitly records that physical audio and desktop
control were not tested. Inspect the report and CI logs before distribution.
Promote each target only after account login, audible speech, microphone,
permissions, stop/cancel, relocation and upgrade/data-preservation tests pass
on a real computer. Keep unsupported capabilities visible in release notes.
