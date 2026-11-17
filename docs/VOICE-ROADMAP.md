# Voice performance and incremental roadmap

Scope: ARISE only. WEG Assistant remains a separate minimal product.
Gonzalo (`es-CO-GonzaloNeural`) remains the preferred output voice.
Future transcription services must be self-hosted/free or demonstrably included
in an existing subscription; an Antigravity subscription is not evidence of
access to a separate speech API.

## Phase 1 — implemented for Preview 0.4.47

The local conversation pipeline now emits content-free `voice_metrics` events.
The authenticated local `GET /api/status` response includes the most recent 120 records in
`voice_metrics`. Records stay in memory and disappear when ARISE exits. They
contain random turn IDs, stages, durations and numeric/boolean diagnostics;
never audio, transcripts, credentials or provider error messages.

| Stage | Measurement |
| --- | --- |
| `model_ready` | Model setup time and whether the existing model was reused |
| `capture` | Captured PCM duration, endpoint silence and submitted audio duration |
| `stt_queue` | Time waiting for the transcription worker |
| `transcription` | Completed transcription, including lazy segment iteration |
| `response_ready` | Command processing through completed agent response, including tool work |
| `synthesis` | Gonzalo synthesis per chunk, before decoding |
| `first_playback` | From capture completion to the first audio block handed to playback |
| `playback` | Time waiting for each queued audio chunk to finish |
| `speech_total` | Speech rendering and playback, including cancellation status |

`first_playback` is an application measurement, not a microphone measurement
of sound leaving the speaker. It excludes the endpoint wait shown in `capture`.
Initial wake text starts timing at submission. Failed stages do not produce a
successful completion metric. Realtime cloud voice and push-to-talk Parakeet
are outside this phase's local conversation measurements.

Optimizations:

- Keep the configured pause threshold (default 1400 ms). Never shorten it
  automatically and split a natural sentence to improve a timing number.
- After detecting the end of a turn, trim only trailing silence beyond a 200 ms
  margin before STT. Internal pauses and the existing preroll remain intact.
- Reuse one Node synthesis bridge across the chunks of one spoken response.
  Close it on completion, failure or cancellation; never share it across chats.
  This saves process launches, not provider WebSocket handshakes.
- Retain the existing STT model cache keyed by engine/model and measure warm
  reuse. The current synthesizer still uses its existing sentence look-ahead.

### Acceptance before stable

Use the same microphone, model, hardware and network for baseline and candidate.
Compare cold startup and at least 20 warm utterances, including a 700 ms pause,
names, background noise, long replies, interruptions, chat switches and network
failures. Inspect median and p95 per stage. Compare the actual recognized words
and accidental activations as well as timing. Verify Gonzalo, stop controls,
ordered playback and no duplicate speech after a partial failure.

Automated tests cover trimming, preserved pauses, no-speech input, max-duration
turns, process reuse/cancellation, metrics and existing speech behavior. No real
microphone/provider latency improvement is claimed before desktop acceptance.

## Future phases — not implemented

| Phase | Planned work | Acceptance gate |
| --- | --- | --- |
| 2. Recognition | Compare free multilingual ASR models on real Spanish samples; evaluate VAD and project vocabulary. | Fewer transcription errors and false activations on the same labeled recordings; no automatic execution of uncertain commands. |
| 3. Fluent dialogue | Speak completed response sentences while generation continues; improve echo handling and interruption. | Gonzalo retained, no self-triggering or repeated/skipped phrases; stop works during every stage. |
| 4. Contextual correction | Conservative correction with access to the original transcript; request clarification for ambiguous names, dates or actions. | No invented instructions; separate raw and corrected text; measure added latency and subscription eligibility. |
| 5. Optional Coolify STT | Evaluate Speaches/faster-whisper, authenticated private connection, persistent model cache, timeouts and explicit local fallback. | Benchmark CPU/GPU resources and network latency first; no public unauthenticated microphone endpoint or duplicate dispatch on retry. |
| 6. Cross-chat continuity | Durable reminders/tasks, routed clarification requests and completion notifications independent of the visible chat. | Recovery after restart without replaying side effects; authoritative task state separate from memory; load context only when needed. |

Delivery: implement and test one bounded phase at a time in QA/ARISE Preview.
Promote only after desktop acceptance. A planning entry is not an implemented
feature or a promise that a third-party subscription supports audio.
