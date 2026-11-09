# Selective component downloads

Windows Settings can download/repair Forge, ScreenView and InputControl
individually or together, using published manifests from ARISE's `herramientas`
branch. Private Transcription remains a separate authenticated operation.
A missing/unpublished manifest is a recoverable error, not a successful install.

Model downloads include supported Spanish Vosk, Whisper, Piper and Qwen/llama.cpp
packages. Each uses pinned version/hash metadata, safe archive handling and a
new destination. Model/catalog checks precede configuration changes; failure
restores the previous selection. Unselected components remain unchanged.
Partial downloads are not resumed. Installing Vosk does not replace an explicitly
selected Whisper model. Piper does not require the Forge bridge.

Tool repositories publish their binaries separately, with a narrowly scoped
`TOOLS_PUBLISH_TOKEN` when needed. An ARISE merge does not publish another repo's
binary. Existing public Forge packages may differ from source-based packages;
the bundled Gonzalo adapter has its own runtime.

These download recipes are Windows-oriented. Native core previews must not be
assumed to contain or install equivalent desktop tools. Verify target/architecture
support and the actual catalog before adoption; see
[native distributions](NATIVE-DISTRIBUTIONS.md) and [managed updates](tool-updates.md).

Regression tests cover selection, corrupt downloads, origin/path checks,
rollback, retained components and Qt actions. Offscreen tests do not validate
desktop operations by the downloaded executable.
