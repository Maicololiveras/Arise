# QA 0.4.19: delegated terminals and installer shutdown

Historical QA record. Use [current setup](INSTALL-WINDOWS.md) and
[validation evidence](VALIDATION.md) for release status. Findings and pending
checks below describe that revision, not every later build.

The compact activity area retained a reachable Stop control. Alt+Q restored the
last user message without sending or replacing a nonempty draft.

`terminal.delegate` required visible approval, local execution authorization and
a valid Gentle environment. Each task had its own session, at most three active
terminals, chat-scoped list/cancel and results. The child did not receive desktop
bridge authority. Chat switch, Stop and exit cancelled managed terminals. Restart
did not reconnect/replay jobs. A directory was not a filesystem sandbox and a
model's final text was not verification. Later bidirectional delegation supersedes
the original single-turn lifecycle; see the current delegation guide.

The 0.4.18 installer had timed out after 600 seconds while stopping processes;
the log did not identify the blocked operation. Inspection found ancestry walks
without PID-cycle detection. The fix bounded CIM queries, rejected cycles and
newer reused parents, ran noninteractively and recorded installer-stop.log.
Failure still blocked replacement; it did not bypass process checks.

Evidence: real Qt at 340×480 on Linux; chat isolation, consent, process cancellation
and missing child bridge token; real Pi/Gentle PTY with a local SSE provider and
public result/exit 0. These were not a Windows console or external-provider test.
Windows installer replacement, visible console and physical emergency shortcut
remained acceptance gates at that revision.
