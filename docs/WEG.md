# WEG Assistant — identity edition

This distribution uses the official WEG PNG supplied by the repository maintainer. The source artwork is retained unchanged as `assets/weg-logo.png`. The orb and application icon fit the complete logo proportionally inside a circular surface; the logo is never cropped, redrawn or regenerated.

## Scope

Based on ARISE 0.4.45. This branch changes visible identity, colors, icons and distribution identifiers only. Agent behavior, tools, voice, memory, authorization and Antigravity integration are inherited unchanged from that baseline. Existing wake phrases remain unchanged and can be configured in Settings.

The identity is active from first launch; no theme-selection step is required. Both orb rendering selections display the official logo. No unprovided WEG font, slogan or secondary brand artwork is invented.

## Dedicated distribution

- Source branch: `weg`.
- Release tag: `weg-v0.4.45` (prerelease).
- Release: https://github.com/Maicololiveras/Arise/releases/tag/weg-v0.4.45
- Application title: **WEG Assistant**.
- Separate installer identities for Windows, Linux and macOS.
- This edition does not publish to the ARISE Stable/Preview update feeds or generated download tables. Replace WEG Core manually from its dedicated release.

| System | Architecture | Installer in the WEG release |
| --- | --- | --- |
| Windows 11 | x64 | `WEG-0.4.45-windows-x64-Setup.exe` |
| Windows 11 | ARM64 | `WEG-0.4.45-windows-arm64-Setup.exe` |
| Ubuntu 24.04 | x64 | `WEG-0.4.45-linux-x64.deb` |
| Ubuntu 24.04 | ARM64 | `WEG-0.4.45-linux-arm64.deb` |
| macOS 15 | Intel | `WEG-0.4.45-macos-x64.pkg` |
| macOS 15 | Apple Silicon | `WEG-0.4.45-macos-arm64.pkg` |

Install only from the **weg-v** release. Published filenames, installed title and orb identify WEG. Links are available only after all six native installer verification jobs pass. Checksums and verification reports accompany the installers.

## Install

Download the matching installer and its SHA-256 file from the dedicated release. On Windows, open the EXE. On Ubuntu, run `sudo apt install ./WEG-0.4.45-linux-x64.deb` (substitute `arm64` for ARM). On macOS, open the PKG matching your processor. Open **WEG Assistant** and configure your account in Settings.

This is the same Core distribution as the baseline: desktop MCP binaries and offline voice models are not bundled. Windows installers are unsigned; macOS packages are not notarized. OS microphone and screen permissions still apply. User data layout and existing authorization rules are unchanged; this is not a separate security boundary or a claim of official WEG endorsement.

## Visibility

WEG download instructions are maintained only on this branch and this document, not in ARISE's main/QA README. A release in a public GitHub repository is still publicly visible in the repository's Releases list; documentation separation does not make it private.

## 0.4.45 inherited fixes

The same live private/shared memory connection button and reviewed Gentle Shell registry fixes as ARISE Preview are included. WEG identity and release isolation remain unchanged.
