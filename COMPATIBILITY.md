# Compatibility report — Vizio D40f-G9

## Hardware and evidence

The owner supplied firmware 4.600.601.0-10, SmartCast API 3.0.12-2507.0002, platform MTK5581, and Conjure MTKA-7.600.261.0-prod. The explicit TV host is 192.164.113.114:7345. The owner is in Malaysia and uses Python 3.13 on a Mac.

The owner confirmed authenticated remote commands work and later supplied successful `Authenticated D40f-G9` setup output. Cloud tests do not establish native app playback, Conjure remote events, AirPlay, or WatchFree+ regional availability. No cloud connection was made to the owner's TV.

## Built-in Google Play without HDMI

No supported internal Google Play, Android TV, APK installation, permanent launcher replacement, root, or firmware migration has been demonstrated for this model. A MediaTek processor does not establish an Android package manager or licensed Google services. The English Google TV-inspired design is an independent hosted HTML interface.

The Mac server must stay running. An already loaded page might remain temporarily after the server stops; that is not permanent installation. A certified external Google TV / Android TV device over HDMI is the practical standalone option, but it does not replace VIZIO firmware. CEC, wake, and automatic input behavior have not been verified.

## Community methods researched

The following public references were fetched over verified HTTPS:

- https://github.com/exiva/Vizio_SmartCast_API — port 7345, STATUS.RESULT, key commands, input HASHVAL behavior, settings metadata, and community app IDs.
- https://github.com/get-air/vizio — Conjure app ID 17 / namespace 4, hosted URL, current-input hash and target CNAME requirements.
- https://github.com/socialvibe/truex-ctv-web-reference-app/blob/develop/platforms/Vizio/README.md — HTML deployment on retail SmartCast 3; not proof for this exact firmware.

Bundled native references: Netflix (3,1), Prime (2,4), Hulu (2,3), Plex (2,9), WatchFree (2,22), FilmRise (2,24), DAZN (2,34). All remain experimental for this TV and region. Validate API acceptance, current-app identity, visible app display, and actual playback separately.

## Malaysia, WatchFree+, and Spotify

The legacy WatchFree ID does not establish access to today's WatchFree+ service in Malaysia. The status helper recognizes known current-app response shapes and reports matching, mismatching, or unknown identity without asserting screen or channel playback. No alternate IDs are brute-forced and no region/DRM/entitlement bypass is provided.

Spotify is an official website link only. Spotify Connect is conditional on the TV appearing in Spotify's device picker; support on this model is not established. RTM Klik and Astro AWANI are official Malaysian website links, not installed apps or extracted streams. Their old-TV-browser playback is unverified.

## Firmware and AirPlay research limits

Requests to the official model page https://www.vizio.com/en/tv/d-series/D40f-G9 and firmware information https://support.vizio.com/s/article/Firmware-Information?language=en_US were rejected by the cloud proxy with 403 Forbidden. Requests to VIZIO WatchFree+, RTM Klik, Astro AWANI, and the Apple AirPlay instructions were also denied. These are cloud access results, not evidence that the owner's network blocks these services or that vendor support has ended.

A newer compatible firmware or supported OS upgrade could neither be confirmed nor ruled out. No update image, verified recovery path, or firmware write was used. Ask official VIZIO support privately for the exact model/board/region compatibility and current official version; do not share serial numbers here or use firmware for a different model. A read-only settings snapshot is not a recovery backup.

AirPlay requires checking whether the TV appears in the Mac's Screen Mirroring list and observing a working image. It is not confirmed for this hardware/firmware. Mac HDMI mirroring also remains Mac-dependent; only an independent external player addresses the owner's standalone requirement with the available evidence.


## Owner-reported black screen

The owner reported a black screen after WatchFree and API acceptance of the old Home command without visible recovery. That output does not establish network, region, firmware, or panel failure. Community pyvizio source documents `/app/current` as singular ITEM.VALUE, and separate Home (4,15), SmartCast (4,3), and Menu (4,8). These formats/mappings have now been added and tested with mocks; real recovery on this device still requires observation. Missing dynamic setting metadata and an empty filtered input list are not proof of unsupported TV capabilities.
