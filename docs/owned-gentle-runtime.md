# ARISE-owned Gentle runtime (QA 0.4.36)

ARISE now ships Gentle Shell 4.7.0 and Pi 1.5.0. Node, pinned native
Gentle AI 4.4.0, Engram 3.7.0 and gentle-engram 0.7.0 travel in the application
bundle. Users do not install Gentle Shell, Node, npm or Go separately to use
this engine. Git and other project-specific build tools remain optional external
dependencies for tasks that need them.

## First launch and upgrades

1. Install or extract the complete ARISE package and launch it.
2. ARISE validates its bundled engine and selects it automatically.
3. Open **Settings → Agent → Open Pi for /login** and authenticate your provider
   in ARISE's private agent. Select the provider/model in ARISE if necessary.
4. Use the chat. Local execution and desktop control still require their normal
   per-chat permissions. The integrated engine does not enable YOLO mode.

The release manifest pins compatible Pi and Gentle versions. Engine upgrades
arrive through ARISE updates, not an independent global npm install. Configuration
repair revalidates the installed bundle; it does not silently download a different
Gentle release. Moving/upgrading the application refreshes owned package paths
while retaining its agent settings, models and auth file.

Existing external Gentle installations, authentication and Engram databases are
not modified or copied. Consequently, the new private agent requires its own
login and does not automatically display memories from a previous global store.
Memory import is a separate operation, not an implicit migration during startup.

## Owned state

The default Windows data root is `%LOCALAPPDATA%\ARISE-Orb`:

| Relative path | Purpose |
| --- | --- |
| `engine/agent` | Pi authentication, model configuration and package settings |
| `engine/gentle-ai` | Gentle AI configuration |
| `engine/home` | Engine HOME, AppData, XDG directories and temporary files |
| `engine/memory` | Private Engram store |
| `engine/runtime.json` | Previously selected bundled package paths and versions |
| `engine/selection-backup.json` | Original engine selection before first adoption |

Engram starts in session-owned mode using an ephemeral local endpoint. It does
not adopt or terminate a global Engram server. Stopping the engine terminates its
owned child process. An explicit `ENGRAM_STARTUP_POLICY=deny` is respected.
Global Git identity remains available through an explicit `GIT_CONFIG_GLOBAL`;
inherited Gentle development overrides and Node injection flags are discarded.
This is configuration separation, **not an OS security sandbox**.

## Advanced external mode

Select **External installation (advanced)** in Agent settings, detect or enter
that installation, and save. This explicitly opts out of bundled selection.
Choose integrated mode again to return to ARISE's private environment. Never
copy authentication or database files between running engines. The selection
backup contains paths only and can help recover the former external setup.

## Implementation and verification

The design follows Gentle Dot's owned agent/configuration and staged native
runtime, using Gentle Shell's upstream `buildPiInvocation` launch contract.
ARISE supplies RPC-compatible UI adapters and propagates those extension paths
to delegated children through Gentle's child-package injection contract.
Interactive login uses the upstream extensions. User-added agent packages remain
intact; only previously tracked bundled entries are replaced during upgrades.

Engram is downloaded only at build time from its official release, checked
against a pinned SHA-256, and version-checked on Windows. Missing or mismatched
engine artifacts fail explicitly instead of falling back to a random global
installation. Standard TLS validation remains enabled.

Automated checks cover adoption, external opt-out, configuration preservation,
chat preference isolation, real Pi/Gentle RPC, local permission checks, delegated
children and cancellation. Windows CI exercises the shipped host and frozen
engine with a restricted PATH and invalid inherited Gentle overrides. Physical
clean-PC acceptance remains a separate QA check.

References:
- [Gentle Shell v4.7.0](https://github.com/Gentleman-Programming/gentle-shell/tree/v4.7.0)
- [Gentle Dot daemon](https://github.com/Gentleman-Programming/gentle-dot/tree/b141d30/packages/daemon)
- [Engram v3.7.0](https://github.com/Gentleman-Programming/engram/releases/tag/v3.7.0)
