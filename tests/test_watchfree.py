"""WatchFree capability observations are simulated, never proof of playback."""
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import main
from test_security import CFG, OK, result


class WatchFreeTests(unittest.TestCase):
    def test_launch_uses_single_legacy_community_id(self):
        with patch.object(main, 'tv_api', return_value=OK) as api:
            main.launch_app(CFG, 'watchfree')
        self.assertEqual(api.call_args.args[1:], ('PUT', '/app/launch', {'VALUE': {'APP_ID': '22', 'NAME_SPACE': 2, 'MESSAGE': ''}}))

    def test_known_current_app_shapes(self):
        identity = {'APP_ID': '22', 'NAME_SPACE': 2}
        for data in (identity, {'VALUE': identity}, result([identity]), result([{'VALUE': identity}])):
            self.assertEqual(main.current_app_identity(data), identity)

    def test_singular_item_response(self):
        self.assertEqual(main.current_app_identity({'STATUS': {'RESULT': 'SUCCESS'}, 'ITEM': {'VALUE': {'APP_ID': '22', 'NAME_SPACE': 2}}}), {'APP_ID': '22', 'NAME_SPACE': 2})

    def test_lowercase_singular_response(self):
        self.assertEqual(main.current_app_identity({'item': {'value': {'app_id': '22', 'name_space': 2}}}), {'APP_ID': '22', 'NAME_SPACE': 2})

    def test_singular_null_does_not_claim_playback(self):
        self.assertIsNone(main.current_app_identity({'ITEM': {'VALUE': None}}))
        self.assertIsNone(main.current_app_identity(None))

    def test_normalizes_numeric_ids(self):
        self.assertEqual(main.current_app_identity({'VALUE': {'APP_ID': 22, 'NAME_SPACE': '2'}}), {'APP_ID': '22', 'NAME_SPACE': 2})

    def test_unknown_shapes_do_not_invent_identity(self):
        for data in ({}, {'ITEMS': None}, result([{'VALUE': 'unknown'}]), {'APP_ID': True, 'NAME_SPACE': 2}):
            self.assertIsNone(main.current_app_identity(data))

    def test_matching_id_is_not_playback_verification(self):
        with patch.object(main, 'read_state', return_value=result([{'VALUE': {'APP_ID': '22', 'NAME_SPACE': 2}}])):
            report = main.watchfree_status(CFG)
        self.assertTrue(report['matches_legacy_id'])
        self.assertFalse(report['screen_verified'])
        self.assertFalse(report['playback_verified'])

    def test_mismatch_and_unknown_distinct(self):
        for data, expected in ((result([{'VALUE': {'APP_ID': '1', 'NAME_SPACE': 3}}]), False), (result([]), None)):
            with patch.object(main, 'read_state', return_value=data):
                self.assertIs(main.watchfree_status(CFG)['matches_legacy_id'], expected)

    def test_watchfree_status_reads_only_current_app(self):
        with patch.object(main, 'tv_api', return_value=result([])) as api:
            main.watchfree_status(CFG)
        api.assert_called_once_with(CFG, 'GET', '/app/current')

    def test_cli_check_does_not_launch(self):
        with patch.object(sys, 'argv', ['main.py', 'watchfree', '--check']), patch.object(main, 'read_config', return_value=CFG), patch.object(main, 'launch_app') as launch, patch.object(main, 'watchfree_status', return_value={'playback_verified': False}), redirect_stdout(io.StringIO()):
            self.assertIsNone(main.main())
        launch.assert_not_called()

    def test_cli_launch_once(self):
        with patch.object(sys, 'argv', ['main.py', 'watchfree']), patch.object(main, 'read_config', return_value=CFG), patch.object(main, 'launch_app', return_value=OK) as launch, patch.object(main, 'watchfree_status', return_value={'playback_verified': False}), redirect_stdout(io.StringIO()):
            main.main()
        launch.assert_called_once_with(CFG, 'watchfree')

    def test_catalog_malaysian_links_are_web_only(self):
        catalog = json.loads((main.SITE / 'catalog.json').read_text())
        for app_id in ('rtmklik', 'awani'):
            item = next(a for a in catalog['apps'] if a['id'] == app_id)
            self.assertEqual(item['type'], 'web')
            self.assertIn('unverified', item['status'])
            self.assertTrue(item['url'].startswith('https://'))

class SpotifyTests(unittest.TestCase):
    def test_spotify_is_official_web_link_not_invented_native_id(self):
        catalog = json.loads((main.SITE / 'catalog.json').read_text())
        app = next(a for a in catalog['apps'] if a['id'] == 'spotify-web')
        self.assertEqual(app['url'], 'https://open.spotify.com/')
        self.assertEqual(app['type'], 'web')
        self.assertIn('unverified', app['status'])
        self.assertNotIn('spotify', main.APPS)
