# Runtime readiness and recovery contracts

Historical engineering record. Version-specific results below are not current
installation instructions. Use [Windows setup](INSTALL-WINDOWS.md),
[owned runtime](owned-gentle-runtime.md) and [validation](VALIDATION.md).

The original report included Pi exits, `codegraph: write EPIPE`, tool-installation
errors and an unavailable local dialogue server. These remain independent until
logs establish a relationship; Gmail OAuth configuration does not explain Pi exit.

Pi retains bounded stderr internally and exposes recognized categories/exit code,
not arbitrary stderr in chat. A failure pauses reconnects for 30 seconds; saving
corrected settings allows an immediate retry without replaying tasks. Repeated
voice errors are deduplicated. Local-server readiness can recover without an
application restart.

Embedded Python installs declared build backends before source dependencies
because its `_pth` does not accept pip's isolated-build PYTHONPATH. Diagnostics
distinguish TLS, dependency, import and connection failures. Managed component
installs are independent; one failed transcription install must not discard
working desktop tools.

A configured local model server must bind loopback and remain in the foreground.
The daemon waits up to 60 seconds for a nonempty model catalog and stops only
its owned process. An already-running external server is reused, never killed.
An empty launch-command list keeps external-server mode. Credentials do not
belong in command arguments. Catalog readiness is not inference/tool-call quality.

The reviewed praxisgenai motor SDK had routing/retry/health but did not register
generation implementations in its gRPC server. Reflection alone was insufficient,
and ARISE expects OpenAI-compatible HTTP models/chat/tool calls. No automatic SDK
replacement was introduced. The inspected Dictto flow used OpenAI Whisper and
`small.pt`; transcription is separate from the conversational model.

Historical 0.4.2 recovered missing bundled paths even after onboarding. 0.4.3
validated official installation ownership before adoption and prevented silent
replacement by a global Pi. Current integrated mode owns its environment from
first launch; external installations remain explicit. See the owned-runtime guide.

Fixtures use real subprocesses/local HTTP but do not reproduce every user's MCP
configuration or microphone. No unsupported claim that codegraph caused the
original failure, no silent MCP disabling and no bypass of integrity checks.
