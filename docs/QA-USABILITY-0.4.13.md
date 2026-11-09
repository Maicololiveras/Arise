# QA 0.4.13: voice, chat and stopping

Historical QA record. Use [current setup](INSTALL-WINDOWS.md) and
[validation evidence](VALIDATION.md) for release status. Findings and pending
checks below describe that revision, not every later build.

The former voice bridge selected System.Speech instead of Forge Edge and silently
substituted a Windows voice. That implicit substitution was removed. A PCM test
showed that a 500 ms endpoint split speech around a 700 ms pause; a longer threshold
preserved one turn. Orb clicking gained toggling and visible privacy/status.

Stop now revoked permission before waiting on Pi, closed owned MCPs concurrently
and rejected stale connections. Settings ignored accidental wheel changes and
closing discarded unsaved edits.

The historical adapter pinned msedge-tts 2.0.4 and checked the installed Forge
Edge capability. Audio went through ARISE's cancelable mixer rather than treating
an asynchronous MCP acknowledgement as playback completion. The preset cleared
Piper and selected Gonzalo; later 0.4.37 introduced the standalone adapter and
explicit optional Windows fallback, superseding the older dependency/policy.

Evidence: Python/Node contracts, synthetic pauses, retained drafts, concurrent
stop and real Qt offscreen. The external synthesis attempt failed with
`Connect Error: {}`; audible Gonzalo was not certified at that revision.
InputControl's emergency hook alone did not stop ScreenView; ARISE coordinated
its owned processes and did not claim to close unrelated applications.

Physical speech, device thresholds, released keys, no delayed capture after Stop
and Windows scaling remained pending. HTTP 503 did not trigger automatic replay;
restoring a draft did not send it. Proposed diagnostics, device calibration and
durable external-delivery reconciliation were not implemented by that revision.
