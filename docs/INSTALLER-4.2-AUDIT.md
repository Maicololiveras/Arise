# ARISE 0.4.10 / Gentle 4.2 installer audit

Historical engineering record. Version-specific results below are not current
installation instructions. Use [Windows setup](INSTALL-WINDOWS.md),
[owned runtime](owned-gentle-runtime.md) and [validation](VALIDATION.md).

Reviewed October 13, 2026 against official Gentle v4.2.0. Windows installer
SHA-256: `352bf1971c00beb555a97279d59c2ea2946e6b261c446d9b3fe787bd6689a1bb`.

The build pinned Pi 1.2.0/Gentle 4.2.0, Node 24.21.0 and npm 11.19.0. Pi's floor
was read from package compatibility metadata before RPC. Profile/model/agent/
usage/change/history adapters were exercised with real packages. Bootstrap
retained upstream ownership/ACL checks, verified acquisition and its USERPROFILE
fallback rather than rewriting permissions.

The official installer result identified its Node, Pi, version and agent home.
ARISE verified package/bin containment, native resolution and real `gentle:status`
before adoption, rolling back failed candidates. Known linked launchers retained
their home; arbitrary custom launchers were not executed. PNPM_HOME was respected.

The Windows delivery included the native application/host, runtime libraries,
Vosk and media/Python/CLI tooling. Larger Whisper/Qwen/llama.cpp/Piper models used
the offline pack or selective downloads. Private MCP inclusion depended on
repository access, recorded in the installation inventory. Public manifests were
pending at the time; this historical finding is not their current status.

The orb SVG generated the executable/installer icon and shared application ID.
CI separated protocol tests and model preparation, then combined verified
artifacts for offline inference and complete-ZIP creation. Old executable reuse
was removed. Existing memory was neither migrated nor deleted; global servers
remained their owner's responsibility. Local fixtures did not prove a final
Windows installation or user authentication.
