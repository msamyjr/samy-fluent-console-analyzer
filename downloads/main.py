#!/usr/bin/env python3
"""Owner-operated SmartCast companion. Standard library only; no firmware writes."""
import argparse
import getpass
import hashlib
import hmac
import http.client
import ipaddress
import json
import os
import re
import secrets
import socket
import ssl
import sys
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SITE = ROOT / 'site'
CONFIG = ROOT / '.vizio_local.json'
REPORTS = ROOT / 'reports'
TV_PORT, CONTROL_PORT, SITE_PORT = 7345, 8766, 8099
DEFAULT_IP = '192.164.113.114'
MAX_RESPONSE = 2 * 1024 * 1024
KEYS = {
    'volume_up': (5, 1), 'volume_down': (5, 0), 'mute': (5, 4),
    'up': (3, 8), 'down': (3, 0), 'left': (3, 1), 'right': (3, 7),
    'ok': (3, 2), 'back': (4, 0), 'home': (4, 3), 'input': (7, 1),
}
APPS = {
    'netflix': {'NAME_SPACE': 3, 'APP_ID': '1', 'MESSAGE': ''},
    'prime': {'NAME_SPACE': 2, 'APP_ID': '4', 'MESSAGE': ''},
    'hulu': {'NAME_SPACE': 2, 'APP_ID': '3', 'MESSAGE': ''},
    'plex': {'NAME_SPACE': 2, 'APP_ID': '9', 'MESSAGE': ''},
    'watchfree': {'NAME_SPACE': 2, 'APP_ID': '22', 'MESSAGE': ''},
    'filmrise': {'NAME_SPACE': 2, 'APP_ID': '24', 'MESSAGE': ''},
    'dazn': {'NAME_SPACE': 2, 'APP_ID': '34', 'MESSAGE': ''},
}
READ_PATHS = {
    'device': '/state/device/deviceinfo', 'power': '/state/device/power_mode',
    'current_app': '/app/current',
    **{name: '/menu_native/dynamic/tv_settings/' + name for name in ('audio', 'picture', 'system')},
    'tv_information': '/menu_native/dynamic/tv_settings/system/system_information/tv_information',
    'current_input': '/menu_native/dynamic/tv_settings/devices/current_input',
    'inputs': '/menu_native/dynamic/tv_settings/devices/name_input',
}
# Only ordinary picture/audio leaves, never network/system/calibration/service settings.
SETTING_NAMES = {
    'picture': {'backlight', 'brightness', 'contrast', 'color', 'tint', 'sharpness', 'picture_mode'},
    'audio': {'bass', 'treble', 'balance'},
}
PRIVATE_MARKERS = ('TOKEN', 'AUTH', 'SERIAL', 'MAC', 'BSSID', 'SSID', 'ESN', 'DIID',
                   'DEVICE_ID', 'DEVICEID', 'DEVICE_INSTANCE', 'TVAD', 'IFA', 'UUID',
                   'GUID', 'UDN', 'DUID', 'ADVERTISING', 'IP_ADDRESS', 'GATEWAY', 'DNS',
                   'WIFI_NETWORKS', 'ACCESS_POINT', 'PASSWORD', 'SECRET')
TV_LOCK = threading.Lock()


class TVError(RuntimeError):
    def __init__(self, code='REQUEST_FAILED'):
        self.code = code if re.fullmatch(r'[A-Z_]{1,40}', str(code)) else 'API_ERROR'
        super().__init__('TV API: ' + self.code)


def check_ip(host):
    try:
        address = ipaddress.IPv4Address(host)
    except (ipaddress.AddressValueError, TypeError) as exc:
        raise ValueError('TV host must be a numeric IPv4 address') from exc
    if address.is_multicast or address.is_unspecified or address.is_loopback or address.is_reserved or int(address) >> 24 == 0:
        raise ValueError('TV host must be an ordinary unicast IPv4 address')
    return str(address)


