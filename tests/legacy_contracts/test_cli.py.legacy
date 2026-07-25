"""Test CLI command coverage (weakness #3 fix)."""
import unittest, subprocess, sys, os, tempfile, json

class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        self.db = self.tmp.name
        self.pack = os.path.join(os.path.dirname(__file__), "..", "cemm", "language_packs", "en.json")
        self.data = [
            os.path.join(os.path.dirname(__file__), "..", "cemm", "data", "base.json"),
            os.path.join(os.path.dirname(__file__), "..", "cemm", "data", "family_knowledge.json"),
        ]

    def tearDown(self):
        if os.path.exists(self.db):
            os.unlink(self.db)

    def _run(self, *args):
        r = subprocess.run([sys.executable, "-m", "cemm.cli"] + list(args),
                           capture_output=True, text=True, timeout=120)
        return r

    def test_init_command(self):
        r = self._run("init", "--db", self.db, "--pack", self.pack,
                      *[d for d in self.data for d in ("--data", d)])
        self.assertEqual(r.returncode, 0, f"init failed: {r.stderr}")

    def test_reload_command(self):
        self._run("init", "--db", self.db, "--pack", self.pack,
                  *[d for d in self.data for d in ("--data", d)])
        r = self._run("reload", "--db", self.db, "--pack", self.pack)
        self.assertEqual(r.returncode, 0, f"reload failed: {r.stderr}")

    def test_acquire_command(self):
        self._run("init", "--db", self.db, "--pack", self.pack,
                  *[d for d in self.data for d in ("--data", d)])
        r = self._run("acquire", "--db", self.db, "--pack", self.pack,
                      "--text", "Friction is resistance.",
                      "--mentions", json.dumps([{"surface":"Friction","kind":"concept"},{"surface":"resistance","kind":"concept"}]))
        self.assertEqual(r.returncode, 0, f"acquire failed: {r.stderr}")

if __name__ == "__main__":
    unittest.main()
