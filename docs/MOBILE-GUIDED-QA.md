# Guided mobile access — Windows and Android QA

This is a controlled companion feature, not a guarantee of vulnerability-free
operation. VPS/Coolify remains deferred. The PC hosts the model/tools and must
remain powered on with ARISE and Tailscale available.

## Pair and use

1. Verify ARISE chat on the PC first. Install Tailscale on both devices and join
   the same private tailnet. Configure strong authentication at its identity
   provider; ARISE cannot certify the provider's MFA configuration.
2. On the PC, open Connections/mobile settings. Configure the authenticator QR
   or manual secret and confirm a code. Windows protects the secret with DPAPI.
   Keep local PC access for revocation; never share the QR.
3. Prepare the private connection. ARISE discovers the Tailscale name and sets
   Serve to loopback. Complete any official login, HTTPS authorization or Windows
   permission request. Existing unrelated Serve services are not overwritten and
   Funnel is not configured. Tailnet access rules remain the owner's responsibility.
4. Generate this chat's pairing QR. In Android, open Tailscale, scan and connect.
   QR scanning needs Google Play Services; pasting the link is the alternative.
   A normal camera can also open the private browser client.
5. Confirm with a fresh authenticator code. Invitations expire after five minutes
   and are single-use. Device access lasts at most 30 days and can be revoked
   earlier on the PC or by unlinking on the phone.
6. Type or record speech. Recording is limited to 29 seconds and transcribed on
   the PC into a draft for review before sending. A microphone permission prompt
   may require another click. The PC needs a compatible installed transcription
   model; mobile capture does not open its microphone or silently download a model.
7. Listen generates speech on the PC using an installed Windows voice. It does
   not guarantee Gonzalo. Incoming recordings are not written to disk; outgoing
   audio uses a temporary file removed after delivery. Sent text remains in history.
8. Explicitly resume the linked chat only when the PC has no active work,
   subagents or terminals. Stop cannot cancel another chat. Protected approvals
   require a fresh authenticator code; local execution/control permissions are
   not granted by pairing or a mobile reply.

The local port persists across restart and binds only loopback. Disabling mobile
access prevents restoration; retaining Serve does not expose a stopped backend.
This does not wake a powered-off PC or bypass Windows login.

## Protections and limits

Cookies are Secure/HttpOnly/SameSite=Strict. POST requests validate Origin; routes
have bounded payloads and CSP. WebView does not receive a privileged native
JavaScript bridge. Cookie storage is private app storage, not a claimed
non-exportable Keystore key.

TOTP uses six digits with a ±30-second window, rejects reused time steps and
persists a five-minute lockout after five failures. Setup is restricted to the
authenticated PC bridge. This is an application second factor, not a passkey or
proof of Tailscale-provider MFA. Revocation is checked before returning results;
already-running transcription/synthesis may finish consuming CPU.

Audio is bounded mono PCM16/16 kHz. Chat is rendered as text; up to four PNG/JPEG
images of 2 MB each are accepted. Office/PDF attachments are not included.

## Acceptance still required

Test QR, Wi-Fi/mobile data, microphone/permissions, screen lock, phone-call
interruption, reconnect, response playback and revocation on real Android.
Verify Serve, HTTPS, DPAPI and PC transcription/SAPI on Windows. CI fixtures do
not substitute for those checks. Android QA uses debug signing; a subsequent
APK may require reinstalling and pairing again. Stable signing keys must remain
outside the repository. Passkeys, account recovery, push, document attachments
and VPS deployment are separate future work.

[Android implementation](android-companion-qa.md) ·
[Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) ·
[Tailscale MFA](https://tailscale.com/docs/multifactor-auth)
