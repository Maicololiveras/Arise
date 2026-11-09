# Delegated terminal communication

A delegated terminal belongs to its originating ARISE chat. Local execution must be enabled and the delegation must be explicitly approved. It does not inherit ARISE screen-control permissions.

## Questions and instructions

- The child calls `arise_ask_user` when it needs a decision. ARISE displays the question with a response field and cancellation button. The reply returns to the same waiting tool call.
- The parent uses `terminal.send` with the ID returned by `terminal.delegate` and a `text` value. This answers a pending question or queues a new instruction for that terminal. Instructions retain submission order; active turns receive steering and idle turns receive follow-up input.
- Ending an agent turn does not finish the delegation. A waiting terminal remains available. The child calls `arise_finish` with `completed` or `failed` and a summary only when it can report a final outcome. Process errors remain failures.
- `terminal.list` exposes public results and status within the originating chat. Queue acceptance is not confirmation of execution or completion.

Stop, chat changes, revoked local execution, and stale agent generations prevent further delivery. Restarted ARISE instances do not reconnect or replay old jobs. Messages are bounded and written atomically to a per-task local mailbox. This is not a security boundary against another process running as the same operating-system user.

Answers do not grant additional permissions. Native Gentle tool approval prompts remain subject to Gentle's controls; they are not automatically approved or replaced by this question channel. A child must use `arise_ask_user` for questions it wants ARISE to relay.

## Dialog layout

Agent questions and delegation approvals use a bounded, resizable dialog. Long descriptions scroll; the response controls and Accept/Reject buttons remain outside the scrolling content. Escape cancels. Confirmation defaults to rejection.

## Validation and release

Tests cover chat and generation isolation, question/reply delivery, ordered steering, explicit completion, cancellation, queue limits, and dialog controls at 340 × 360 pixels. Run:

```sh
python -m pytest tests/test_terminal_tasks.py tests/test_task_dialog.py tests/test_update_dialog.py tests/test_assistant.py tests/test_chat_capabilities.py tests/test_connections_companion.py -q
```

The Windows frozen InputControl indicator fix for issue #8 is maintained in `Maicololiveras/inputcontrol-mcp` PR #9. It launches the indicator using its packaged executable instead of requiring a separate Python installation. That fix requires a rebuilt InputControl distribution; changing ARISE alone does not update existing binaries. Validate the Windows build's visible indicator and a complete start/act/verify/stop cycle before publishing a release.
