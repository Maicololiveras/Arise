# Engram ownership and external-installation recovery

The integrated engine ships Engram 3.7.0 and gentle-engram 0.7.0. Its private
session-owned server uses ARISE's memory directory. See
[owned runtime](owned-gentle-runtime.md) before changing binaries or stores.
The npm integration package and native Engram executable are different components.

## Historical incident: QA 0.4.28

On MAIX's PC, Gentle Shell 4.5.0/Pi 1.4.0 worked through the npm launcher while
ARISE had an empty `gentle_agent_home`. Selecting the launcher's official home
restored chat. Engram 3.6.0 existed under LocalAppData but was absent from ARISE's
inherited PATH. This was evidence for that PC, not a universal cause.

External-mode recovery detects the real package, resolves `bin.pi` from metadata
and retains the official home. Windows Engram reinstall downloads an official
release and its checksums, reads only `engram.exe`, verifies the hash and version,
then adopts the new explicit path. It does not change global PATH, delete memory,
kill unrelated servers, bypass TLS/ACL checks or force npm updates.

Stop active tasks first. A Gentle update and a separate Engram update are not a
single atomic transaction. An invalid explicit binary must fail rather than
silently selecting another installation. Restart the affected engine and run
`mem_doctor` with the intended project; a successful download alone is not proof
that the memory provider uses it.

## Preserve historical memory and sync state

Project/directory mismatches, unclassified session ownership and old `cloud:*`
targets are metadata/synchronization findings, not proof of lost local memories.
Do not reassign records by session name, delete pending sync state or confirm
mutations merely to clear diagnostics. A broad Git root such as the user home
can misidentify a workspace project.

Identify the effective store, stop its owner for a consistent full backup,
verify a copy and inspect the exact repair plan before changing the original.
A future cloud server in Coolify remains deferred. Preserve retained cloud state
until a conservative migration has been verified. Updating Engram does not fix
an independent InputControl configuration/capture failure.
