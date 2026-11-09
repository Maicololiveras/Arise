# Stable distributions

Stable publication is explicit. Update `releases/stable.json` on `main` to request
new desktop binaries, or manually run **ARISE stable distributions**. The request
version must match the application version. The coordinator calls reusable workflows
at its own source commit; it does not relabel existing Preview assets. QA remains
an exact source mirror of main. The two release channels remain distinct.

| Package | Stable identity | Publication requirement |
| --- | --- | --- |
| Windows Complete x64 | `vVERSION`, `ARISE-Setup.exe` | Full Windows gates, private component access and offline validation |
| Windows Core x64 / ARM64 | `native-stable-vVERSION`, `ARISE-Native` folder | Six-target native acceptance |
| Linux Core x64 / ARM64 | `native-stable-vVERSION`, `arise-native` DEB, `arise` command | Six-target native acceptance |
| macOS Core Intel / Apple Silicon | `native-stable-vVERSION`, `ARISE Core.app` | Six-target native acceptance |
| Android | `android-vVERSION`, `com.praxis.arise` | Tests, release lint and persistent release signature |
| iPhone / iPad | Not published | Apple Developer membership, signing, device validation and Apple distribution |

Core excludes private desktop MCP servers and offline speech models. Its release
channel does not imply those features are bundled. Native packages use manual
updates on both channels, including Windows Core; they must never consume the
Complete x64 Windows updater. Stable and Preview have distinct install identities
but share desktop user profiles: back up first and never run both simultaneously.
Desktop signing/notarization is unchanged: Windows installers are unsigned and
macOS apps are ad-hoc signed, not notarized. Do not disable OS security.

## Android signing setup

The stable job intentionally fails before building when these repository secrets
are missing: `ANDROID_KEYSTORE_BASE64`, `ANDROID_STORE_PASSWORD`,
`ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`. Configure them in GitHub Settings >
Secrets and variables > Actions. Never paste their values into an issue, README or
chat. Use a persistent private release keystore, retain an offline backup, and use
the same key for every update. The workflow creates a temporary runner keystore
and deletes it in an always-run cleanup step. Debug signing is never a fallback.

Stable builds create a signed APK for direct installation and AAB for later Play
Console submission. The workflow publishes GitHub assets only; it does not publish
to Google Play. Stable uses a different application ID from Preview, so users pair
again rather than installing an incompatible signature over the Preview app.

## iPhone and iPad

See [iOS companion](IOS-COMPANION.md). Simulator artifacts are development builds,
not IPA installers and not a stable release. TestFlight/App Store publication is
blocked until the maintainer has Apple Developer membership and signing configured.

## Documentation and failure recovery

The documentation reconciler runs after the coordinator completes even if one
platform failed, and advertises only complete published releases with checksums.
A failed Android signing job does not hide successfully published desktop releases.
Existing version tags are immutable. Correct binary changes with a new version;
rerun failed jobs for transient infrastructure errors. A release channel is never
inferred from the name of a source branch other than canonical main.
