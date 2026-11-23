"""No app dependencies needed: python -m unittest discover -s tests -p test_release.py."""
import hashlib,importlib.util,tempfile,unittest,zipfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('release',Path(__file__).resolve().parents[1]/'scripts/package_release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'source';self.root.mkdir()
        (self.root/'README.md').write_text('Demo\n');(self.root/'release-files.txt').write_text('README.md\nrelease-files.txt\n')
        self.out=Path(self.tmp.name)/'release.zip'
    def test_reproducible_verified_and_unlisted_secrets_excluded(self):
        (self.root/'.env').write_text('PRIVATE=secret');one=release.create(self.root,self.out)
        other=self.out.with_name('other.zip');two=release.create(self.root,other)
        self.assertEqual(one['sha256'],two['sha256']);self.assertEqual(one['files'],3)
        with zipfile.ZipFile(self.out) as z:self.assertNotIn('CineDraft-VSCode/.env',z.namelist())
    def test_existing_output_is_preserved(self):
        self.out.write_bytes(b'existing')
        with self.assertRaises(ValueError):release.create(self.root,self.out)
        self.assertEqual(self.out.read_bytes(),b'existing')
    def test_sensitive_and_traversal_paths_rejected(self):
        for name in ['.env','backend/.env','../file','/file','a/../b','C:/file','a\\b','backups/a.txt','private.key','x.local.json']:
            with self.subTest(name=name),self.assertRaises(ValueError):release.safe_name(name)
    def test_missing_or_duplicate_sources_fail(self):
        for listing in ['missing\nrelease-files.txt\n','README.md\nREADME.md\nrelease-files.txt\n']:
            (self.root/'release-files.txt').write_text(listing)
            with self.assertRaises(ValueError):release.create(self.root,self.out)
            self.assertFalse(self.out.exists())
    def test_symlink_is_refused(self):
        (self.root/'README.md').unlink()
        try:(self.root/'README.md').symlink_to(Path(self.tmp.name)/'target')
        except OSError:self.skipTest('Symlinks unavailable')
        with self.assertRaises(ValueError):release.create(self.root,self.out)
    def test_modified_archive_entry_is_detected(self):
        release.create(self.root,self.out);bad=self.out.with_name('bad.zip')
        with zipfile.ZipFile(self.out) as original,zipfile.ZipFile(bad,'w') as changed:
            for name in original.namelist():changed.writestr(name,b'changed' if name.endswith('README.md') else original.read(name))
        with self.assertRaises(ValueError):release.verify(bad)
    def test_wrong_archive_root_is_rejected(self):
        with zipfile.ZipFile(self.out,'w') as z:z.writestr('../outside','text');z.writestr('CineDraft-VSCode/MANIFEST.sha256','')
        with self.assertRaises(ValueError):release.verify(self.out)
    def test_manifest_cannot_omit_an_archive_member(self):
        release.create(self.root,self.out)
        with zipfile.ZipFile(self.out,'a') as z:z.writestr('CineDraft-VSCode/extra.txt','unexpected')
        with self.assertRaises(ValueError):release.verify(self.out)
if __name__=='__main__':unittest.main()
