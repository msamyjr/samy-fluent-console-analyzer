import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main

class TestVizio(unittest.TestCase):
    def test_owner_network_is_accepted(self):
        self.assertEqual(main.check_ip('192.164.113.114'), '192.164.113.114')
    def test_reject_loopback(self):
        with self.assertRaises(ValueError):
            main.check_ip('127.0.0.1')
    def test_redaction(self):
        obj = {'SERIAL_NUMBER': '1234', 'AUTH_TOKEN': 'secret', 'ITEMS': [{'CNAME': 'ssid', 'VALUE': 'network'}], 'MODEL_NAME': 'D40f-G9'}
        redacted = main.redact(obj)
        self.assertEqual(redacted['SERIAL_NUMBER'], '[REDACTED]')
        self.assertEqual(redacted['AUTH_TOKEN'], '[REDACTED]')
        self.assertEqual(redacted['MODEL_NAME'], 'D40f-G9')
        self.assertEqual(redacted['ITEMS'][0]['VALUE'], '[REDACTED]')
    def test_volume_command_payload(self):
        with patch.object(main, 'tv_api', return_value={'STATUS': {'RESULT': 'SUCCESS'}}) as api:
            main.send_key({'host': '192.164.113.114', 'token': 'fake'}, 'volume_up')
            args = api.call_args.args
            self.assertEqual(args[1:3], ('PUT', '/key_command/'))
            self.assertEqual(args[3]['KEYLIST'][0]['CODESET'], 5)
            self.assertEqual(args[3]['KEYLIST'][0]['CODE'], 1)
    def test_conjure_payload(self):
        with patch.object(main, 'local_ip_for', return_value='192.164.113.83'), patch.object(main, 'tv_api', return_value={'STATUS': {'RESULT': 'SUCCESS'}}) as api:
            main.launch_conjure({'host': '192.164.113.114', 'token': 'fake'}, 'http://192.164.113.83:8099/tv/')
            data = api.call_args.args[3]['VALUE']
            self.assertEqual(data['APP_ID'], '17')
            self.assertEqual(data['NAME_SPACE'], 4)
    def test_conjure_rejects_other_port(self):
        with self.assertRaises(ValueError):
            main.launch_conjure({}, 'http://example.com:8000/')

if __name__ == '__main__':
    unittest.main()
