# Desktop chat in Preview 0.4.49

While Pi is writing, the native chat shows a scrollable plain-text reply. Markdown is rendered once after completion. Older messages opens the preceding page of 40 saved messages, excluding diagnostics. Back to latest returns to the active conversation. Incoming messages remain saved while browsing. The live history view is periodically compacted to avoid retaining an entire long conversation with images.

The resident host maintains a bounded event log. On reopening the panel or detecting a cursor outside that log, the desktop can recover saved messages, the current partial response and outstanding questions from the active session. This does not re-run prompts or grant approvals. A daemon restart cannot recover uncommitted output from a dead Pi process.

In Settings, open the chat capabilities dialog to see the permission mode, active profile and job count if the connected Gentle Desktop RPC service provides them. Missing fields are unknown, not zero. These are reads; the ARISE local-execution permission remains separate.

Windows acceptance: stream a long reply, scroll up while it is writing, compare the final text, open older messages in a chat with over 40 saved replies, return to latest, and reconnect the renderer during an unanswered agent question. Confirm that answering it once resumes the same session.
