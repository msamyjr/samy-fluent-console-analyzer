"""Local HTTP integration and simulated TV checks; no owner-TV requests."""
from contextlib import contextmanager
import http.client
import json
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import main
from test_security import CFG, OK, result


@contextmanager
def running_servers(cfg=None):
    with patch.object(main, 'CONTROL_PORT', 0), patch.object(main, 'SITE_PORT', 0):
        control, site = main.make_servers(cfg)
    threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (control, site)]
    for thread in threads: thread.start()
    try: yield control, site
    finally:
        for server in (control, site): server.shutdown(); server.server_close()
        for thread in threads: thread.join(2)


def request(server, path):
    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=4)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        return response.status, response.read()
    finally: connection.close()


class LauncherChecks(unittest.TestCase):
    def test_offline_connectivity_uses_real_local_servers_without_tv_requests(self):
        with running_servers() as (control, site), patch.object(main, 'CONTROL_PORT', control.server_port), patch.object(main, 'SITE_PORT', site.server_port), patch.object(main, 'tv_api') as api:
            report = main.connectivity_report()
        api.assert_not_called()
        self.assertEqual(report['tv_api'], 'not_configured')
        self.assertEqual(report['local_services']['static_site']['catalog_entries'], 14)
        self.assertEqual(report['local_services']['dashboard']['status'], 'reachable')
        self.assertFalse(report['network_settings_changed'])
        self.assertEqual(report['rendering'], 'requires_visual_test')

    def test_authenticated_connectivity_is_a_read_not_a_launch(self):
        device = result([{'VALUE': {'MODEL_NAME': 'D40f-G9', 'SYSTEM_INFO': {'VERSION': 'mock-version'}}}])
        with running_servers() as (control, site), patch.object(main, 'CONTROL_PORT', control.server_port), patch.object(main, 'SITE_PORT', site.server_port), patch.object(main, 'local_ip_for', return_value='10.0.0.2'), patch.object(main, 'tv_api', return_value=device) as api:
            report = main.connectivity_report(CFG)
        api.assert_called_once_with(CFG, 'GET', main.READ_PATHS['device'])
        self.assertEqual(report['tv_api'], 'authenticated_read_succeeded')
        self.assertNotIn(CFG['token'], json.dumps(report))

    def test_missing_local_services_are_reported_not_passed(self):
        with patch.object(main.http.client, 'HTTPConnection', side_effect=lambda *a, **k: BrokenConnection()):
            report = main.connectivity_report()
        for value in report['local_services'].values():
            self.assertEqual(value['status'], 'unavailable_or_unexpected_response')

    def test_only_configured_peer_counts_as_tv_request(self):
        with running_servers(CFG) as (control, site):
            request(site, '/tv/')
            status, body = request(control, '/api/diagnostics')
        self.assertEqual(status, 200)
        state = json.loads(body)['data']
        self.assertIsNone(state['tv_page_requested_at_utc'])
        self.assertEqual(state['tv_assets_requested'], [])

    def test_tv_asset_requests_remain_distinct_from_rendering(self):
        # Synthetic loopback peer stands in for TV; only local servers are contacted.
        with running_servers({'host': '127.0.0.1', 'token': 'fixture-only'}) as (control, site):
            for path in ('/tv/', '/tv/app.js', '/tv/styles.css', '/tv/catalog.json'):
                self.assertEqual(request(site, path)[0], 200)
            _, body = request(control, '/api/diagnostics')
        state = json.loads(body)['data']
        self.assertIsNotNone(state['tv_page_requested_at_utc'])
        self.assertEqual(len(state['tv_assets_requested']), 4)
        self.assertFalse(state['rendering_verified'])
        self.assertFalse(state['remote_verified'])
        self.assertEqual(state['conjure_api_status'], 'not_attempted')

    def post(self, server, path, data):
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=4)
        try:
            connection.request('POST', path, body=json.dumps(data), headers={
                'Content-Type': 'application/json', 'X-Samy-CSRF': server.RequestHandlerClass.csrf})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally: connection.close()

    def test_native_app_endpoint_uses_allowlisted_smartcast_payload(self):
        with running_servers(CFG) as (control, site), patch.object(main, 'tv_api', return_value=OK) as api:
            for app in ('netflix', 'plex'):
                status, data = self.post(control, '/api/app', {'app': app})
                self.assertEqual(status, 200)
                self.assertEqual(data['result'], 'SUCCESS')
                api.assert_called_with(CFG, 'PUT', '/app/launch', {'VALUE': main.APPS[app]})
            self.assertEqual(api.call_count, 2)

    def test_native_app_endpoint_rejects_unknown_id_without_tv_request(self):
        with running_servers(CFG) as (control, site), patch.object(main, 'tv_api') as api:
            status, data = self.post(control, '/api/app', {'app': 'unverified-native-app'})
        self.assertEqual(status, 400)
        api.assert_not_called()

    def test_conjure_endpoint_tracks_api_acceptance_separately(self):
        with running_servers(CFG) as (control, site), patch.object(main, 'local_ip_for', return_value='10.0.0.2'), patch.object(main, 'launch_conjure', return_value=OK) as launch:
            status, data = self.post(control, '/api/conjure', {})
            self.assertEqual(status, 200)
            _, raw = request(control, '/api/diagnostics')
        launch.assert_called_once_with(CFG, 'http://10.0.0.2:8099/tv/')
        observed = json.loads(raw)['data']
        self.assertEqual(observed['conjure_api_status'], 'accepted')
        self.assertIsNone(observed['tv_page_requested_at_utc'])
        self.assertFalse(observed['rendering_verified'])

    def test_accepted_conjure_is_recorded_without_rendering_claim(self):
        server = SimpleNamespace(observation={'tv_page_requested_at_utc': 'old', 'tv_assets_requested': ['old']}, observation_lock=threading.Lock())
        with patch.object(main, 'launch_conjure', return_value=OK) as launch:
            self.assertEqual(main.observed_conjure(CFG, 'http://10.0.0.2:8099/tv/', server), OK)
        launch.assert_called_once()
        self.assertEqual(server.observation['conjure_api_status'], 'accepted')
        self.assertIsNone(server.observation['tv_page_requested_at_utc'])
        self.assertEqual(server.observation['tv_assets_requested'], [])

    def test_failed_conjure_attempt_is_not_reported_as_accepted(self):
        server = SimpleNamespace(observation={}, observation_lock=threading.Lock())
        with patch.object(main, 'launch_conjure', side_effect=main.TVError('UNSUPPORTED')), self.assertRaises(main.TVError):
            main.observed_conjure(CFG, 'http://10.0.0.2:8099/tv/', server)
        self.assertEqual(server.observation['conjure_api_status'], 'failed')
        self.assertNotIn(CFG['token'], json.dumps(server.observation))


class BrokenConnection:
    def request(self, *args, **kwargs): raise OSError('offline fixture')
    def close(self): pass