def validate_token(token):
    if not isinstance(token, str) or not token or len(token) > 512 or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise ValueError('Invalid token; use the hidden setup prompt')
    return token


def read_config():
    if not CONFIG.exists():
        raise RuntimeError('No local configuration. Run: python3 main.py setup')
    if CONFIG.is_symlink() or CONFIG.stat().st_mode & 0o077:
        raise RuntimeError('Configuration must be a regular owner-only file (chmod 600 .vizio_local.json)')
    try:
        data = json.loads(CONFIG.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError()
        cfg = {'host': check_ip(data.get('host')), 'token': validate_token(data.get('token'))}
        pin = data.get('certificate_sha256')
        if pin is not None:
            if not isinstance(pin, str) or not re.fullmatch(r'[a-fA-F0-9]{64}', pin):
                raise ValueError()
            cfg['certificate_sha256'] = pin.lower()
        return cfg
    except (ValueError, TypeError) as exc:
        raise RuntimeError('Invalid local configuration; rerun setup') from exc


def private_json(destination, data):
    """Atomic replacement, owner-only at creation; never follow a destination symlink."""
    destination = Path(destination)
    if destination.is_symlink():
        raise RuntimeError('Refusing symbolic link destination')
    fd, name = tempfile.mkstemp(prefix='.samy-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, destination)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def save_config(host, token, certificate_sha256=None):
    data = {'host': check_ip(host), 'token': validate_token(token)}
    if certificate_sha256:
        if not re.fullmatch(r'[a-fA-F0-9]{64}', certificate_sha256):
            raise ValueError('Invalid certificate fingerprint')
        data['certificate_sha256'] = certificate_sha256.lower()
    private_json(CONFIG, data)


def pinned_context():
    # Chain validation is replaced by an exact certificate pin BEFORE sending AUTH.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def certificate_fingerprint(host):
    with socket.create_connection((check_ip(host), TV_PORT), timeout=8) as raw:
        with pinned_context().wrap_socket(raw, server_hostname=host) as tls:
            return hashlib.sha256(tls.getpeercert(binary_form=True)).hexdigest()


def tv_api(cfg, method, path, payload=None):
    """Direct fixed-host HTTPS: no environment proxies, redirects, or auth forwarding."""
    host = check_ip(cfg['host'])
    token = validate_token(cfg['token'])
    if method not in ('GET', 'PUT') or not re.fullmatch(r'/[a-zA-Z0-9_/-]+', path) or '..' in path or path.startswith('//'):
        raise ValueError('Invalid API request')
    pin = cfg.get('certificate_sha256')
    context = pinned_context() if pin else ssl.create_default_context()
    connection = http.client.HTTPSConnection(host, TV_PORT, timeout=8, context=context)
    try:
        connection.connect()
        if pin:
            actual = hashlib.sha256(connection.sock.getpeercert(binary_form=True)).hexdigest()
            if not hmac.compare_digest(actual, pin):
                raise TVError('CERTIFICATE_CHANGED')
        body = None if payload is None else json.dumps(payload, allow_nan=False).encode('utf-8')
        connection.request(method, path, body=body, headers={
            'AUTH': token, 'Content-Type': 'application/json', 'Accept': 'application/json',
        })
        response = connection.getresponse()
        if response.status != 200:
            raise TVError('HTTP_ERROR')
        raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise TVError('RESPONSE_TOO_LARGE')
        result = json.loads(raw)
        if not isinstance(result, dict) or not isinstance(result.get('STATUS'), dict):
            raise TVError('MALFORMED_RESPONSE')
        code = result['STATUS'].get('RESULT')
        if code != 'SUCCESS':
            # DETAIL may echo credentials or device identifiers: never display it.
            raise TVError(code)
        return result
    except TVError:
        raise
    except ssl.SSLCertVerificationError as exc:
        raise TVError('CERTIFICATE_UNTRUSTED') from exc
    except (OSError, http.client.HTTPException, ValueError) as exc:
        raise TVError('TRANSPORT_OR_JSON_ERROR') from exc
    finally:
        connection.close()


def read_state(cfg, section):
    if section not in READ_PATHS:
        raise ValueError('Unknown read-only section')
    return tv_api(cfg, 'GET', READ_PATHS[section])


def items_of(data):
    items = data.get('ITEMS')
    if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
        raise TVError('MALFORMED_ITEMS')
    return items


def device_info(data):
    items = items_of(data)
    if not items or not isinstance(items[0].get('VALUE'), dict):
        raise TVError('MALFORMED_DEVICE_INFO')
    return items[0]['VALUE']


def send_key(cfg, name):
    if not isinstance(name, str) or name not in KEYS:
        raise ValueError('Unsupported key')
    codeset, code = KEYS[name]
    return tv_api(cfg, 'PUT', '/key_command/', {'KEYLIST': [
        {'CODESET': codeset, 'CODE': code, 'ACTION': 'KEYPRESS'}]})


def launch_app(cfg, name):
    if not isinstance(name, str) or name not in APPS:
        raise ValueError('Unknown app name')
    return tv_api(cfg, 'PUT', '/app/launch', {'VALUE': APPS[name]})


def local_ip_for(host):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect((check_ip(host), TV_PORT))  # Route selection only, no UDP packet sent.
        return sock.getsockname()[0]


def launch_conjure(cfg, url):
    parsed = urlparse(url)
    if (parsed.scheme != 'http' or not parsed.hostname or parsed.port != SITE_PORT
            or parsed.username or parsed.password or parsed.path != '/tv/'
            or parsed.query or parsed.fragment):
        raise ValueError('Launcher URL must be the Mac HTTP /tv/ URL on port 8099')
    check_ip(parsed.hostname)
    if parsed.hostname != local_ip_for(cfg['host']):
        raise ValueError('Launcher URL must match the local interface used to reach the configured TV')
    return tv_api(cfg, 'PUT', '/app/launch', {'VALUE': {
        'MESSAGE': url, 'NAME_SPACE': 4, 'APP_ID': '17'}})


def redact(value, parent=''):
    name = re.sub(r'[^A-Z0-9]', '_', parent.upper())
    if any(marker in name for marker in PRIVATE_MARKERS) or name in ('DID', 'UID', 'IP'):
        return '[REDACTED]'
    if isinstance(value, dict):
        labels = ' '.join(str(value.get(k, '')) for k in ('CNAME', 'NAME', 'KEY', 'LABEL'))
        sensitive = redact('', labels) == '[REDACTED]'
        return {k: ('[REDACTED]' if sensitive and k not in ('CNAME', 'NAME', 'TYPE', 'KEY', 'LABEL')
                    else redact(v, k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, parent) for v in value]
    if isinstance(value, str):
        value = re.sub(r'(?i)\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b', '[REDACTED]', value)
        value = re.sub(r'\b\d{1,3}(?:\.\d{1,3}){3}\b', '[REDACTED]', value)
    return value


def redact_for_config(cfg, data):
    """Scrub exact credentials before JSON encoding, including escaped tokens."""
    token = cfg.get('token', '') if cfg else ''
    def scrub(value):
        if isinstance(value, str):
            return value.replace(token, '[REDACTED]') if token else value
        if isinstance(value, dict):
            return {scrub(k): scrub(v) for k, v in value.items()}
        if isinstance(value, list):
            return [scrub(v) for v in value]
        return value
    return scrub(redact(data))


def safe_identity(info):
    # Allowlist instead of dumping firmware-dependent identifiers.
    system = info.get('SYSTEM_INFO')
    binaries = info.get('BINARIES')
    return {'model': info.get('MODEL_NAME'), 'firmware': system.get('VERSION') if isinstance(system, dict) else None,
            'api': info.get('API_VERSION'), 'conjure': binaries.get('CONJURE') if isinstance(binaries, dict) else None}


def input_options(cfg):
    result = []
    for item in items_of(read_state(cfg, 'inputs')):
        cname = item.get('CNAME')
        if not isinstance(cname, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,50}', cname) or item.get('ENABLED') is not True:
            continue
        value = item.get('VALUE')
        label = value.get('NAME') if isinstance(value, dict) else item.get('NAME')
        result.append({'id': cname, 'name': str(label or cname)[:80]})
    return result


def set_input(cfg, target):
    if target not in [i['id'] for i in input_options(cfg)]:
        raise ValueError('Input not advertised as enabled by TV')
    items = items_of(read_state(cfg, 'current_input'))
    if not items or type(items[0].get('HASHVAL')) is not int:
        raise TVError('MISSING_HASHVAL')
    # Fresh current-input HASHVAL, target CNAME, never a list-item HASHVAL.
    return tv_api(cfg, 'PUT', READ_PATHS['current_input'], {
        'REQUEST': 'MODIFY', 'VALUE': target, 'HASHVAL': items[0]['HASHVAL']})


def setting_spec(item):
    if item.get('ENABLED') is not True or item.get('READONLY') or type(item.get('HASHVAL')) is not int:
        return None
    elements = item.get('ELEMENTS')
    if isinstance(elements, list) and elements and all(isinstance(v, (str, int, bool)) for v in elements):
        return {'kind': 'enum', 'choices': elements}
    # Do not invent ranges or assume a firmware TYPE. Unknown schemas stay read-only.
    low, high = item.get('MINIMUM'), item.get('MAXIMUM')
    step = item.get('INCREMENT', 1)
    if (type(low) is int and type(high) is int and low < high and type(step) is int and step > 0
            and type(item.get('VALUE')) is int):
        return {'kind': 'integer', 'min': low, 'max': high, 'step': step}
    return None


def settings_options(cfg, group):
    if group not in SETTING_NAMES:
        raise ValueError('Only picture and audio settings are permitted')
    result = []
    for item in items_of(read_state(cfg, group)):
        if item.get('CNAME') in SETTING_NAMES[group]:
            result.append({'id': item['CNAME'], 'name': str(item.get('NAME') or item['CNAME']),
                           'value': item.get('VALUE'), 'spec': setting_spec(item),
                           'note': 'Unknown or disabled metadata means read-only'})
    return result


def set_setting(cfg, group, name, value):
    if group not in SETTING_NAMES or name not in SETTING_NAMES[group]:
        raise ValueError('Setting is not allowlisted')
    for attempt in range(2):
        candidates = [i for i in items_of(read_state(cfg, group)) if i.get('CNAME') == name]
        item = candidates[0] if len(candidates) == 1 else {}
        spec = setting_spec(item)
        if not spec:
            raise ValueError('TV did not advertise safe writable metadata')
        if spec['kind'] == 'enum':
            valid = any(type(value) is type(v) and value == v for v in spec['choices'])
        else:
            valid = type(value) is int and spec['min'] <= value <= spec['max'] and (value - spec['min']) % spec['step'] == 0
        if not valid:
            raise ValueError('Value does not match advertised choices or range')
        try:
            return tv_api(cfg, 'PUT', READ_PATHS[group] + '/' + name, {
                'REQUEST': 'MODIFY', 'HASHVAL': item['HASHVAL'], 'VALUE': value})
        except TVError as exc:
            if exc.code != 'HASHVAL_ERROR' or attempt:
                raise


def setup(host, trust_on_first_use=False, certificate_sha256=None):
    host = check_ip(host)
    pin = certificate_sha256
    if pin and not re.fullmatch(r'[a-fA-F0-9]{64}', pin):
        raise ValueError('SHA-256 fingerprint must contain 64 hex digits')
    if trust_on_first_use:
        pin = certificate_fingerprint(host)
        print('Certificate SHA-256:', pin)
        print('First-use trust cannot establish identity on a hostile Wi-Fi network.')
        if input('Trust this exact TV certificate? Type TRUST: ').strip() != 'TRUST':
            raise RuntimeError('Certificate not trusted; no token sent')
    token = validate_token(getpass.getpass('Vizio AUTH token (hidden): ').strip())
    cfg = {'host': host, 'token': token}
    if pin:
        cfg['certificate_sha256'] = pin.lower()
    info = device_info(read_state(cfg, 'device'))
    if info.get('MODEL_NAME') != 'D40f-G9':
        raise RuntimeError('Model mismatch: expected D40f-G9; configuration not saved')
    save_config(host, token, pin)
    print('Authenticated D40f-G9; configuration saved with owner-only permissions.')


def diagnose(cfg):
    print(json.dumps(redact_for_config(cfg, safe_identity(device_info(read_state(cfg, 'device')))), ensure_ascii=False, indent=2))
    print('Authenticated read succeeded; this does not validate firmware upgrades or HTML rendering.')


def snapshot(cfg):
    REPORTS.mkdir(exist_ok=True, mode=0o700)
    output = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'real_tv_test': True, 'sections': {}}
    for name in READ_PATHS:
        try:
            output['sections'][name] = redact(read_state(cfg, name))
            print(name, 'read succeeded')
        except RuntimeError as exc:
            output['sections'][name] = {'error': str(exc)}
            print(name, 'unavailable')
    # Also scrub exact auth string even if returned under an unknown firmware field.
    output = redact_for_config(cfg, output)
    destination = REPORTS / ('vizio_readonly_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f') + '.json')
    private_json(destination, output)
    print('Private redacted report:', destination.name, '(not a firmware backup; inspect locally before sharing)')


STATIC = {'/tv/': ('index.html', 'text/html'), '/tv/index.html': ('index.html', 'text/html'),
          '/tv/styles.css': ('styles.css', 'text/css'), '/tv/app.js': ('app.js', 'text/javascript'),
          '/tv/catalog.json': ('catalog.json', 'application/json')}


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class BaseHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def reply(self, status, body, ctype='application/json'):
        if isinstance(body, str):
            body = body.encode('utf-8')
        elif not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', ctype + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass  # Never log URL, body, identifiers, or token.

    def static(self, path):
        if path not in STATIC:
            return self.reply(404, {'ok': False, 'error': 'Not found'})
        name, mime = STATIC[path]
        try:
            body = (SITE / name).read_bytes()
        except OSError:
            return self.reply(404, {'ok': False, 'error': 'Static file unavailable'})
        self.reply(200, body, mime)


class SiteHandler(BaseHandler):
    """LAN allowlist contains only public assets. No control, proxy, or secrets."""
    def do_GET(self):
        path = urlparse(self.path).path
        observation = getattr(self.server, 'observation', None)
        if observation is not None and self.client_address[0] == self.server.tv_host and path in ('/', '/tv/', '/tv/index.html'):
            observation['tv_page_requested_at_utc'] = datetime.now(timezone.utc).isoformat()
        self.static('/tv/' if path == '/' else path)

    def do_POST(self):
        self.reply(405, {'ok': False, 'error': 'Static read-only host'})

    do_PUT = do_DELETE = do_PATCH = do_POST


class ControlHandler(BaseHandler):
    cfg = None
    csrf = ''

    def trusted(self):
        port = self.server.server_port
        hosts = ('127.0.0.1:' + str(port), 'localhost:' + str(port))
        if self.headers.get('Host') not in hosts:
            self.reply(403, {'ok': False, 'error': 'Forbidden host'})
            return False
        origin = self.headers.get('Origin')
        if origin and origin not in tuple('http://' + h for h in hosts):
            self.reply(403, {'ok': False, 'error': 'Forbidden origin'})
            return False
        # A link from another site may open the dashboard document. It cannot
        # read its session or call APIs: those requests still require same-origin.
        document_navigation = (
            self.command == 'GET' and self.path == '/'
            and self.headers.get('Sec-Fetch-Mode') == 'navigate'
            and self.headers.get('Sec-Fetch-Dest') == 'document'
        )
        if self.headers.get('Sec-Fetch-Site') in ('cross-site', 'same-site') and not document_navigation:
            self.reply(403, {'ok': False, 'error': 'Same-origin access required'})
            return False
        return True

    def require_cfg(self):
        if not self.cfg:
            raise RuntimeError('Offline preview: no TV connected. Run setup on your Mac.')

    def scrub(self, data):
        # JSON round trip replaces exact token regardless of the TV's field names.
        return redact_for_config(self.cfg, data)

    def do_GET(self):
        if not self.trusted():
            return
        path = urlparse(self.path).path
        try:
            if path == '/':
                return self.reply(200, (SITE / 'controller.html').read_bytes(), 'text/html')
            if path in STATIC:
                return self.static(path)
            if path == '/api/session':
                return self.reply(200, {'ok': True, 'csrf': self.csrf, 'offline': self.cfg is None})
            if path == '/api/diagnostics':
                return self.reply(200, {'ok': True, 'data': {**self.server.observation,
                    'note': 'A page request from the configured IP proves an HTTP request only, not visible rendering or working remote events.'}})
            self.require_cfg()
            with TV_LOCK:
                if path == '/api/status':
                    data = safe_identity(device_info(read_state(self.cfg, 'device')))
                elif path == '/api/inputs':
                    data = input_options(self.cfg)
                elif path.startswith('/api/settings/'):
                    data = settings_options(self.cfg, path.rsplit('/', 1)[-1])
                elif path.startswith('/api/read/'):
                    data = read_state(self.cfg, path.rsplit('/', 1)[-1])
                else:
                    return self.reply(404, {'ok': False, 'error': 'Not found'})
            self.reply(200, {'ok': True, 'data': self.scrub(data)})
        except (ValueError, RuntimeError, OSError):
            self.reply(502, {'ok': False, 'error': 'TV read unavailable. Check setup or run diagnose locally.'})

    def do_POST(self):
        if not self.trusted():
            return
        if not self.csrf or not hmac.compare_digest(self.headers.get('X-Samy-CSRF', '').encode('utf-8'), self.csrf.encode('ascii')):
            return self.reply(403, {'ok': False, 'error': 'Missing session protection'})
        if self.path not in ('/api/key', '/api/app', '/api/conjure', '/api/input', '/api/setting'):
            return self.reply(404, {'ok': False, 'error': 'Not found'})
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            return self.reply(415, {'ok': False, 'error': 'JSON required'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2048:
                raise ValueError()
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError()
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError()
            self.require_cfg()
            with TV_LOCK:
                if self.path == '/api/key':
                    result = send_key(self.cfg, data.get('key'))
                elif self.path == '/api/app':
                    result = launch_app(self.cfg, data.get('app'))
                elif self.path == '/api/input':
                    result = set_input(self.cfg, data.get('input'))
                elif self.path == '/api/setting':
                    result = set_setting(self.cfg, data.get('group'), data.get('name'), data.get('value'))
                else:
                    result = launch_conjure(self.cfg, 'http://%s:%d/tv/' % (local_ip_for(self.cfg['host']), SITE_PORT))
            self.reply(200, {'ok': True, 'result': result['STATUS']['RESULT'],
                             'note': 'API accepted only; verify the TV screen/state.'})
        except (ValueError, TypeError, KeyError, RuntimeError, OSError):
            self.reply(400, {'ok': False, 'error': 'Command rejected or TV unavailable. Read capabilities / run diagnose locally.'})


def make_servers(cfg):
    handler = type('SessionControlHandler', (ControlHandler,), {'cfg': cfg, 'csrf': secrets.token_urlsafe(32)})
    control = Server(('127.0.0.1', CONTROL_PORT), handler)
    try:
        site = Server(('0.0.0.0', SITE_PORT), SiteHandler)
    except OSError:
        control.server_close()
        raise
    observation = {'tv_page_requested_at_utc': None}
    control.observation = site.observation = observation
    site.tv_host = cfg['host'] if cfg else None
    return control, site


def serve(cfg=None, launch=False):
    control, site = make_servers(cfg)
    servers = (control, site)
    threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in servers]
    for thread in threads:
        thread.start()
    try:
        print('Mac control: http://127.0.0.1:%d/' % CONTROL_PORT)
        print('Local preview: http://127.0.0.1:%d/tv/' % SITE_PORT)
        print('LAN port 8099 is STATIC ONLY; stop with Control+C.')
        if cfg:
            url = 'http://%s:%d/tv/' % (local_ip_for(cfg['host']), SITE_PORT)
            print('TV URL:', url)
            if launch:
                try:
                    launch_conjure(cfg, url)
                    print('Conjure API accepted. Screen rendering and remote events still require observation.')
                except RuntimeError as exc:
                    print(str(exc), '— control remains available. Use AirPlay fallback if unsupported.')
        else:
            print('OFFLINE preview; no commands can be sent to a TV.')
        threading.Event().wait()
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('setup')
    p.add_argument('ip', nargs='?', default=DEFAULT_IP)
    trust = p.add_mutually_exclusive_group()
    trust.add_argument('--trust-on-first-use', action='store_true')
    trust.add_argument('--certificate-sha256')
    for name in ('diagnose', 'snapshot', 'preview', 'launch', 'catalog'):
        sub.add_parser(name)
    p = sub.add_parser('key'); p.add_argument('name', choices=sorted(KEYS))
    p = sub.add_parser('app'); p.add_argument('name', choices=sorted(APPS))
    p = sub.add_parser('read'); p.add_argument('section', choices=sorted(READ_PATHS))
    p = sub.add_parser('input'); p.add_argument('name', nargs='?')
    p = sub.add_parser('settings'); p.add_argument('group', choices=sorted(SETTING_NAMES))
    p = sub.add_parser('set'); p.add_argument('group', choices=sorted(SETTING_NAMES)); p.add_argument('name'); p.add_argument('value', help='JSON value, e.g. 50 or \"Calibrated\"')
    args = parser.parse_args()
    try:
        if args.command == 'setup':
            return setup(args.ip, args.trust_on_first_use, args.certificate_sha256)
        if args.command == 'catalog':
            return print((SITE / 'catalog.json').read_text(encoding='utf-8'))
        if args.command == 'preview':
            return serve(read_config() if CONFIG.exists() else None)
        cfg = read_config()
        if args.command == 'launch':
            return serve(cfg, launch=True)
        if args.command == 'diagnose':
            return diagnose(cfg)
        if args.command == 'snapshot':
            return snapshot(cfg)
        if args.command == 'key':
            send_key(cfg, args.name)
            return print('Key accepted; verify on TV.')
        if args.command == 'app':
            launch_app(cfg, args.name)
            print('App launch API accepted; check TV, then run: python3 main.py read current_app')
            return
        if args.command == 'input':
            result = input_options(cfg) if args.name is None else set_input(cfg, args.name)
        elif args.command == 'settings':
            result = settings_options(cfg, args.group)
        elif args.command == 'set':
            result = set_setting(cfg, args.group, args.name, json.loads(args.value))
        else:
            result = read_state(cfg, args.section)
        print(json.dumps(redact_for_config(cfg, result), ensure_ascii=False, indent=2))
    except TVError as exc:
        print(str(exc), file=sys.stderr)
        if exc.code == 'CERTIFICATE_UNTRUSTED':
            print('Use setup --certificate-sha256 with a known fingerprint, or explicitly opt into --trust-on-first-use on your Mac. Never ignore a changed certificate.', file=sys.stderr)
        return 1
    except (RuntimeError, ValueError, OSError, TypeError):
        print('ERROR: Operation failed. Check configuration permissions, certificate trust, TV availability, and advertised capabilities. No sensitive TV detail was printed.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
