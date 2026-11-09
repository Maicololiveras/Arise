# Validation evidence and release gates

Record the exact commit, target, test result and artifact. Source tests, packaged
smoke checks and physical-device acceptance establish different facts.

## Windows baseline: 0.4.37

[QA run 42624810967](https://github.com/Maicololiveras/Arise/actions/runs/42624810967)
passed native Windows tests, Docker, frozen engine/renderer, installer replacement,
offline inference and publication. The suite ran 296 tests; Docker recorded seven
explicit Windows-only skips. The user subsequently reported the installed version
working successfully. This is user acceptance of that tested setup, not a claim
that every provider/device combination or non-Windows target was exercised.

[Production run 42634680905](https://github.com/Maicololiveras/Arise/actions/runs/42634680905)
rebuilds the promoted revision with the production channel. Its status and the
published main feed are authoritative for production availability; a promotion
commit alone is not a downloadable release.

## Native preview gates

The separate native workflow builds on Windows/Linux/macOS x64 and ARM64 runners.
Python and Node architecture must match the target. A package is archived only
after real bundled Pi/Gentle connects through the frozen daemon, private memory
tools register and the Qt renderer produces an offscreen image. Reports explicitly
mark physical audio/desktop control as untested. See
[native distribution limits](NATIVE-DISTRIBUTIONS.md).

A missing native dependency, failed smoke or unavailable runner is a failed or
blocked target, never a pass inferred from another architecture. Core previews
exclude private desktop MCP bundles and offline models. Signing/notarization,
physical devices and per-target update acceptance remain separate release gates.

## Run checks

```bash
npm ci --prefix vendor --ignore-scripts
python -m pip install .
QT_QPA_PLATFORM=offscreen python scripts/test.py
cargo test --locked --manifest-path host/Cargo.toml
node --test scripts/install-gentle-native.test.mjs
```

Tests use real processes, Pi/Gentle with deterministic local HTTP, MCP fixtures,
local WebSocket providers, SQLite and Qt. They do not send real email or require
production model credentials. Intentional Windows-only skips are narrowly listed
in the runner; unrelated skips fail validation. Docker runs in CI even when the
local development environment cannot run containers.

## Historical results

- 0.4.0: [run 37973490621](https://github.com/Maicololiveras/Arise/actions/runs/37973490621),
  74 Python tests per environment, Rust Linux/Windows and installer rename tests.
  Frozen host/daemon/engine/memory/Qt/Vosk/Whisper/SAPI checks passed. Replacement
  stopped four owned children, retained chat/memory and removed obsolete code.
  Published installer: 388502656 bytes, SHA-256
  `b0e51a0dede79c031f4e15635d855663ed6d8f97c43bb23e34bad62d57d301f4`.
- 0.3.0: [run 37954993176](https://github.com/Maicololiveras/Arise/actions/runs/37954993176),
  51 Python tests per environment and native host checks. Vosk processed silence;
  Whisper imports and two SAPI voices were detected without opening a microphone.

Historical screenshots are real Qt widgets rendered offscreen on Linux. They do
not prove Windows transparency, monitor scaling or input devices. Private MCP
catalog checks require their actual packaged distributions and repository access.
No automated suite demonstrates speech accuracy, absence of echo, external-account
entitlement or a complete real desktop-control loop. Use the
[physical Windows checklist](WINDOWS-CHECK.md) and equivalent target acceptance.
