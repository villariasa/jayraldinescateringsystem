import unittest
import os

class TestRunShScriptSyntax(unittest.TestCase):
    def test_run_sh_exists(self):
        script_path = os.path.join("Catering_Present", "jayraldines_catering", "run.sh")
        self.assertTrue(os.path.exists(script_path))
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertTrue(content.startswith("#!/usr/bin/env bash"))
        self.assertIn("venv/bin/python", content)

if __name__ == "__main__":
    unittest.main()
