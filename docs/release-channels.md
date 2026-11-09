# Release channels and source synchronization

**Main is the single source for installers, release workflows, download links and
update manifests.** The `qa` branch is a fast-forward mirror of `main`, not an
independent publication source. The public prerelease name is **ARISE Preview**.

| Distribution | Source branch | Release tag | Update index on main |
| --- | --- | --- | --- |
| ARISE stable, complete Windows x64 | main | `vX.Y.Z` | `updates/windows.json` |
| ARISE Preview, complete Windows x64 | main | `qa-vX.Y.Z` (compatibility identifier) | `updates/windows-preview.json` |
| ARISE Preview, six native core installers | main | `native-vX.Y.Z` | Manual per-target installation |

The internal Windows preview channel remains `qa` to retain channel validation;
it is displayed as ARISE Preview. The updater always reads `ref=main`, choosing
the channel-specific filename. Stable and preview installers are never exchanged
silently. Release URLs, channel, version, asset ID, size and SHA-256 remain checked.

## Publishing

- Native previews build and publish from main only after all six target gates
  pass. The published release title and installer display name are ARISE Preview.
- Main pushes build and verify the complete Windows ARISE Preview package; a new
  version publishes after every gate passes. Existing versions are never replaced.
- To promote stable, run **ARISE verification** on **main** with
  `release_channel: stable`. Manual `preview` also publishes Preview; manual `none`
  only verifies. A push never publishes a stable release.
- Both channels build their own embedded channel and pass the complete Windows
  gates. Published versions and asset hashes are immutable; changes need a version
  bump. Never relabel an old preview executable as stable.
- Metadata publication updates the selected index and README atomically on main,
  then fast-forwards QA to that exact commit. The mirror workflow also follows
  ordinary main pushes. Divergent QA commits cause a failure, never a forced reset.

## Existing installations

Already published 0.4.37 and native 0.4.38 assets remain unchanged. Their origin
commits are preserved in main's merged history; new binaries are built from main.
Native 0.4.38 previews remain manual-update installations.

Old complete Windows QA clients read `updates/windows.json` from the QA branch.
After QA becomes an exact mirror, that historical endpoint is no longer a QA feed.
Their channel validation rejects a stable manifest rather than installing it.
Install the next complete **ARISE Preview** Windows package manually once to move
to the new preview index on main. This does not authorize deleting the user profile.
Do not use a reduced native core preview as an automatic replacement for the
complete Windows distribution.

Core previews still exclude private desktop MCP servers and offline models.
Signing/notarization and physical-device acceptance remain separate gates.
Android Preview also builds and publishes from main, retaining its legacy APK identifiers.
Existing APK versions are immutable and are not republished during branch synchronization.
Component/model repositories retain their separate distribution systems;
VPS/Coolify is deferred.

## Automatic documentation reconciliation

`release-documentation.yml` runs after successful desktop/native/Android publication
workflows, on published releases, daily for recovery, and on manual dispatch.
It reads published GitHub assets rather than assuming a build succeeded. Drafts,
incomplete uploads and releases without installer checksums are excluded.
Each product retains its own latest published version; Android and desktop versions
are independent. iOS remains explicitly unavailable until an iOS distribution and
its validation contract are implemented.

The generated published-platform table is refreshed in the root README, documentation
index, native installation guide, Android guide, update guide and this channel guide.
Native download filenames and installation commands are refreshed as well. Historical
validation reports, incident records and introduction-version references remain intact;
a newer release does not retroactively validate old tests. Add new current installation
guides to `GUIDES` in `scripts/sync_release_docs.py`.

Documentation updates are committed atomically on `main` and fast-forwarded to `qa`
under the shared release-metadata concurrency lock. A divergent QA branch fails visibly
instead of being overwritten. A repeated run is idempotent and repairs an interrupted
QA mirror update. Other development branches do not receive documentation-only merges.
