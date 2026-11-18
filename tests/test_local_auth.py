"""Controles sem container/rede para o bootstrap de autenticação local."""

import importlib.util
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare-local-auth.py"
spec = importlib.util.spec_from_file_location("local_auth", SCRIPT)
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)


class LocalAuthTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def hash_stub(self, argv, **kwargs):
        self.assertEqual(argv[1:3], ["-niBC", "12"])
        self.assertNotIn(kwargs["input"].strip(), argv)
        return subprocess.CompletedProcess(
            argv, 0, argv[3] + ":$2y$12$synthetic-for-unit-test\n", ""
        )

    def prepare(self):
        with (
            patch.object(auth.shutil, "which", return_value="/usr/bin/htpasswd"),
            patch.object(auth.subprocess, "run", side_effect=self.hash_stub),
        ):
            auth.prepare(self.root)

    def test_random_values_and_rerun_preserves_passwords(self):
        self.prepare()
        output = self.root / ".local-lab"
        initial = (output / "lab.env").read_bytes()
        self.prepare()
        self.assertEqual(initial, (output / "lab.env").read_bytes())
        values = dict(line.split("=", 1) for line in initial.decode().splitlines())
        self.assertEqual(len(set(values.values())), 3)
        self.assertTrue(all(len(value) == 64 for value in values.values()))
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((output / "lab.env").stat().st_mode), 0o600)
        for service, variable in [
            ("prometheus", "PROMETHEUS_BASIC_AUTH_PASSWORD"),
            ("alertmanager", "ALERTMANAGER_BASIC_AUTH_PASSWORD"),
        ]:
            self.assertEqual(
                (output / (service + ".password")).read_text().strip(), values[variable]
            )

    def test_wrapper_rejects_symlinks_before_side_effects(self):
        original = SCRIPT.parent / "bootstrap-local-lab.sh"
        for relative in [
            ".local-lab",
            ".local-lab/certs",
            ".local-lab/certs/tls.key",
            ".local-lab/certs/tls.crt",
            ".env",
        ]:
            with (
                self.subTest(relative=relative),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory) / "repo"
                (root / "scripts").mkdir(parents=True)
                wrapper = root / "scripts/bootstrap-local-lab.sh"
                wrapper.write_bytes(original.read_bytes())
                outside = Path(directory) / "outside"
                outside.mkdir(mode=0o750)
                sentinel = outside / "preserve"
                sentinel.write_text("preserve")
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(outside, target_is_directory=True)
                before = stat.S_IMODE(outside.stat().st_mode)
                result = subprocess.run(
                    ["/bin/bash", str(wrapper)], capture_output=True, text=True
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("symlink", result.stderr)
                self.assertEqual(stat.S_IMODE(outside.stat().st_mode), before)
                self.assertEqual(sentinel.read_text(), "preserve")
                self.assertEqual(list(outside.iterdir()), [sentinel])

    def test_symlink_directory_rejected(self):
        (self.root / ".local-lab").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.prepare()

    def test_invalid_existing_credentials_are_preserved(self):
        output = self.root / ".local-lab"
        output.mkdir()
        file = output / "lab.env"
        file.write_text("INVALID=do-not-overwrite\n")
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(file.read_text(), "INVALID=do-not-overwrite\n")


if __name__ == "__main__":
    unittest.main()
