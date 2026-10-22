# Samy TV — English edition

[Download the complete ZIP](./Samy_Vizio_Modern_Home.zip?raw=true) · [Preview the English interface](./preview.png)

English TV page and Mac dashboard, left-to-right navigation, app rows, search, favorites, status/errors, and accessibility labels. The package includes English setup, compatibility, validation, and real-device guides.

55 offline app tests, 4 updater tests, and both browser suites passed. No cloud test establishes real-TV playback. WatchFree+ in Malaysia and Spotify playback/Connect remain unverified. Website links are not native app installations; no Google Play or firmware replacement is provided.

## Update an existing installation

Stop your server with Control+C. From the project folder containing main.py and site/:

```bash
curl -fL "https://github.com/msamyjr/samy-fluent-console-analyzer/raw/refs/heads/download/samy-vizio-modern-home/downloads/update.py" -o .samy_update.py &&
python3 .samy_update.py &&
python3 main.py launch
```

The updater checks SHA-256 and backs up application files. It does not read or change your private TV config; no new setup or AUTH entry is needed. Old Arabic documentation is preserved in existing installations; README.md is now the English guide.

Archive SHA-256: `6c044d12338b9157b325176375bf07efae06cf3da645c353302e63134b3b833e`
