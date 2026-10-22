# Current device-test entry point

Read DEVICE_COMPATIBILITY.md first. The owner reported a WatchFree black screen, and visible recovery has not been confirmed. Avoid repeating that launch while the screen is black. Use the physical Input menu or normal remote power to recover before testing an app already known to work.

Run `python3 launcher.py preview` to keep the dashboard active without automatically requesting Conjure. Run `python3 launcher.py check` in another terminal to check authenticated API reads and local HTTP services. Request Conjure explicitly from the dashboard, inspect the new API/page/assets evidence, then observe the screen. Open Remote check on the TV itself and record physical-remote arrow/OK/Back behavior. Counters from a Mac browser or automation are simulated evidence only.

# Real-device checks

These checks must run on the owner's Mac and TV. Cloud simulations are separate. Never share AUTH, `.vizio_local.json`, account details, serial numbers, MAC addresses, or unreviewed diagnostic reports.

1. Run setup using an appropriate certificate trust method, then `python3 launcher.py diagnose`. Compare model and versions. Stop if the pinned certificate changes unexpectedly.
2. Test `key volume_up`, `key volume_down`, then `key mute` twice to restore the starting state. Confirm visible/audio behavior, not just API acceptance. Mute uses toggle code (5,4).
3. Open `preview` and test the English desktop/mobile layout, app search, favorites after reload, horizontal navigation, Enter, and Escape. This validates the Mac browser only.
4. Run `launch`. Record Conjure API acceptance separately from an HTTP page request, actual TV rendering, and CSS/JS loading. Check whether English text is readable at viewing distance.
5. Test TV remote arrows, OK, and Back within Conjure. System Home/Back may be consumed before the page receives them; Mac remote-command success does not prove web keyboard events.
6. Only after recovering from the reported black screen, optionally run `python3 launcher.py watchfree`, wait for startup, then `python3 launcher.py watchfree --check`. Record the reported app identity, visible application, and channel picture/audio in Malaysia separately. A matching legacy ID is not proof of WatchFree+ availability.
7. Test one other native app such as Netflix and read `current_app`. Do not include account information in reports.
8. Discover inputs before selecting one. Switch to a connected, advertised CNAME; read current input and inspect the actual source image. Restore the previous input.
9. Read picture/audio settings first. Record the original value. Only if writable metadata is complete, change an ordinary setting by one advertised step, verify and restore it. Leave unknown settings read-only.
10. Open Spotify's website tile and separately test page loading, sign-in, and audio. In Spotify on a phone/Mac, check whether the TV appears in the device picker. Absence does not establish Connect support.
11. Open RTM Klik and Astro AWANI official pages; test video separately from page loading. Do not alter region, network, entitlement, or DRM settings to force playback.
12. Optionally test AirPlay from macOS Control Center if the TV appears as a compatible receiver. Confirm actual mirroring, not just device discovery. This still needs a Mac.
13. Stop the server with Control+C. Dashboard/reload availability ends; a cached page may persist temporarily. This is not a built-in installation. Standalone Google Play requires a supported independent player with the current evidence.

Report safe results using:

```text
Date:
Model / firmware:
Authenticated API read:
Volume / mute on screen:
Conjure API / HTTP page request / visible rendering:
TV remote arrows / OK / Back inside the page:
App launch / reported identity / visible app / actual playback:
Input CNAME / subsequent read / source image:
Setting / original value / test value / restored:
WatchFree+ channels in Malaysia:
Spotify web / Spotify Connect:
RTM Klik / Astro AWANI page load and video:
AirPlay:
Notes without personal identifiers or credentials:
```


## If the screen is black

Stop relaunching WatchFree. Try the physical Input button to see whether a TV overlay is visible. Normal remote power off/on is an optional recovery step if overlays are absent; never factory reset or flash firmware. Install the correction and test `python3 launcher.py key home`, then `python3 launcher.py support`. Share the metadata output and whether the screen returned. This support command is read-only and does not relaunch any application.
