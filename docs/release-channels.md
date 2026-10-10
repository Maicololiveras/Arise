# ARISE release channels

- `qa`: integration and Windows acceptance testing. All new work is delivered here first.
- `main`: production. Promote a reviewed and tested QA revision through a pull request; do not promote automatically.

Each Windows build embeds `arise_app/resources/update-channel.json` before freezing the executable. CI sets `ARISE_BUILD_CHANNEL=qa` for QA and `main` for production. This is independent of the Gentle stable/main selection. Installing a different ARISE channel explicitly changes the channel; user settings and conversations remain in place.

On startup ARISE reads `updates/windows.json` from its own branch. It checks the version, channel, release URL, asset size and SHA-256, then shows release notes and asks whether to install. QA cannot accept production manifests or vice versa. Updates close ARISE processes and run the installer over the current installation.

Pushes to `qa` and `main` run Docker, native Windows tests, frozen runtime/installer smoke checks and offline model inference before publication. QA releases use `qa-vX.Y.Z` and are prereleases; production uses `vX.Y.Z`. Versions are immutable: bump the application version before publishing a subsequent update within a channel.

The release contains `ARISE-Setup.exe` and `ARISE-Windows-Complete.zip`. The complete ZIP includes the models and the one-click setup launcher. Successful publication updates only the originating branch's manifest with `[skip ci]`.

Acceptance: install the QA ZIP; confirm chat/login, new chat, ScreenView, InputControl and Forge on a real Windows desktop; test updating an older QA installation and preserving data. Only then promote QA to main. Production publication happens only after main passes the same build gates.
