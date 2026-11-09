# Release channels and promotion

| Stream | Purpose | Publication |
| --- | --- | --- |
| main | User-accepted production baseline | Windows `vX.Y.Z`, production feed |
| qa | Windows integration and acceptance | `qa-vX.Y.Z` prerelease, QA feed |
| feat/platform-distributions | Native core portability work | Successful native CI artifacts |
| herramientas | Managed desktop-tool manifests | Component-owned releases |
| distribution/parakeet-v3 | Pinned dictation mirror | Immutable model/runtime assets |

Production promotion is explicit after review and acceptance. The user-validated
0.4.37 revision was promoted to main, preserving the old production feed until
the new main-channel executable passes publication gates. QA binaries are not
relabelled as production. Main and QA publication rebuild and verify their own
embedded channel. Subsequent binary changes require a new version.

Windows checks Docker, native tests, frozen engine/renderer, installation over a
running instance and offline model inference before publishing. `ARISE-Setup.exe`
and the complete ZIP have different contents; consult the release inventory.
Successful publication updates the originating feed and both README download
sections atomically per branch, with conflict checks and no forced ref updates.

Each Windows installation follows its embedded channel. Switching channels is an
explicit installer action; it is independent of external Gentle stable/main.
Native previews embed target identity and do not use the Windows x64 feed.
Their manual replacement, signing limits and separate physical acceptance are
explained in [NATIVE-DISTRIBUTIONS.md](NATIVE-DISTRIBUTIONS.md).

Never publish a failed target or infer ARM64 acceptance from x64. Android and
component release workflows are separate. VPS/Coolify remains deferred.
