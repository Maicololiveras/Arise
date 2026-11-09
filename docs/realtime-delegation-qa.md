# QA 0.4.22 — realtime delegation

OpenAI and Gemini voice adapters now acknowledge an accepted Gentle Shell task without waiting for completion. Explicit tools query, correct and cancel a task belonging to the current chat. A new request during an active task returns busy rather than silently steering it. Runtime approvals and local execution permissions are unchanged.

Final public output is announced once while the original voice session is still active and idle. Raw tool events and error diagnostics are not forwarded. Chat switch/generation changes reject stale dispatch and suppress old audio/results. Stop invalidates queued dispatch across its generation boundary. Reconnect does not replay work. The chat history remains the result destination if voice is closed.

## Try it
1. Settings > Voice: choose openai or gemini, a model available in your account, its native voice and credentials. Existing values are not migrated automatically.
2. Enable local execution for this chat only if the task requires it. Start microphone.
3. Ask for a document, then keep talking; ask for status and explicitly correct the same task.
4. Test cancellation, stopping desktop tools, switching chats and returning. Confirm no wrong-chat output or automatic permission restoration.

## Limits
- One active parent task per chat; Gentle Shell may delegate internally. No new independent job scheduler.
- Initial runtime connection/submission can still take time; only waiting for completion was removed.
- Cloud provider audio is not Gonzalo. Local/Forge settings remain selectable and no fallback voice is introduced.
- Local dialogue retains its existing request-alias/queued dispatch contract. Its advertised tools are isolated from the new realtime task-ID contract, with no duplicate task_status schema.
- Local open-model route: STT + local OpenAI-compatible text endpoint + local TTS. Full offline operation additionally requires local Gentle Shell models and tools; Gonzalo via Edge requires Internet.
- Local WebSocket fixtures validate transport/events, not provider availability or actual audio quality.
- Cloud credentials, real microphone, Windows install/update and a live delegated DOCX on this build remain manual QA gates. No claim of a full real-provider trial.
