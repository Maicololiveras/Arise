# Desktop transport · Preview 0.4.50

ARISE keeps a Pi/Gentle process for the active chat. As in [Gentle Shell GPUI's RPC client](https://github.com/ismaelosuna7824/gentle-shell-gpui/blob/5388943f292d7ac8585093a3cbdd767438074eaf/crates/pi-rpc/src/lib.rs), commands and replies use correlated IDs and LF-delimited UTF-8 JSON over pipes. A reader delivers correlated replies directly; an ordered worker handles unsolicited messages, tools and dialogs. Its bounded queue applies backpressure when saturated.

The separate resident process remains the owner of sessions, permissions, memory and the ARISE system prompt. A single desktop reader uses a persistent authenticated loopback HTTP socket. It waits for events by cursor rather than asking from the UI thread every 80 ms. The resident wakes the wait on publication or returns an idle heartbeat after one second. The next request reuses the socket. Batches contain at most 128 ordered events. The reader waits for Qt to consume a batch before asking for the next one. A broken connection retries by cursor; a cursor outside the retained log invokes the existing snapshot recovery. Reconnecting never resubmits a prompt.

Normal prompts with an already known session file skip the redundant get_state round trip. Initial session discovery, slash commands and checkpointing still query the engine. The Desktop RPC capability probe remains separate from model prompts: unsupported operations do not gain permission through the transport.

## Acceptance checks

Run unittest discovery for test_resident_channel.py, test_arise.py and test_pi_real.py. The channel tests use actual OS pipes and loopback sockets; the real-Pi integration uses a deterministic local provider. On Windows, test a warm and cold chat with the same provider, switch conversations, answer one pending approval and stop an active reply. Measure submission-to-first-visible-text separately from model generation and voice synthesis.
