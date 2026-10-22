# Samy Home — Google TV-inspired launcher

[Download ZIP](./Samy_Vizio_Modern_Home.zip?raw=true) · [Preview](./preview.png) · [Real-device compatibility](./DEVICE_COMPATIBILITY.md)

English TV home screen, protected Mac dashboard, searchable app rows, favorites, remote-event check, and separate Conjure API / TV asset-request observations. Native Wi-Fi and DNS remain unchanged. No firmware flashing or native APK support.

This checkout originally contained main.py but no launcher.py. The new launcher.py delegates to the existing backend. A different launcher.py on the owner's Mac was not available for inspection.

## Update an existing project

Stop its server with Control+C. From the project folder:

```bash
curl -fL "https://github.com/msamyjr/samy-fluent-console-analyzer/raw/refs/heads/download/samy-vizio-modern-home/downloads/update.py" -o .samy_update.py &&
python3 .samy_update.py &&
python3 launcher.py preview
```

The updater verifies SHA-256, backs up replaced application files, and preserves private pairing. From a second terminal in the project directory, run `python3 launcher.py check`. To request Conjure explicitly, stop preview and run `python3 launcher.py launch`, or use the dashboard.

73 offline app tests, 4 updater tests, and both browser suites passed. Cloud tests do not establish real-TV compatibility. Owner-confirmed pairing/settings reads and the WatchFree black screen are documented separately. Native commands remain on the loopback dashboard; LAN assets are read-only. The server must stay running.

For exact device steps and limitations, read README.md and DEVICE_COMPATIBILITY.md inside the ZIP.

Archive SHA-256: `c0eee8be661e48ed2995a31e66f028c68aecf4c9a7b328f75fb60fe6bb5a3b95`

[Earlier cross-model firmware investigation](./FIRMWARE_RESEARCH.md): no compatible firmware image was verified.
