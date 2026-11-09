# Connections and reminders: initial QA record

Historical engineering record. Version-specific results below are not current
installation instructions. Use [Windows setup](INSTALL-WINDOWS.md),
[owned runtime](owned-gentle-runtime.md) and [validation](VALIDATION.md).

Initial implementation: `qa-connections-companion`, based on 0.4.23,
October 22, 2026. The mobile flow was subsequently extended; use the
[guided setup](MOBILE-GUIDED-QA.md) for current behavior.

## Implemented contracts

Outbound adapters cover Telegram Bot API, WhatsApp Business Cloud API using an
approved one-body-variable template, Outlook Mail.Send and Teams ChatMessage.Send.
Configuration is not proof of connectivity or delivery. Incoming chat/webhooks,
Outlook reading/calendar and Teams reading/channels were not implemented.

Microsoft device authorization uses explicit consent, renewal and Windows DPAPI.
A public-client Entra registration is required; Teams uses an organizations
tenant. Tokens remain masked and network requests run outside the UI thread.
Telegram requires an exact chat ID and prior recipient interaction. WhatsApp
requires Business credentials, phone-number ID, API version, approved template
and language; a personal WhatsApp Web QR is not equivalent.

SQLite reminders belong to a chat. Creation/list/cancel supports timezone-bearing
ISO dates and interval recurrence, with visible confirmation and exact authorized
external destination. Occurrences are claimed before delivery. A timeout/crash
leaves uncertain delivery and is never automatically resent. Missed repetitions
coalesce once on recovery while preserving cadence; a 86400-second interval is
not a DST-aware fixed local time. Reminders are not general agent-execution jobs.

The mobile gateway is separate loopback plus Tailscale Serve. Initial pairing
used a 192-bit single-use invitation, five-minute expiry, 256-bit device secrets
stored as SHA-256, Secure/HttpOnly/SameSite=Strict cookies, 15-minute renewable
sessions and a 30-day maximum. Current TOTP/persistent-port behavior is documented
in the guided guide. Pairing never exposes privileged configuration or the
internal daemon capability. Failed sends preserve the draft without replay.

Delegated process nonzero exits remain failures even when a result file exists.
Delegation retains originating chat, ID, public result and parent notification.

## Deferred scope

Bidirectional service webhooks, deduplication, secure sender/chat association,
calendar/DST scheduling, conditional execution jobs, push notifications,
proactive cross-project memory, document attachments and VPS deployment require
separate work. Tailscale network policy is not automatically granted by ARISE.
The later Android APK is separate from the Windows installer and is not iPadOS.

Agent subscription OAuth and voice API billing are separate. No combined
subscription-funded realtime voice workflow was certified here. Local STT/TTS
with a permitted text provider is a pipeline, not native speech-to-speech.
Check current provider documentation before making billing/entitlement claims.

## Historical evidence

The initial local suite ran 226 tests: 220 passed and six Windows-only skips.
Fourteen connection tests covered simulated HTTP/OAuth pending/slowdown/renewal,
template parameters, revocation, expiry, rotation, origin, route bounds, chat
changes, durable scheduling, restart, cancellation and uncertain delivery.
The delegated nonzero-exit suite subsequently passed 6/6. Qt was rendered
at 430×640 offscreen on Linux. No external account or physical phone was tested.
Windows DPAPI, live delivery, Tailscale and device acceptance remained separate.

References: [Telegram](https://core.telegram.org/bots/api),
[Microsoft device authorization](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-device-code),
[Graph mail](https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0),
[Graph chat](https://learn.microsoft.com/en-us/graph/api/chat-post-messages?view=graph-rest-1.0),
[Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve).
