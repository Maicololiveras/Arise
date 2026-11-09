# QA 0.4.20: Gentle Shell 4.3 integration

Historical QA record. Use [current setup](INSTALL-WINDOWS.md) and
[validation evidence](VALIDATION.md) for release status. Findings and pending
checks below describe that revision, not every later build.

The historical build pinned gentle-pi 4.3.0 with Pi 1.2.0. Official Windows
installer SHA-256:
`b8d8087fe7ad74e7a2dab9121d09dd9fe5fef3ba6498b59d2fe07f701ae80f36`.
Upstream pinned Gentle AI 4.2.0, provider contract 1.4.0 and capabilities/v2.6.
Native integrity checks and ACL rules were retained; no development override.

RPC adapters preserved structure checks and original handlers. The official
launcher selected isolated, linked or custom homes without silently switching a
configured environment. Interactive RPC confirmations stayed enabled, without
YOLO. Gentle owned scratch/session temporary files and artifact cleanup; ARISE
kept documents in the chat workspace and discovered real commands, including
`gentle:scratch`.

Real-package wrapper and RPC tests covered home modes, session continuity,
profiles/models, subagents, DOCX, memory and cancellation using a controlled
provider. Windows CI/affected-PC installation remained separate. These results
did not certify resolution of entry-storage or every TUI command/provider.
