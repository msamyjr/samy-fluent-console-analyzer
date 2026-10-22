# Samy Home — Google TV-inspired launcher

An English, TV-friendly home screen and protected local Mac dashboard for the Vizio D40f-G9. Features include horizontal app rows, search, favorites, spatial navigation, an on-screen remote-event check, SmartCast command integration, and Conjure/network diagnostics.

The entry point is `launcher.py`, which delegates to the existing `main.py` backend. This checkout had no file named launcher.py before this work; a different launcher.py on the owner's Mac has not been inspected. Existing main.py commands and private pairing configuration remain compatible.

**The TV keeps its native Wi-Fi connection.** No Wi-Fi provisioning, hotspot, DNS override, VPN setup, subnet scan, firmware flashing, factory reset, or APK installation is implemented. This is a Mac-hosted companion, not a permanent TV system replacement.

## Start on macOS

Python standard library only; no pip packages are required. The owner uses Python 3.13. The current code is tested with Python 3.13.5 on Linux; an earlier 40-test version was also run by the owner on macOS/Python 3.13.17.

After extracting the ZIP on Desktop:

```bash
cd "$HOME/Desktop/Samy_Vizio_Modern_Home"
python3 --version
python3 -m unittest discover -s tests -v
python3 launcher.py preview
```

Keep this Terminal open. In another Terminal:

```bash
open http://127.0.0.1:8766/
open http://127.0.0.1:8099/tv/
```

Preview works without TV credentials. If private configuration already exists, preview enables the dashboard but does not automatically launch Conjure. Stop with Control+C.

From a second terminal **in the project folder**:

```bash
python3 launcher.py check
```

This checks the configured TV identity, local route selection, and both actual local HTTP services. It sends no app-launch or setting-write commands. Local readiness, Mac-to-TV authentication, TV-to-Mac reachability, visible rendering, and physical remote behavior are separate stages.

## Existing TV pairing

Keep `.vizio_local.json` private. The updater preserves it; do not rerun setup or share AUTH if you are already paired.

If setup is needed, run on the owner's Mac on the same network as the TV. With a fingerprint obtained through a trusted channel:

```bash
python3 launcher.py setup 192.164.113.114 --certificate-sha256 YOUR_KNOWN_64_HEX_SHA256
```

Explicit first-use trust for a self-signed TV certificate is also available:

```bash
python3 launcher.py setup 192.164.113.114 --trust-on-first-use
```

Inspect the fingerprint and type uppercase `TRUST` only if you trust the connection. First-use trust cannot establish identity on hostile Wi-Fi. Enter AUTH in the hidden prompt, never in chat or shell arguments. Later requests check the exact pinned certificate before sending AUTH. Investigate a changed certificate rather than automatically accepting it again.

Setup validates D40f-G9 and atomically stores the private config with permissions 0600. Tokens remain on the Mac, never in browser assets or download bundles. If a token was actually exposed, rotate it using the supported pairing flow and rerun setup privately.

## Conjure compatibility

With pairing already configured, stop preview before using:

```bash
python3 launcher.py launch
```

Alternatively use Launch Samy Home on TV in the dashboard. Conjure requests use namespace 4, app ID 17, and the Mac LAN `/tv/` URL on port 8099. The URL is restricted to the local interface selected for the configured TV.

The dashboard's Diagnostics section now reports:

1. Conjure attempt time and API result: not attempted, pending, accepted, or failed.
2. Whether a page request arrived from the configured TV IP.
3. Which allowlisted assets that peer requested, including HTML, CSS, JavaScript, and catalog.
4. An explicit reminder that rendering and remote behavior still require observation.

Each launch attempt clears stale HTTP observations. API acceptance or asset fetching does not establish visible rendering. Server processes and observations do not survive a new task or restart.

## Remote navigation

On the actual TV page, open Remote check. Press the physical remote's four arrows, OK, and Back; observe the counters and focus movement. The panel records navigation events only, sends no native commands, and does not record typed text. Reset starts a new local check.

Arrow keys, Enter, Escape, legacy Back codes, Back aliases, and non-editing Backspace are handled. Text editing keeps normal Backspace and left/right behavior. Physical Home/Back may be consumed by the TV before JavaScript receives an event. Counters measured on the Mac or in automated Chromium are simulated TV evidence, not proof of the TV remote.

## Native apps and controls

Native commands are restricted to the loopback dashboard on 127.0.0.1:8766. The LAN server on 8099 serves an explicit static-asset allowlist only. Do not forward the dashboard port onto LAN. TV-page native tiles explain that launch commands must use the Mac dashboard.

