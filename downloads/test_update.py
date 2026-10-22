"""Checks for the optional local updater; no network or real credentials."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

UPDATER = Path(__file__).resolve().parents[1] / 'downloads' / 'update.py'


@unittest.skipUnless(UPDATER.exists(), 'Updater developer source is distributed separately from application ZIP')
class UpdateTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('samy_updater', UPDATER)
        self.updater = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.updater)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project'; self.root.mkdir(); (self.root/'site').mkdir()
        (self.root/'main.py').write_text('previous application')
        (self.root/'.vizio_local.json').write_text('private-sentinel-not-a-token')
        self.archive = Path(self.temp.name)/'update.zip'

    def make_zip(self, extras=None):
        files = {'main.py':'updated application', **{'site/'+n:'updated file' for n in ('index.html','controller.html','styles.css','app.js','catalog.json')}}
        files.update(extras or {})
        with zipfile.ZipFile(self.archive,'w') as z:
            for name, body in files.items(): z.writestr('Samy_Vizio_Modern_Home/'+name,body)

    def test_keeps_private_configuration_and_backs_up_application(self):
        self.make_zip(); backup=self.updater.apply_update(self.archive,self.root)
        self.assertEqual((self.root/'.vizio_local.json').read_text(),'private-sentinel-not-a-token')
        self.assertEqual((self.root/'main.py').read_text(),'updated application')
        self.assertEqual((backup/'main.py').read_text(),'previous application')
        self.assertFalse((backup/'.vizio_local.json').exists())

    def test_rejects_configuration_in_archive(self):
        self.make_zip({'.vizio_local.json':'must not overwrite'})
        with self.assertRaises(RuntimeError): self.updater.apply_update(self.archive,self.root)
        self.assertEqual((self.root/'.vizio_local.json').read_text(),'private-sentinel-not-a-token')
        self.assertEqual((self.root/'main.py').read_text(),'previous application')

    def test_rejects_path_traversal(self):
        self.make_zip({'../outside':'unsafe'})
        with self.assertRaises(RuntimeError): self.updater.apply_update(self.archive,self.root)
        self.assertEqual((self.root/'main.py').read_text(),'previous application')

    def test_rejects_symlink_destination(self):
        external=Path(self.temp.name)/'external'; external.write_text('preserve')
        (self.root/'site/app.js').symlink_to(external)
        self.make_zip()
        with self.assertRaises(RuntimeError): self.updater.apply_update(self.archive,self.root)
        self.assertEqual(external.read_text(),'preserve')
