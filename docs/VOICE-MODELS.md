# Speech, dictation and models

ARISE has three distinct paths: draft dictation, voice conversation and optional
wake activation. Their models and devices are not interchangeable.

| Path | Behavior | Main requirement |
| --- | --- | --- |
| Dictation microphone | Record, stop, transcribe into the draft | Compatible pinned Parakeet runtime/model |
| Voice conversation | Transcribe/respond/speak while work continues | Selected provider, devices and credentials or local models |
| Wake activation | Listen for configured phrases | Opt-in Vosk runtime and activation model |

## Dictation

Click the microphone once to record and again to stop/transcribe. Review the
inserted text before sending. Escape, Stop, chat switch and exit discard a
cancelled result. Parakeet uses the system default input, which may differ from
the conversation device. Downloads show progress and verify hashes; completion
does not automatically open the microphone. See [Parakeet details](DICTATION-PARAKEET-QA.md).

## Output and Gonzalo

Select Gonzalo in Voice settings and use the output-only preview. The bundled
`msedge-tts` 2.1.1 adapter needs Microsoft's online service; no offline Gonzalo
weights are distributed. System trust and explicit HTTP/HTTPS proxies are
supported without disabling TLS. PAC and interactive proxy authentication are
not implemented.

Fluent playback starts with a short phrase and prepares one following phrase.
It is ordered and interruptible, not live model-token streaming or a fixed-latency
guarantee. The established Windows build converts audio using bundled FFmpeg;
native previews include Miniaudio decoding. Optional Windows fallback is visible
and uses an installed system voice, not Gonzalo. A failure after speech begins
does not replay the entire response through another voice.

## Local and cloud conversation

Vosk, OpenAI Whisper `.pt` and faster-whisper/CTranslate2 folders require their
matching engines. Never pass a `.pt` file to faster-whisper. Use explicit model
selection or detection; a path alone does not prove a valid loaded model.
The complete Windows model pack includes its pinned weights, provenance,
licenses and checksums. Models are installed under the ARISE data directory.
Installation validates before changing configuration and rolls back failures.

A local OpenAI-compatible dialogue server can run alongside Gentle, or voice
can delegate directly to Pi. Its endpoint must be local, and a configured launch
command must remain in the foreground. ARISE only stops the server it owns.
External servers are reused, not terminated. Local STT/TTS does not make a cloud
agent or Gonzalo offline.

OpenAI Realtime and Gemini Live use separate credentials and models. A ChatGPT
subscription login does not grant a realtime API key. Provider availability
and billing must be checked for the selected account.

## Wake, interruption and limits

Wake listening is off by default. Configure phrases, optional spoken response
and whether to open the chat. Test recognition with your pronunciation. The
renderer must remain running for automatic panel opening. Windows shortcuts
are not claimed as cross-platform global shortcuts.

Speech interruption, Stop and task cancellation have distinct effects. Use
headphones to reduce feedback: acoustic echo cancellation is not implemented.
UI questions may accept speech, but sensitive approvals retain their required
review. Changing chats rejects late audio from the previous session.

Vosk 0.3.45 has no pinned wheel for macOS or Windows ARM64. Native previews do
not bundle offline models or claim feature parity. See the
[platform capability limits](NATIVE-DISTRIBUTIONS.md). Physical microphone,
recognition accuracy, speaker selection and latency require on-device testing.