```bash
python3 launcher.py key volume_up
python3 launcher.py key volume_down
python3 launcher.py key mute
python3 launcher.py key home
python3 launcher.py app netflix
python3 launcher.py read current_app
python3 launcher.py input
python3 launcher.py settings picture
python3 launcher.py settings audio
python3 launcher.py support
```

Only launch an app known to be available on your TV, then compare the reported identity and inspect actual display/playback. Community IDs are experimental; website links are not installed apps. Home=(4,15), SmartCast=(4,3), and Menu=(4,8) follow pyvizio's documented community mappings; visible recovery is not guaranteed.

Inputs without explicit enabled metadata remain visible but read-only. Input writes use a fresh current-input HASHVAL and a discovered target CNAME. Picture/audio writes require allowlisted ordinary controls, valid HASHVAL, explicit enablement, and advertised scalar choices or integer ranges. Missing metadata remains read-only with an explanatory reason. No bounds or service endpoints are guessed.

The read-only `support` command prints app identity and capability field metadata without raw values or credentials. `snapshot` produces a private redacted API report, not a firmware backup or screen/playback verification. Review reports locally before sharing.

## Known real-device limits

Read [DEVICE_COMPATIBILITY.md](DEVICE_COMPATIBILITY.md) for the evidence matrix. The owner confirmed authenticated D40f-G9 setup and supplied successful picture/audio reads. The owner reported a black screen after the legacy WatchFree launch; its cause and recovery remain unverified. Do not repeatedly relaunch WatchFree while the TV is black. Try the physical Input menu or normal remote power off/on, without factory reset.

WatchFree's legacy namespace 2 / app ID 22 does not establish WatchFree+ availability in Malaysia. `watchfree --check` is read-only; identity matching never verifies channels or audio. Spotify opens its official website; Spotify Connect is conditional on TV discovery and remains unverified. RTM Klik and Astro AWANI are official website links whose TV-browser playback is unverified. No regional, entitlement, or DRM bypass is provided.

Conjure rendering, physical remote events, and TV-to-Mac HTTP access are not established by the supplied device evidence. Wi-Fi client isolation or macOS Firewall can affect TV-to-Mac requests even when authenticated remote commands work. A phone test is separate evidence, not proof of TV reachability. The explicit owner-supplied 192.164.113.114 address is accepted even though it is not RFC1918 private; no subnet scanning occurs.

AirPlay is an optional Mac screen-mirroring fallback only if the TV appears as a compatible receiver; it is unverified and still needs the Mac. No permanent internal launcher, Google Play, native APK support, bootable USB OS, or cross-model firmware compatibility is claimed.

## Update without pairing again

Stop the server. From the existing project directory:

```bash
curl -fL "https://github.com/msamyjr/samy-fluent-console-analyzer/raw/refs/heads/download/samy-vizio-modern-home/downloads/update.py" -o .samy_update.py &&
python3 .samy_update.py
```

The updater verifies SHA-256, rejects unsafe archive paths and private config files, and backs up replaced application files under `backups/`. It does not read or copy `.vizio_local.json`. If your existing launcher.py is a separate custom implementation, review its backed-up version before treating this as an adaptation of that file. Existing older documentation is preserved rather than deleted; use this English README for the current release.

## Tests and files

```bash
python3 -m unittest discover -s tests -v
```

The 73-test app suite uses mocked TV HTTPS and real local HTTP servers. Four independent updater tests are available in the development checkout under downloads/. Optional browser tests require Node, Playwright, and Chromium; these are not runtime dependencies:

```bash
node tests/browser_smoke.cjs
node tests/browser_controls.cjs
```

In the cloud, system Chromium is selected with `SAMY_CHROMIUM_PATH=/usr/bin/chromium`. The browser controls suite simulates TV API responses. All screenshots in artifacts/ are local-browser captures, not photographs of the TV.

- `launcher.py`: compatible entry point; `main.py`: existing backend.
- `site/`: English TV page, Mac dashboard, local artwork, styles, ES5 JavaScript, and catalog.
- `DEVICE_COMPATIBILITY.md`: current owner-confirmed versus simulated evidence.
- `REAL_DEVICE_TESTS.md`: detailed device acceptance procedure.
- `TEST_RESULTS.md`: test scope and limitations.
- `COMPATIBILITY.md`: platform and service limitations.

The old repository-root index.html is not the application entry point. CODEX_PROMPT.md is the supplied historical brief, not independent evidence of compatibility or token exposure.
