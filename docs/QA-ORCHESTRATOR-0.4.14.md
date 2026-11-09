# QA 0.4.14: execution, continuity and public activity

Historical QA record. Use [current setup](INSTALL-WINDOWS.md) and
[validation evidence](VALIDATION.md) for release status. Findings and pending
checks below describe that revision, not every later build.

Inspection found an unconditional claim that shell/write/edit were blocked even
when local execution was enabled; unrelated settings could close Pi; new chats
inherited execution authorization; late voice calls lacked complete chat-generation
checks. Gentle background children could outlive the parent's RPC abort. The
original affected Windows session log was unavailable, so these were real defects
without a claim that one uniquely caused that user's empty document.

## Resulting contracts

Actual capabilities show observed commands, Gentle verification, working folder
and local permission. Registration is not proof of provider readiness.
`documents.create_docx`/`read_docx` operate without shell/desktop: nonempty content,
reopen/compare verification, SHA-256, bounded workspace destination, no overwrite,
atomic publication and cancellation before publish. Optional templates retain
content and append; this is not advanced field filling or a verified WEG template.

Local execution is explicitly authorized per chat and does not grant desktop
control. Gentle policies remain intact. Subagent execution is blocked when local
execution is unauthorized; cross-chat/orchestrator communication remains isolated.
Gmail still requires visible approval.

Consecutive messages share process/session. Hiding the panel and unrelated
voice/appearance settings do not close Pi. Process-affecting changes may reconnect
the same session file. Chat switching cancels work, revokes desktop control,
checkpoints results and closes owned processes. Returning resumes history, not
cancelled work. If background children were delegated, Stop conservatively closes
the owned tree because inspected upstream lacked a direct cancel-all contract.
Already-written files are not undone; ambiguous external results need inspection.

Activity uses actual tool start/end, public model metadata and bounded Gentle
subagent status events. It excludes private reasoning, prompts and shell arguments.
Missing phase/model/progress stays unreported, not invented. Late old-generation
events are discarded. The compact view retains focus, size and emergency controls.

## Evidence

October 14, 2026: 176 local tests passed without skips. Real Pi/Gentle/local HTTP
covered persistent session, authorization, real children, DOCX and cancellation.
Qt 340×480 offscreen and rendered test DOCX were inspected. These did not validate
the user's WEG E3 template, production provider, physical voice/mouse or Windows DPI.

Initial Windows CI exposed font elision and a test that did not recognize
ConnectionResetError/WinError 10054 as cancellation. The display prioritized phase;
the assertion accepted EOF/reset but still failed on timeout and required observed
child processes to terminate. Production cancellation was not weakened.
