# Gentle Shell registry backport

Source: Gentleman-Programming/gentle-shell commit `c991fb4c3` (main, reviewed 2026-11-13), `extensions/skill-registry.ts`, MIT license included.

Backported fixes include disk-only atomic registry writes, session-local resolved skills (#3089), stale-session notification protection (#3127), and reduced fallback polling. Only this extension is replaced; the rest of Gentle Shell stays pinned to npm 4.7.0. Its existing local helper imports are available in that package.

ARISE-specific changes:

- If Git is missing, allow automatic writes only after proving that no ancestor contains `.git` metadata and no explicit Git directory override is set. A broken, inaccessible or actual repository remains fail-closed.
- Recognize the real host home when the owned runtime has an isolated HOME, retaining the broad-home repository guard.
- Include Git failure codes in diagnostics. Do not force refresh, delete `.git`, add `safe.directory=*`, or overwrite tracked registry files.

`scripts/patch_gentle.py` checks the target package/version and the reviewed source SHA-256 before applying it to build-owned dependencies. Windows Complete, native Core and integration tests apply the same patch. External Gentle Shell installations are never modified. Review/remove the backport when upgrading the pinned upstream package.
