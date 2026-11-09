# Native distribution previews

<!-- arise-published-platforms:start -->
## Published downloads (automatic)

Versions below refer to published installers, not unreleased source changes.

| Platform / channel | Published version | Downloads |
| --- | --- | --- |
| Windows complete / stable | 0.4.37 | [Release and checksums](https://github.com/Maicololiveras/Arise/releases/tag/v0.4.37) |
| Windows complete / ARISE Preview | 0.4.37 | [Release and checksums](https://github.com/Maicololiveras/Arise/releases/tag/qa-v0.4.37) |
| Windows, Linux and macOS / x64 and ARM64 Preview | 0.4.39 | [Release and checksums](https://github.com/Maicololiveras/Arise/releases/tag/native-v0.4.39) |
| Android / ARISE Preview | 0.2.0-qa | [Release and checksums](https://github.com/Maicololiveras/Arise/releases/tag/android-qa-v0.2.0-qa) |
| iOS | Not published | No iOS installer is currently distributed. |

<!-- arise-published-platforms:end -->


Windows x64 0.4.37 is the user-validated desktop baseline. Version 0.4.39 provides
six published native core preview installers, each tested on its own OS and CPU.
Production Windows installation remains documented in [INSTALL-WINDOWS.md](INSTALL-WINDOWS.md).

| Target | Native build runner | Artifact | Minimum baseline |
| --- | --- | --- | --- |
| Windows x64 | windows-latest | EXE installer + portable ZIP | Windows 11 x64 |
| Windows ARM64 | windows-11-arm | EXE installer + portable ZIP | Windows 11 ARM64 |
| Linux x64 | ubuntu-24.04 | DEB installer + tar.gz | Ubuntu 24.04, glibc 2.39 |
| Linux ARM64 | ubuntu-24.04-arm | DEB installer + tar.gz | Ubuntu 24.04, glibc 2.39 |
| macOS x64 | macos-15-intel | PKG installer + app ZIP | macOS 15 |
| macOS ARM64 | macos-15 | PKG installer + app ZIP | macOS 15 |

The target must match the computer. ARM64 packages are compiled on ARM64 runners,
not x64 packages relabeled for emulation. Node and Python architecture are checked
before packaging. Bundled manifests reject adoption on a different target.

All six installers passed installation, installed engine/UI startup, same-version
reinstallation, removal and user-data preservation in
[run 42655321028](https://github.com/Maicololiveras/Arise/actions/runs/42663055949).
Download the permanent [0.4.39 native prerelease assets](https://github.com/Maicololiveras/Arise/releases/tag/native-v0.4.39),
including checksums and per-target JSON evidence. Portable archives and offscreen
screenshots remain available as Actions artifacts with 14-day retention.

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

The [native prerelease](https://github.com/Maicololiveras/Arise/releases/tag/native-v0.4.39)
contains all six verified installers. Future releases remain blocked until
every native installer job passes.
Download the installer matching both your OS and CPU and its `.sha256` sidecar.
Verify using `Get-FileHash` on Windows, `sha256sum` on Linux or `shasum -a 256`
on macOS before opening it.

- Windows: open `ARISE-0.4.39-windows-<arch>-Setup.exe`. It installs per user at
  `%LOCALAPPDATA%\Programs\ARISE-Native-Preview` and adds Start menu shortcuts.
  Remove it through Windows Installed apps. Administrator rights are not required.
- Ubuntu 24.04: run `sudo apt install ./ARISE-0.4.39-linux-<arch>.deb`.
  APT installs required system libraries. Open **ARISE Preview** from the
  application menu or run `arise-preview`. The app resides in
  `/opt/arise-native-preview`. Remove with `sudo apt remove arise-native-preview`.
  These DEBs are not certified for older Ubuntu, Alpine, Fedora or other distros.
- macOS 15: open `ARISE-0.4.39-macos-<arch>.pkg` and follow Installer. It installs
  `/Applications/ARISE Preview.app` and requires administrator authorization.
  Close ARISE and move that application to Trash to uninstall. Optionally remove
  its receipt with `sudo pkgutil --forget com.praxisgenai.arise.preview`.

Windows installers are unsigned. macOS apps are ad-hoc signed, and the PKG is
unsigned and not notarized. Enterprise policy or Gatekeeper may block them.
Do not disable system security globally. Developer signing is still required
before a frictionless production release.

Portable archives remain available as workflow artifacts. Extract the whole
archive, keeping internal libraries and bundle together. Run `ARISE/ARISE.exe`,
`./ARISE/ARISE` or the macOS application as appropriate.

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

Preview updates require manually running the matching installer again (or replacing a portable archive). The preview uses a separate application location but shares the standard user profile; never run stable and preview concurrently against that profile. Uninstallers preserve user data. Their embedded marker
disables the Windows installer update feed, preventing a Linux, macOS or ARM64
preview from downloading the production x64 installer. Automatic per-target
updates and signed/notarized installers remain release gates, not completed features.

## Build and acceptance

Run `python -m pip install '.[build,portable]'`, then
`python scripts/build_native.py --target <target>` on a matching native machine
with Node 24.21.0, Go 1.25.14 and Rust 1.90.0. The workflow supplies these tools. Run `python scripts/build_installers.py --target <target>` afterward to create the installer. Inno Setup is required on Windows; Linux uses dpkg-deb and macOS uses pkgbuild/productbuild. The `--verify-install` option is for disposable CI runners: it installs, tests, reinstalls and uninstalls the package and checks a profile sentinel. It refuses to overwrite an existing installation. This tests same-version replacement, not every migration from older releases.
The official Gentle installer verifies native binary provenance; Engram archives
are pinned by SHA-256. TLS checks remain enabled.

Every archive is created only after the frozen daemon starts, real bundled
Pi/Gentle connects, private memory tools register and Qt renders an offscreen
image. The smoke report explicitly records that physical audio and desktop
control were not tested. Inspect the report and CI logs before distribution.
Promote each target only after account login, audible speech, microphone,
permissions, stop/cancel, relocation and upgrade/data-preservation tests pass
on a real computer. Keep unsupported capabilities visible in release notes.
