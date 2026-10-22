> Provenance: the text below is the supplied historical project prompt, not independent evidence of TV compatibility, a token leak, or completed device tests. The owner’s latest requirement is built-in operation without a Mac. That requirement is not achieved by this hosted HTML project; see COMPATIBILITY.md. Current user instructions take precedence.

# Paste this into Codex after opening the folder

You are engineering a local Vizio SmartCast 3 custom home project for the owner's Vizio D40f-G9, firmware 4.600.601.0-10, SCPL 3.0.12-2507.0002, Conjure MTKA-7.600.261.0-prod, VIZIOS MTK5581. The TV is reachable from the owner's Mac on 192.164.113.114:7345 and authenticated key commands work. The Mac is running Python 3.13. The owner will not open the TV case and does not have a firmware image or a verified recovery path.

Goal: improve and validate the included code so the Mac hosts a modern TV-friendly HTML interface and launches it using the documented SmartCast Conjure /app/launch mechanism. The result must be practical, beautiful, responsive to TV remote arrow/OK/back keys, and controllable from the Mac.

Rules:
1. Do not claim to replace or upgrade VIZIO firmware, install APKs, persist home-screen tiles, gain root, or bypass DRM/region restrictions without direct model-specific evidence.
2. Never flash, reset, change DNS/network settings, brute-force, exploit, or modify bootloader. Do not add arbitrary internal-API calls. Require separate verified backups and recovery strategy before even proposing firmware writes.
3. Never include pairing token in source, logs, reports, or commits. Keep `.vizio_local.json` private. The current token has been exposed and should be rotated through re-pairing.
4. Preserve Mac-local control API on 127.0.0.1 only. The LAN web server on port 8099 must be static/read-only and must not expose secrets or write APIs. Hostel Wi-Fi is open.
5. The actual TV address 192.164.113.114 is not RFC1918 private; don't reject it using is_private. Only communicate with explicitly configured TV host; no subnet scanning.
6. Use GET reads to discover capabilities and firmware details, verify STATUS.RESULT in every API response. Conjure launch uses `PUT /app/launch` with VALUE = {APP_ID:'17', NAME_SPACE:4, MESSAGE:'http://MAC_LAN_IP:8099/tv/'}. API success does not prove TV web rendering. Test TV-to-Mac reachability and user-visible display.
7. Improve app catalog with verified app IDs, separate known vs experimental. Native app launch success doesn't guarantee regional availability. Avoid unlicensed streams and DRM circumvention.
8. Add tests using mock TV responses; never require the actual TV to run unit tests. Redact serial, MAC, SSID, token, Netflix ESN and device IDs from diagnostics.
9. Preserve Python standard-library-only operation, and give precise macOS commands.
10. If Conjure fails, provide AirPlay fallback and a factual incompatibility report rather than inventing a firmware solution.

Work plan: (a) audit current code/security, (b) run offline tests, (c) add robust diagnostic/snapshot and connectivity troubleshooting, (d) refine the 1080p remote-friendly launcher, (e) document what works, what remains unverified, and an actionable next step requiring the owner's TV screen observation.
