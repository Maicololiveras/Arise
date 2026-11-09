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
passed all production gates and published v0.4.37. The main feed selects the
production installer (413051665 bytes), SHA-256
`4db4e1837640f6b4d744d5a92edc59df271d387e434372cfb7846643b4b9e153`.
Its source commit is `654eeff6b3630971567912d08f6d9f4a237a0002`; it is a
main-channel rebuild, not the QA executable.

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

The six-target matrix first passed in
[run 42638622809](https://github.com/Maicololiveras/Arise/actions/runs/42638622809).
The final runtime revision `aaee782386e59e777956b049b6f954cf365510e6` also passed
all six targets in [run 42639847104](https://github.com/Maicololiveras/Arise/actions/runs/42639847104),
including capability/UI, Rust architecture and macOS trust refinements. Local
validation ran 303 tests: 296 passed and seven explicit Windows-only skips.
[PR #12](https://github.com/Maicololiveras/Arise/pull/12) remains a draft for
physical platform acceptance. Later documentation-only commits do not change
the tested runtime.

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
