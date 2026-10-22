"""Offline tests: TV transport is mocked; only local HTTP servers are real."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
import main

OK = {'STATUS': {'RESULT': 'SUCCESS'}}
CFG = {'host': main.DEFAULT_IP, 'token': 'test-only-not-a-real-token'}


def result(items):
    return {**OK, 'ITEMS': items}


class TransportTests(unittest.TestCase):
    def call(self, body=OK, status=200, cfg=CFG):
        connection = Mock()
        connection.getresponse.return_value.status = status
        connection.getresponse.return_value.read.return_value = json.dumps(body).encode()
        with patch.object(main.http.client, 'HTTPSConnection', return_value=connection):
            value = main.tv_api(cfg, 'GET', '/app/current')
        return value, connection

    def test_status_success(self):
        value, connection = self.call()
        self.assertEqual(value, OK)
        self.assertEqual(connection.request.call_args.kwargs['headers']['AUTH'], CFG['token'])
        connection.close.assert_called_once()

    def test_bad_status_shapes(self):
        for data in ([], {}, {'STATUS': []}, {'STATUS': None}, {'STATUS': {'RESULT': 'FAILURE', 'DETAIL': CFG['token']}}):
            with self.subTest(data=data), self.assertRaises(main.TVError) as context:
                self.call(data)
            self.assertNotIn(CFG['token'], str(context.exception))

    def test_redirect_never_followed(self):
        with self.assertRaises(main.TVError):
            self.call(status=302)

    def test_pin_checked_before_auth(self):
        connection = Mock()
        connection.sock.getpeercert.return_value = b'unexpected certificate'
        with patch.object(main.http.client, 'HTTPSConnection', return_value=connection):
            with self.assertRaisesRegex(main.TVError, 'CERTIFICATE_CHANGED'):
                main.tv_api({**CFG, 'certificate_sha256': '0' * 64}, 'GET', '/app/current')
        connection.request.assert_not_called()
        connection.close.assert_called_once()

    def test_matching_pin_allows_request(self):
        connection = Mock()
        cert = b'mocked certificate'
        connection.sock.getpeercert.return_value = cert
        connection.getresponse.return_value.status = 200
        connection.getresponse.return_value.read.return_value = json.dumps(OK).encode()
        with patch.object(main.http.client, 'HTTPSConnection', return_value=connection):
            self.assertEqual(main.tv_api({**CFG, 'certificate_sha256': hashlib.sha256(cert).hexdigest()}, 'GET', '/app/current'), OK)
        connection.request.assert_called_once()

    def test_invalid_json_and_large_reply(self):
        for raw in (b'not json', b'x' * (main.MAX_RESPONSE + 1)):
            connection = Mock()
            connection.getresponse.return_value.status = 200
            connection.getresponse.return_value.read.return_value = raw
            with patch.object(main.http.client, 'HTTPSConnection', return_value=connection), self.assertRaises(main.TVError):
                main.tv_api(CFG, 'GET', '/app/current')

    def test_no_path_or_host_injection(self):
        for path in ('//attacker/path', '/app/current?token=x', '/app/../network', 'https://attacker'):
            with self.assertRaises(ValueError):
                main.tv_api(CFG, 'GET', path)
        for host in ('127.0.0.1', '0.0.0.0', '224.1.2.3', 'example.com', '192.164.113.114@evil'):
            with self.assertRaises(ValueError):
                main.check_ip(host)

    def test_token_cannot_inject_header(self):
        for token in ('', 'abc\r\nX:evil', 'a b', 'é'):
            with self.assertRaises(ValueError):
                main.validate_token(token)


class ConfigTests(unittest.TestCase):
    def test_private_config_atomic_save_and_read(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(main, 'CONFIG', Path(directory) / 'config'):
            main.save_config(CFG['host'], CFG['token'], 'a' * 64)
            self.assertEqual(main.CONFIG.stat().st_mode & 0o777, 0o600)
            self.assertEqual(main.read_config()['token'], CFG['token'])
            main.CONFIG.chmod(0o644)
            with self.assertRaises(RuntimeError):
                main.read_config()

    def test_config_symlink_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'target'; target.write_text('preserve')
            config = Path(directory) / 'link'; config.symlink_to(target)
            with patch.object(main, 'CONFIG', config), self.assertRaises(RuntimeError):
                main.save_config(CFG['host'], CFG['token'])
            self.assertEqual(target.read_text(), 'preserve')

    def test_escaped_token_redacted_before_json_encoding(self):
        token = 'test"quoted\\value'
        data = {'unknown': 'prefix ' + token, token: [token]}
        output = main.redact_for_config({'token': token}, data)
        self.assertEqual(output['unknown'], 'prefix [REDACTED]')
        self.assertEqual(output['[REDACTED]'], ['[REDACTED]'])

    def test_nested_redaction(self):
        data = {'device-id': 'private-id', 'ITEMS': [{'CNAME': 'wifi_ssid', 'VALUE': {'value': 'secret network'}, 'ELEMENTS': ['secret network']}], 'text': 'aa:bb:cc:dd:ee:ff 10.1.2.3', 'MODEL_NAME': 'D40f-G9'}
        output = json.dumps(main.redact(data))
        for secret in ('private-id', 'secret network', 'aa:bb:cc:dd:ee:ff', '10.1.2.3'):
            self.assertNotIn(secret, output)
        self.assertIn('D40f-G9', output)

    def test_snapshot_exact_token_scrubbed_and_private(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(main, 'REPORTS', Path(directory)), patch.object(main, 'read_state', return_value={**OK, 'unknown': CFG['token']}):
            main.snapshot(CFG)
            reports = list(Path(directory).glob('*.json'))
            self.assertEqual(len(reports), 1)
            self.assertNotIn(CFG['token'], reports[0].read_text())
            self.assertEqual(reports[0].stat().st_mode & 0o777, 0o600)


class CapabilityTests(unittest.TestCase):
    def test_home_smartcast_and_menu_are_distinct_commands(self):
        for name, code in (('home', 15), ('smartcast', 3), ('menu', 8)):
            with patch.object(main, 'tv_api', return_value=OK) as api:
                main.send_key(CFG, name)
            self.assertEqual(api.call_args.args[3]['KEYLIST'][0], {'CODESET': 4, 'CODE': code, 'ACTION': 'KEYPRESS'})

    def test_inputs_without_enable_flag_remain_visible_read_only(self):
        with patch.object(main, 'read_state', return_value=result([{'CNAME': 'HDMI-1', 'VALUE': {'NAME': 'HDMI 1'}}])):
            options = main.input_options(CFG)
        self.assertEqual(options[0]['id'], 'HDMI-1')
        self.assertIsNone(options[0]['enabled'])
        self.assertFalse(options[0]['writable'])

    def test_readonly_input_is_not_switched(self):
        with patch.object(main, 'tv_api', return_value=result([{'CNAME': 'HDMI-1'}])) as api:
            with self.assertRaises(ValueError): main.set_input(CFG, 'HDMI-1')
        api.assert_called_once_with(CFG, 'GET', main.READ_PATHS['inputs'])

    def test_setting_reason_identifies_missing_metadata(self):
        self.assertIn('HASHVAL', main.setting_readonly_reason({'ENABLED': True}))
        self.assertIn('ENABLED', main.setting_readonly_reason({}))
        self.assertIn('range or choices', main.setting_readonly_reason({'ENABLED': True, 'HASHVAL': 1}))

    def test_support_report_is_readonly_and_excludes_values(self):
        response = {**OK, 'ITEM': {'VALUE': {'APP_ID': '22', 'NAME_SPACE': 2}}, 'ITEMS': [
            {'CNAME': 'brightness', 'TYPE': 'T_SLIDER', 'HASHVAL': 9, 'VALUE': 'private sentinel', 'ENABLED': True}]}
        with patch.object(main, 'tv_api', return_value=response) as api:
            report = main.support_report(CFG)
        self.assertTrue(report['read_only'])
        self.assertEqual(report['sections']['current_app']['identity']['APP_ID'], '22')
        self.assertEqual(api.call_count, 4)
        self.assertTrue(all(c.args[1] == 'GET' for c in api.call_args_list))
        self.assertNotIn('private sentinel', json.dumps(report))

    def test_mute_is_toggle_not_mute_off(self):
        with patch.object(main, 'tv_api', return_value=OK) as api:
            main.send_key(CFG, 'mute')
        self.assertEqual(api.call_args.args[3]['KEYLIST'][0]['CODE'], 4)

    def test_current_input_hash_not_input_list_hash(self):
        responses = [result([{'CNAME': 'HDMI-2', 'NAME': 'Friendly name', 'ENABLED': True, 'HASHVAL': 1}]), result([{'HASHVAL': 99}]), OK]
        with patch.object(main, 'tv_api', side_effect=responses) as api:
            main.set_input(CFG, 'HDMI-2')
        self.assertEqual(api.call_args.args[3], {'REQUEST': 'MODIFY', 'VALUE': 'HDMI-2', 'HASHVAL': 99})

    def test_missing_input_hash_no_write(self):
        with patch.object(main, 'tv_api', side_effect=[result([{'CNAME': 'HDMI-1', 'ENABLED': True}]), result([{}])]) as api:
            with self.assertRaises(main.TVError): main.set_input(CFG, 'HDMI-1')
        self.assertTrue(all(c.args[1] == 'GET' for c in api.call_args_list))

    def test_unadvertised_input_no_write(self):
        with patch.object(main, 'tv_api', return_value=result([])) as api:
            with self.assertRaises(ValueError): main.set_input(CFG, 'HDMI-999')
        api.assert_called_once()

    def item(self, **changes):
        return {'CNAME': 'brightness', 'ENABLED': True, 'HASHVAL': 12, 'VALUE': 50, 'MINIMUM': 0, 'MAXIMUM': 100, 'INCREMENT': 1, **changes}

    def test_valid_setting_uses_fresh_hash(self):
        with patch.object(main, 'tv_api', side_effect=[result([self.item()]), OK]) as api:
            main.set_setting(CFG, 'picture', 'brightness', 51)
        self.assertEqual(api.call_args.args[3], {'REQUEST': 'MODIFY', 'HASHVAL': 12, 'VALUE': 51})

    def test_unsafe_settings_rejected(self):
        for value in (-1, 101, True, '50', 1.5, float('nan')):
            with patch.object(main, 'tv_api', return_value=result([self.item()])) as api:
                with self.assertRaises(ValueError): main.set_setting(CFG, 'picture', 'brightness', value)
            self.assertEqual(api.call_count, 1)
        with patch.object(main, 'tv_api') as api, self.assertRaises(ValueError):
            main.set_setting(CFG, 'system', 'factory_reset', 'yes')
        api.assert_not_called()

    def test_unknown_or_disabled_metadata_read_only(self):
        for item in (self.item(ENABLED=False), self.item(HASHVAL=None), self.item(MINIMUM=None), self.item(READONLY=True)):
            self.assertIsNone(main.setting_spec(item))

    def test_enum_types_match_exactly(self):
        item = self.item(ELEMENTS=[1, 2])
        with patch.object(main, 'tv_api', return_value=result([item])), self.assertRaises(ValueError):
            main.set_setting(CFG, 'picture', 'brightness', True)

    def test_hash_error_refetch_once(self):
        replies = [result([self.item()]), main.TVError('HASHVAL_ERROR'), result([self.item(HASHVAL=13)]), OK]
        with patch.object(main, 'tv_api', side_effect=replies) as api:
            main.set_setting(CFG, 'picture', 'brightness', 51)
        self.assertEqual(api.call_count, 4)
        self.assertEqual(api.call_args.args[3]['HASHVAL'], 13)

    def test_hash_error_does_not_loop(self):
        with patch.object(main, 'tv_api', side_effect=[result([self.item()]), main.TVError('HASHVAL_ERROR'), result([self.item()]), main.TVError('HASHVAL_ERROR')]) as api:
            with self.assertRaises(main.TVError): main.set_setting(CFG, 'picture', 'brightness', 51)
        self.assertEqual(api.call_count, 4)

    def test_conjure_requires_actual_local_interface(self):
        with patch.object(main, 'local_ip_for', return_value='10.0.0.5'), patch.object(main, 'tv_api') as api:
            for url in ('http://attacker:8099/tv/', 'http://10.0.0.6:8099/tv/', 'http://u:p@10.0.0.5:8099/tv/', 'http://10.0.0.5:8099/tv/?x=1'):
                with self.assertRaises(ValueError): main.launch_conjure(CFG, url)
        api.assert_not_called()


class HTTPTests(unittest.TestCase):
    def setUp(self):
        handler = type('TestControl', (main.ControlHandler,), {'cfg': CFG, 'csrf': 'test-session-protection'})
        self.control = main.Server(('127.0.0.1', 0), handler)
        self.control.observation = {'tv_page_requested_at_utc': None}
        self.site = main.Server(('127.0.0.1', 0), main.SiteHandler)
        self.threads = []
        for server in (self.control, self.site):
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start(); self.threads.append(thread)

    def tearDown(self):
        for server in (self.control, self.site): server.shutdown(); server.server_close()
        for thread in self.threads: thread.join(2)

    def req(self, path, body=None, server=None, headers=None, method=None):
        server = server or self.control
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=4)
        h = {'Content-Type': 'application/json', 'X-Samy-CSRF': 'test-session-protection'}
        if headers: h.update(headers)
        connection.request(method or ('GET' if body is None else 'POST'), path, body=body, headers=h)
        response = connection.getresponse(); value = response.read(); status = response.status
        connection.close(); return status, value

    def test_real_static_routes_and_secret_exclusion(self):
        for route in ('/tv/', '/tv/app.js', '/tv/styles.css', '/tv/catalog.json', '/tv/landscape.svg'):
            status, body = self.req(route, server=self.site)
            self.assertEqual(status, 200); self.assertNotIn(CFG['token'].encode(), body)
        for route in ('/.vizio_local.json', '/main.py', '/tv/../main.py', '/api/session', '/tv/controller.html', '/reports/test.json'):
            self.assertEqual(self.req(route, server=self.site)[0], 404)
        self.assertEqual(self.req('/api/key', '{}', server=self.site)[0], 405)

    def test_controller_session_does_not_expose_tv_auth(self):
        status, body = self.req('/api/session')
        self.assertEqual(status, 200); self.assertNotIn(CFG['token'].encode(), body)
        self.assertEqual(json.loads(body)['csrf'], 'test-session-protection')

    def test_csrf_origin_and_dns_rebinding_denied(self):
        for headers in ({'X-Samy-CSRF': ''}, {'X-Samy-CSRF': 'é'}, {'Origin': 'https://evil.example'}, {'Host': 'evil.example'}, {'Sec-Fetch-Site': 'cross-site'}, {'Sec-Fetch-Site': 'same-site'}):
            with self.subTest(headers=headers), patch.object(main, 'send_key') as key:
                self.assertEqual(self.req('/api/key', '{"key":"volume_up"}', headers=headers)[0], 403)
                key.assert_not_called()
        self.assertEqual(self.req('/api/status', headers={'Host': 'evil.example'})[0], 403)

    def test_external_top_level_link_can_open_dashboard(self):
        for site in ('same-site', 'cross-site'):
            headers = {'Sec-Fetch-Site': site, 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document'}
            status, body = self.req('/', headers=headers)
            self.assertEqual(status, 200)
            self.assertIn(b'data-mode="control"', body)
            self.assertNotIn(CFG['token'].encode(), body)

    def test_navigation_exception_never_exposes_api_or_allows_commands(self):
        headers = {'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document'}
        with patch.object(main, 'tv_api') as api:
            for path in ('/api/session', '/api/status'):
                self.assertEqual(self.req(path, headers=headers)[0], 403)
            self.assertEqual(self.req('/api/key', '{"key":"up"}', headers=headers)[0], 403)
        api.assert_not_called()

    def test_external_iframe_or_fetch_cannot_load_dashboard(self):
        for mode, dest in (('navigate', 'iframe'), ('cors', 'empty')):
            self.assertEqual(self.req('/', headers={'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': mode, 'Sec-Fetch-Dest': dest})[0], 403)

    def test_authenticated_local_command(self):
        with patch.object(main, 'send_key', return_value=OK) as key:
            status, body = self.req('/api/key', '{"key":"volume_up"}')
        self.assertEqual(status, 200); key.assert_called_once_with(CFG, 'volume_up')
        self.assertIn('verify', json.loads(body)['note'])

    def test_bad_bodies_no_tv_write(self):
        with patch.object(main, 'tv_api') as api:
            for body in ('null', '[]', '"x"', 'invalid', '{"key":[]}'):
                self.assertEqual(self.req('/api/key', body)[0], 400)
            self.assertEqual(self.req('/api/key', 'x' * 2049)[0], 400)
            self.assertEqual(self.req('/api/key', '{}', headers={'Content-Type': 'text/plain'})[0], 415)
        api.assert_not_called()

    def test_secret_in_unknown_tv_field_scrubbed(self):
        with patch.object(main, 'read_state', return_value={**OK, 'unknown': CFG['token']}):
            status, body = self.req('/api/read/device')
        self.assertEqual(status, 200); self.assertNotIn(CFG['token'].encode(), body)

    def test_offline_preview_rejects_commands(self):
        with patch.object(self.control.RequestHandlerClass, 'cfg', None), patch.object(main, 'tv_api') as api:
            status, body = self.req('/api/session'); self.assertTrue(json.loads(body)['offline'])
            self.assertEqual(self.req('/api/key', '{"key":"up"}')[0], 400)
        api.assert_not_called()

    def test_malformed_device_response_handled(self):
        with patch.object(main, 'read_state', return_value=result([])):
            self.assertEqual(self.req('/api/status')[0], 502)

    def test_watchfree_http_status_uses_read_only_state(self):
        with patch.object(main, 'read_state', return_value=result([{'VALUE': {'APP_ID': '22', 'NAME_SPACE': 2}}])) as read:
            status, body = self.req('/api/watchfree/status')
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)['data']['matches_legacy_id'])
        self.assertFalse(json.loads(body)['data']['playback_verified'])
        read.assert_called_once_with(CFG, 'current_app')

    def test_diagnostics_no_device_claim(self):
        status, body = self.req('/api/diagnostics')
        self.assertEqual(status, 200); self.assertIsNone(json.loads(body)['data']['tv_page_requested_at_utc'])

    def test_partial_startup_closes_control_socket(self):
        first = Mock()
        with patch.object(main, 'Server', side_effect=[first, OSError('occupied')]), self.assertRaises(OSError):
            main.make_servers(None)
        first.server_close.assert_called_once()


if __name__ == '__main__': unittest.main()
