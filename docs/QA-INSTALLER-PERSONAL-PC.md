# Personal-PC installation investigation, 0.4.15–0.4.17

Historical engineering record. Version-specific results below are not current
installation instructions. Use [Windows setup](INSTALL-WINDOWS.md),
[owned runtime](owned-gentle-runtime.md) and [validation](VALIDATION.md).

The supplied bootstrap failed at `process-failed (entry-storage)`. That step
checks the JavaScript entry targeted by an existing pnpm shim. The message did
not distinguish missing file, PowerShell failure or access denial and did not
prove `acl-mask`. No ACL bypass was authorized or introduced.

Automatic tool installation originally grouped public tools with private
transcription; a transcription failure discarded prior candidates. Component
isolation and bounded import diagnostics fixed that behavior. Initial local
coverage passed 178 tests on Linux/offscreen, not on the affected Windows PC.

## 0.4.15

A real pnpm v11 junction was observed from its global node_modules entry to
`pnpm/store/v11/links/@/pnpm/<version>/<hash64>/node_modules/pnpm`. The adapter
accepted only that known LocalAppData structure, validating the destination,
ancestors and original path with existing ownership/ACL rules. Other junctions,
external/chained targets, Everyone-write access and missing files remained denied.
Windows-only tests checked those conditions without changing ACLs.

Audio opening errors were separated from missing/invalid Vosk models. This did
not establish the user's hardware cause or substitute Gonzalo.

## 0.4.16

The real entry-storage failure persisted despite junction CI passing. Predicate
transport changed to EncodedCommand and tests invoked Node → PowerShell like
production. Diagnostics classified read/missing/access/length/start/exit/timeout
without claiming an unproven root cause. Forge checked the actual Edge adapter;
transcription named missing modules; audio identified direction and PortAudio code.

## 0.4.17

Recovery probed the official private prefix, active-version marker, Node and
packages using the verified helper and native-binary policy. It avoided global
pnpm, retained known linked-home priority and rejected incomplete/ambiguous
installs. Real RPC preceded adoption; failure restored previous settings.
Transcription pinned MCP 1.x for `mcp.server.fastmcp` in its private runtime.

Local final coverage: 190 tests, 186 passed, four Windows junction skips. A clean
MCP 1.30.0 environment imported FastMCP, but that did not validate the full Windows
server. Device-opening error -9996 still required testing the real input.

CI corrections preserved production checks: run 38720302265 exposed a fixture
CRLF marker mismatch; fixtures now wrote exact Node-style LF and tested CRLF
rejection. Run 38732037480 exposed short/long TEMP-path spelling differences;
assertions used `samefile` while retaining command-argument checks. Run 38733341391
exposed shutdown before HTTP response flush; response is now written/flushed
before server shutdown, including disconnected-client cleanup.

Current integrated-engine setup supersedes these external-installation steps.
The historical investigation did not identify every missing file on rober's PC.
