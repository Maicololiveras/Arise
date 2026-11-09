# Installable mobile web app

The current mobile distribution is a PC-hosted PWA for Android, iPhone and iPad.
It is included in ARISE PC 0.4.41+. It does not require an Apple/Google developer
account, an APK/IPA, a production keystore or an app-store payment. Native mobile
sources are retained for future work; their workflows are manual development tools.

Follow the [Android installation](../README.md#install-android) or
[iPhone/iPad installation](../README.md#install-ios) steps. The address is unique to
your PC and private Tailscale network, so there is no universal public app URL.
Install from that exact HTTPS address. Generate a fresh pairing code after opening
the Home Screen app, and complete authenticator verification there.

## Capabilities and limits

Text, image attachments, explicit microphone recording, PC-side transcription,
response playback, approvals and Stop use the existing authenticated companion.
The PC supplies the agent, memory, tools and configured speech services. Installing
an icon does not supply a missing voice model or enable a paid provider for free.
All existing pairing, session expiry, revocation and per-action approvals remain.

The manifest starts at `/`, never at a URL containing a pairing secret. Installation
code does not save tokens, conversations or audio. Cookies remain Secure, HttpOnly
and SameSite=Strict. There is intentionally no service worker, persistent web cache
or offline task queue: requests reach the PC and uncertain actions are not replayed.
Updating the PC and reopening the app loads its current interface. HTTPS validation
is never bypassed. Tailscale and the PC must remain connected for tasks and voice.

The browser controls installation UI and microphone permission. iOS/iPadOS uses
Safari > Share > Add to Home Screen; enable Open as Web App when offered. Android
uses the install prompt or browser menu. There is no background wake-word listener,
floating system overlay or guarantee of activity while locked/backgrounded.
Physical-device testing of installation, microphone and playback remains necessary.

Removing the Home Screen icon is not server-side revocation. Use PC Settings to
revoke a device, or Disconnect/Unpair in the mobile chat. Stop PC work explicitly
before closing the app when required.

References: [Apple Home Screen web apps](https://support.apple.com/guide/iphone/iphea86e5236/ios),
[MDN installable PWAs](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable).
