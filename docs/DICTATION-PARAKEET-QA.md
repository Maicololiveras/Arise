# Local draft dictation

The panel microphone records on the first click and transcribes on the second.
While listening it displays a microphone with an upward arrow. Text is inserted
at the cursor without erasing the draft or sending it to Pi; insertion can be
undone. The waveform button is the separate voice-conversation control.

First use prepares the pinned runtime/model with progress and cancellation.
The model is approximately 670 MB plus runtime files. After installation, click
again to record; download completion never opens the microphone. Subsequent
recognition is local and requires no model API key.

Escape, Stop, chat changes and exit cancel capture. Late cancelled results are
discarded. Sending is suspended while dictation owns the microphone; editing
remains available. Capture is limited to 120 seconds. Conversation capture is
paused and its previous mute state restored afterward.

## Engine and provenance

The installer, worker and session derive from Gentle Shell v4.5.1 commit
`e8b2814934f98ded9199f49bde8f482c97eece3a`. ARISE calls its own adapter rather
than invoking `/gentle:voice` in RPC. Distributed ESM does not require a local
TypeScript compiler.

- Parakeet TDT 0.6B v3 int8, sherpa-onnx 1.13.8 and node-cpal 1.0.0.
- Node 22+; Windows x64 needs Visual C++ Runtime. Windows ARM64 is unsupported
  by this pinned dictation distribution.
- CPU inference; audio/text is not sent to an AI provider.
- System default input; preserve the complete default rate/channel/sample-format
  tuple. Convert to mono 16 kHz for recognition.
- Capture and inference run in a separate process with temporary in-memory audio.
- Private storage: `<ARISE data>/dictation/voice`; hashes and sizes are pinned.
- The panel's repair action reinstalls pinned components without touching chats
  or memories. Notices and licenses are in `resources/parakeet/NOTICE.txt`.

The fixed [ARISE mirror release](https://github.com/Maicololiveras/Arise/releases/tag/voice-parakeet-v3-2bda32ec70b0)
is maintained by `distribution/parakeet-v3`. Clients do not need direct Hugging
Face/npm access. Networks must allow GitHub and its release asset CDN. TLS and
upstream integrity checks remain enabled.

## Diagnostics and acceptance

The local history retains at most 100 bounded installation/runtime events. It
contains no recordings, drafts, transcripts or raw native stderr. Opening,
streaming, model loading and transcription failures are distinguished.

Tests cover two-click behavior, draft/undo preservation, no automatic send,
cancellation, late results, chat changes, format retention and download failure.
Native capture/recognizer fixtures do not prove physical microphone behavior.
Before promoting a target, compare Spanish and technical terms against the same
Dictto recordings, measure startup/inference time and verify tray shutdown.
The desktop change does not update Android dictation.
