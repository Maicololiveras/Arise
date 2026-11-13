# Private and shared local memory — 0.4.45 Preview

Settings > Agent > Memory selects **ARISE private memory** (default) or **Shared local Engram server**. Engine and account selection stay independent.

For shared mode, start your compatible Engram server using its existing installation, then select shared memory and press **Apply and connect memory**. The button applies only the selected memory mode and private binary path, verifies compatibility, and reconnects the internal agent without closing ARISE/WEG or deleting the chat. Other unsaved settings are not applied. Switch back to private memory with the same button. A busy agent rejects the change until its task ends. ARISE validates before changing configuration or creating delegated-task files. A failed preflight preserves the old configuration and connection. If startup fails after a successful preflight, the explicit selection remains saved, Error is shown and the button can retry. Connected is only shown after a memory tool succeeds; opening a transport alone is not proof.

The saved private executable remains stored for switching back, but shared mode does not inject or automatically discover an executable. Explicit inherited ENGRAM_BIN, ENGRAM_URL, ENGRAM_DATA_DIR, ENGRAM_PORT, ENGRAM_SOCKET, ENGRAM_DATABASE_URL, ENGRAM_SERVER_MODE, ENGRAM_HTTP_TOKEN, or ENGRAM_STARTUP_POLICY values are rejected. Remove conflicting overrides from ARISE's launch environment and reopen it; do not delete databases.

## Evidence and ownership

The actual adapter imports Gentle Shell's native engramProbeAllowed, isReadyCompatibility and classifyEngramStartup contract. Only a ready, explicitly reusable server at 127.0.0.1:7437 can be adopted. Neither a matching version nor /health alone suffices.

Preflight is not an adoption guarantee: the child repeats validation on its own persistent connection before loading Pi. Compatibility and instance/runtime identity are checked before and after each memory HTTP request on that same connection. A closed connection cannot reconnect to another listener; missing, changed or incompatible servers fail closed. A heartbeat checks idle sessions every five seconds. A server internally losing readiness during a write cannot be rolled back by ARISE; the response is rejected and the session requires reconnection.

The explicit verified URL selects gentle-engram's non-spawning transport, preserving its runtime-contract checks. ARISE does not start, stop, replace, migrate, import or merge the shared server/database. Shutting down closes only ARISE's client sockets. Shared mode does not change project scopes or authorize cross-project retrieval. ARISE's separate explicit local notes feature is unchanged.

## Status and recovery

- **Configured**: saved selection, not proof of a provider connection.
- **Verifying**: adapter verified transport; memory-tool success is still unconfirmed.
- **Connected**: a memory tool completed successfully in this Pi session.
- **Error**: validation, memory operation or heartbeat failed. Errors remain sticky until reconnection.

Labels and help switch between Spanish and English. Private mode retains existing behavior; no shared connection claim is made. If the server closes idle connections, shared mode fails safely and requires reconnection. Authenticated/custom endpoints and Cloud are not supported by this selector.

## Verification

Regression tests use temporary application state and a synthetic loopback server, never real memories or credentials. The six initial policy tests ran against the pre-change stub and failed (11 assertions and 2 errors); they then passed. Tests exercise native contract rejection, the actual ARISE adapter, final composed environments, unchanged private behavior, configuration preservation, reconnection, rejected delegation without files, tool-evidence status, server identity changes and external-server lifecycle. Physical desktop acceptance remains separate from automated verification.
