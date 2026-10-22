# Device compatibility — Vizio D40f-G9

Prepared 2026-10-22. Device identity supplied by the owner: firmware 4.600.601.0-10, SmartCast API 3.0.12-2507.0002, MTK5581, Conjure MTKA-7.600.261.0-prod. The owner is in Malaysia.

## Real-device evidence from this conversation

| Capability | Evidence | Status |
|---|---|---|
| AUTH and model identification | Owner supplied successful `Authenticated D40f-G9` output | Owner-confirmed |
| Remote transport | Owner supplied API-accepted key output; previously reported working volume | API transport confirmed by owner; not every key verified |
| Picture/audio reads | Owner supplied actual setting values | Owner-confirmed reads |
| Input switching | Earlier filtered input list was empty | Not verified; metadata report needed |
| Picture/audio writes | Setting specifications were null | Remain read-only unless complete safe metadata is present |
| WatchFree / WatchFree+ playback | Owner reported a black screen after legacy launch | Failed in the reported attempt; cause unknown |
| Home recovery | Old Home command was API-accepted but owner still saw black | Old mapping did not visibly recover the screen; corrected mapping unverified on TV |
| Conjure API, visible launcher | No complete real-device launch/render evidence supplied; owner said the TV screen had not changed | Compatibility not established |
| Physical remote events within Conjure | No on-TV event-check result supplied | Not verified |
| TV-to-Mac HTTP page and assets | No actual TV-peer observation supplied | Not verified |
| Spotify / RTM Klik / Astro AWANI video | No successful real-device playback supplied | Not verified |
| AirPlay | No real-device test supplied | Not verified |

The black screen is not proof that DNS, region, firmware, or the panel caused it. Do not repeatedly relaunch WatchFree while the TV is black. Try the physical Input menu or normal remote power off/on, without factory reset. The corrected Home and separate SmartCast commands are available for a subsequent controlled recovery test.

## What was tested in the development environment

- Python standard-library runtime, offline suite, real loopback HTTP servers, static-asset allowlist, protected control APIs, certificate pinning, redaction, and native payload generation.
- Simulated Conjure accepted and rejected responses, reset of stale observations, and separate TV-peer asset tracking.
- Native Netflix/Plex command payloads through real local HTTP handlers with mocked TV HTTPS; unknown app rejection.
- Chromium desktop/mobile layout, search, favorites, spatial arrow navigation, OK, Back aliases, and observable event counters.
- `python3 launcher.py check`: both actual local servers reachable and 14 catalog entries. The cloud has no TV configuration, so TV status is explicitly `not_configured`.

These are simulated TV tests and local-browser/local-server checks. None establishes physical TV rendering or regional playback.

## Native Wi-Fi preservation

The launcher uses the TV's existing connection. No Wi-Fi provisioning, hotspot, DNS override, network configuration write, VPN setup, subnet scan, firmware update, factory reset, or APK installation is provided. The Mac hosts public static assets on 8099 and a control dashboard on 127.0.0.1:8766. Authentication stays in the private Mac configuration.

Mac-to-TV API access and TV-to-Mac HTTP access are independent. Open-Wi-Fi client isolation or macOS Firewall can affect the latter. A successful localhost request, route lookup, phone test, API launch, or asset fetch alone does not prove visible rendering. Phone reachability checks should be recorded separately from a request attributed to the configured TV IP.

## On-device acceptance sequence

1. Keep the existing TV Wi-Fi settings. On the paired Mac, start `python3 launcher.py preview`; open the dashboard locally.
2. In a second terminal in the project folder, run `python3 launcher.py check`. Confirm authenticated reads and local services separately.
3. From the Mac dashboard, request Launch Samy Home on TV. Inspect Diagnostics for `conjure_api_status`, page-request timestamp, and `tv_assets_requested`.
4. Look at the physical screen. Record whether the English Samy page actually renders; an accepted API command is insufficient.
5. On that TV page, open Remote check. Use the physical remote's four arrows, OK, and Back. Record the counts shown on the TV and whether focus visibly moves. Browser counters measured on Mac do not validate the TV remote.
6. Launch one native app that is already known to work on this TV, then read `current_app` and inspect actual display/playback. Do not choose WatchFree while the earlier black screen is unresolved.
7. Preserve the resulting observations as device evidence, without AUTH, serial numbers, SSIDs, MAC addresses, or unreviewed reports.

`launcher.py` was added as a compatible entry point because this checkout contained `main.py` but no existing file named `launcher.py`. The backend and old commands remain usable. If a different launcher.py exists on the owner's Mac, it has not been inspected; the updater backs up files before replacing them, and that separate version should be reviewed before treating this as an adaptation of it.

No native APK support, permanent launcher installation, bootable USB OS, or firmware replacement has been verified. This remains a Mac-hosted companion. See COMPATIBILITY.md for wider platform limits and REAL_DEVICE_TESTS.md for detailed procedures.
