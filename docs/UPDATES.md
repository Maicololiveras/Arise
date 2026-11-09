# Application and component updates

Stable Windows reads `main/updates/windows.json`; ARISE Preview Windows reads
`main/updates/windows-preview.json`. Both are published from main; QA mirrors main. The embedded build channel controls selection, independently
of any external Gentle channel. A QA installer never accepts a production feed
or vice versa. Native core previews currently require manual replacement and
never consult the Windows x64 installer feed.

The publisher waits for Docker, native Windows tests, frozen runtime, installer
replacement and offline model checks. It publishes an immutable versioned
release, then updates its channel index and download links on main and fast-forwards QA. A subsequent
binary requires a new version. The production promotion of user-validated
0.4.37 rebuilds on main instead of relabeling a QA executable.

The updater validates semantic version, channel, official release URL, asset ID,
size and SHA-256. Downloads use HTTPS and preserve certificate/hostname checks.
A temporary external launcher closes the UI/daemon, waits for session persistence
and replaces the installed program. Process identification includes PID and
creation time; it does not kill every Node process on the computer. Failure to
stop owned processes blocks replacement.

Managed code and libraries are replaced; chats, settings, credentials, memory
and data-directory tool installs are preserved. Back up the data directory with
ARISE closed before a manual migration. Versions before the updater require a
manual installer upgrade.

Old complete Windows QA clients used a branch-specific endpoint. Install the
next complete ARISE Preview package manually once to migrate to the index on main.
Old clients reject the stable manifest rather than crossing channels. Existing
native core previews still update manually; they are not replacements for the
complete Windows package. See [channel migration](release-channels.md).

## Credentials and proxies

Private GitHub access uses a configured credential or existing authenticated
GitHub CLI session. Credentials do not enter release descriptors, command
arguments or logs. Authorization is removed on asset-host redirects. Windows
uses its native trust store; an organization proxy CA must already be trusted.
ARISE does not install certificates or disable verification automatically.

SHA-256 detects a mismatch with repository metadata; it is not Authenticode,
Developer ID signing or an independent signature over the update channel.

## Separate component lifecycles

Managed ScreenView, InputControl and Forge use public manifests on `herramientas`.
Transcription source updates need repository access. Each update stages a new
runtime and verifies its MCP catalog before adoption; failures roll back its
selection. Custom commands and disabled tools remain untouched.

Bundled Gentle/Pi/Engram versions are updated with ARISE. An external installation
is an explicit advanced choice. Model downloads and Android updates have their
own feeds and acceptance gates. Merging ARISE does not publish a pending fix in
another repository. See [tool updates](tool-updates.md) and
[release channels](release-channels.md).
