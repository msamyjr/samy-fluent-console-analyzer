# Samy TV — English edition, recovery/protocol correction

[Complete ZIP](./Samy_Vizio_Modern_Home.zip?raw=true) · [Preview](./preview.png)

63 offline app tests, 4 updater tests, and both browser suites passed. The owner's black screen is not proven fixed by cloud simulations.

The current version reads singular ITEM.VALUE current-app responses; separates Home (4,15), SmartCast (4,3), Menu (4,8); lists inputs with missing enable flags read-only; and explains missing setting metadata.

## Update and diagnose without relaunching WatchFree

From the existing project folder, after stopping any running server:

```bash
curl -fL "https://github.com/msamyjr/samy-fluent-console-analyzer/raw/refs/heads/download/samy-vizio-modern-home/downloads/update.py" -o .samy_update.py &&
python3 .samy_update.py &&
python3 main.py key home &&
python3 main.py support
```

The updater preserves pairing and backs up app files. The support command only reads metadata; it does not launch an app or change settings. Do not repeatedly relaunch WatchFree while the screen is black. Physical Input and normal remote power off/on can be tried; never factory reset or flash firmware.

English interface and guides included. WatchFree+ availability in Malaysia, Spotify/website playback, and real TV recovery remain unverified. No DNS/network changes, DRM bypass, firmware replacement, or Google Play installation.

SHA-256: `df01e601e31bf8e8ada60823d07fda68fc69704c93d828671483e3a82a6cbefb`

## Firmware research

[Cross-model firmware investigation](./FIRMWARE_RESEARCH.md) — no compatible firmware candidate verified; official-source access blocked in the cloud.
