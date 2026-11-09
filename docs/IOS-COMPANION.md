# ARISE Companion for iPhone and iPad

**Native mobile development is deferred.** Use the [installable mobile web app](MOBILE-WEB-APP.md) for current Android, iPhone and iPad installation, without store accounts or signing fees. The native workflows are manual development tools only.


The initial native UIKit/WebKit app lives in `mobile/ios`. It targets iOS/iPadOS 16+
and both device families. It connects to the existing PC-hosted companion using
an exact private HTTPS Tailscale origin. The PC still runs the agent and tools.

## Implemented scope

- Responsive iPhone/iPad layout, text entry and the existing paired chat UI.
- One-use pairing and authenticator remain enforced by the PC backend.
- Same-origin navigation and subresource filtering, default TLS trust validation,
  no privileged native JavaScript bridge and no insecure HTTP exception.
- Microphone permission prompts only for the selected origin and its main frame.
  Backgrounding the app stops media capture/playback; there is no background wake
  listener or floating overlay over other applications.
- Ephemeral web storage: disconnecting discards the device's web session. Pair again
  when opening a new connection. Disconnect does not cancel a PC task; use Stop in
  the paired chat first when needed. Revoke device access from the PC separately.

Recording, image picking, audio playback, pairing and accessibility still require
physical iPhone and iPad acceptance. Passing simulator tests does not certify them.

## Build and test on a Mac

1. Install Xcode with an iOS simulator runtime and XcodeGen.
2. Run `cd mobile/ios && xcodegen generate`.
3. Open `ARISECompanion.xcodeproj`, select the `ARISECompanion` scheme, and choose an
   iPhone or iPad simulator. Run Product > Test, then Product > Run.
4. For a personal device, select your own development team in Signing & Capabilities
   and follow Xcode's device provisioning instructions. Do not bypass device trust.
5. Install Tailscale on the device, join your authorized network, and enter the
   private address from ARISE PC Settings > Connections > Mobile. Complete pairing
   and the authenticator prompt. Test text, explicit recording and Stop.

The **ARISE iOS companion** workflow compiles and tests on both simulator families
and uploads simulator ZIPs and test reports. These ZIPs cannot be installed on an
ordinary iPhone or iPad. No distribution certificate is needed for simulator CI.

## Distribution remains blocked

The maintainer does not yet have Apple Developer membership. Consequently no IPA,
TestFlight link or App Store download is advertised. After enrollment:

1. Register the app identifier and create its App Store Connect record.
2. Configure the team and distribution signing in Xcode; add the final app icon,
   privacy disclosures, screenshots, support URL and review information.
3. Archive and validate on a Mac, then upload the signed archive to App Store Connect.
4. Test on physical iPhone and iPad through TestFlight, including microphone consent,
   disconnect/background transitions, certificate rejection and profile upgrades.
5. Submit the selected build for review. Advertise the App Store/TestFlight URL only
   after it is available to the intended users. Apple approval is not automatic.

Sources: [Apple distribution](https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases),
[App Store Connect workflow](https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-workflow),
[XcodeGen project specification](https://github.com/yonaskolb/XcodeGen/blob/master/Docs/ProjectSpec.md).
