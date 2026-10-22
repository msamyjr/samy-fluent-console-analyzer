# Validation evidence — English release

Validation runs in the Linux cloud development environment, not on a real TV. The initial uploaded project had 6 tests. The current application suite has 73 offline tests; four independent updater tests are maintained under `downloads/` in the development repository. Current-run logs and English screenshots are in `artifacts/`.

## Scope

- Python 3.13.5: application unit and local HTTP integration tests. TV HTTPS responses are mocked; loopback HTTP servers are real.
- Chromium 154.0.8037.57 / Node 24.19.0 / Playwright: browser smoke and simulated-control tests. System Chromium was used because the Playwright browser CDN was denied by network policy; TLS verification was not disabled.
- English release: both documents declare lang=en and dir=ltr. Browser checks cover LTR layout, English navigation/status/error text, no Arabic application text, desktop/mobile overflow, search, persistent favorites, horizontal rows, keyboard navigation, external-link navigation, offline command rejection, and diagnostics.
- Simulated controls: volume, error feedback, input discovery/switching, metadata-gated settings, native launches, CSRF headers, and WatchFree identity without a playback claim.
- Updater: checksum, backup, config preservation, private-file rejection, path traversal, and symlink safety. The published updater and actual ZIP are also executed in an isolated fixture before delivery.

## Security and behavior covered

Pinned TV certificates are checked before sending AUTH. Default TLS chain verification remains enabled without a pin. Redirects and inherited proxies do not forward authentication. Invalid JSON, oversized replies, malformed STATUS/ITEMS, invalid headers, CSRF, hostile Host/Origin, and cross-site API requests are rejected. Top-level external navigation may open only the dashboard document.

Config and reports use private permissions. Exact credentials are scrubbed before JSON encoding, including escaped strings. LAN serves only an explicit static-asset allowlist. Preview needs no AUTH and rejects writes when offline. Partial startup closes the first server; shutdown releases both.

Input writes use the fresh current-input HASHVAL and target CNAME. Settings require allowlisted names and enabled, bounded metadata; HASHVAL_ERROR retries once. Mute uses toggle code 4 rather than mute-off code 2. WatchFree status normalizes supported current-app shapes but never asserts screen or playback verification. Spotify and Malaysian services are website links, not invented native app IDs.

## Limits

No real-TV tests were performed from the cloud. Owner-provided setup output confirms authenticated D40f-G9 pairing; it is separate from simulated results. Test-log `device read succeeded` lines belong to a mocked snapshot test in a temporary directory, not live reads.

WatchFree+ channels in Malaysia, Spotify playback/Connect, website video in Conjure, AirPlay, permanent installation, Google Play, and firmware upgrades remain unverified or unsupported by the available evidence. See COMPATIBILITY.md and REAL_DEVICE_TESTS.md. Existing Arabic documentation in previously installed folders is preserved rather than deleted; current distribution and runtime UI use English.


## Black-screen recovery and protocol parsing correction

63 app tests passed. Added regression checks for singular and lowercase ITEM current-app responses, null identity, distinct Home/SmartCast/Menu mappings, read-only display of inputs without an enable flag, rejection of switching those inputs, explanatory setting metadata, and a read-only support report excluding raw values. Both browser suites were rerun; the control fixture also verifies disabled read-only input buttons.

The owner's physical TV black screen remains unverified/unresolved from the cloud. API key acceptance is not proof of visible recovery, and these tests do not establish the cause or WatchFree+ availability.

## Current launcher workflow

73 app tests plus 4 independent updater tests cover the current workflow. The launcher.py entry point was exercised directly. Connectivity checks used real local servers; TV HTTPS was mocked. New coverage includes accepted/rejected Conjure attempts, configured-peer asset observation, separate rendering/remote status, Netflix/Plex API payloads, and unknown-app rejection. Browser tests exercise the Remote check counters (four arrows, Enter, Escape, non-editing Backspace), reset/close behavior, responsive English UI, and native launch controls with simulated TV responses. No native Wi-Fi or DNS setters were added. Real-device results are reported separately in DEVICE_COMPATIBILITY.md.
