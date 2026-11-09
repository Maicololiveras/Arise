# Historical upstream prerequisite investigation

Historical engineering record. Version-specific results below are not current
installation instructions. Use [Windows setup](INSTALL-WINDOWS.md),
[owned runtime](owned-gentle-runtime.md) and [validation](VALIDATION.md).

Inspected Gentle main commit `a6c539aced3d68bf673ea48b77302120f1488934`
in the context of ARISE 0.4.8 and the Gentle 4.0.0 Windows installer.
The user reported missing dependencies on a second PC; this was not a complete
clean-VM reproduction with a new log.

`installer-preflight.mjs` inventoried Node, pnpm, Pi, Shell, Gentle AI, Go,
globalBin and setup, but did not inventory Git/Bash or Windows tar. Node/pnpm
and Go already had acquisition mechanisms; the finding did not claim all
automatic prerequisite installation was absent. `main-channel.mjs` extracted
source with `System32\tar.exe`, not a Git clone.

Desired behavior: show requirements, paths, versions and capabilities; acquire
missing requirements through the official consent flow; reuse compatible tools;
refresh PATH and verify again. A failed download, missing package manager or
cancelled elevation must not report readiness. Tests should include clean Windows
and stale PATH, not only pre-provisioned CI runners.

ARISE added prerequisite handling as mitigation. Current users should prefer
its [owned engine](owned-gentle-runtime.md); external repair guidance is in
[GENTLE-PREREQUISITES.md](GENTLE-PREREQUISITES.md). No new upstream issue is claimed
as filed by this documentation update.
