"""Release gates prevent wrong versions and accidental private file packaging."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("check_release", ROOT / "scripts/check_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseChecks(unittest.TestCase):
    def test_actual_version_matches_release_tag(self):
        name, version = release.check_version(ROOT)
        self.assertEqual(name, "qnap-user-manager")
        self.assertEqual(release.check_version(ROOT, "v" + version), (name, version))
        with self.assertRaises(ValueError):
            release.check_version(ROOT, "v999.0.0")

    def test_metadata_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "qnap_sdk").mkdir()
            (root / "pyproject.toml").write_text('[project]\nname="fixture"\nversion="1.0"\n')
            (root / "qnap_sdk/__init__.py").write_text('__version__="2.0"\n')
            with self.assertRaises(ValueError):
                release.check_version(root)

    def test_sensitive_or_escaping_paths_refused(self):
        for path in (
            "work/file",
            "reports/file",
            "pkg/nas-session.txt",
            "pkg/.env",
            "../outside",
            "/absolute",
            "pkg/capture.har",
            "pkg/__pycache__/a.pyc",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                release.check_archive_names([path])
        release.check_archive_names(["qnap_sdk/client.py", "pkg/LICENSE"])
