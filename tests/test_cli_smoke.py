import subprocess
import unittest

class TestCLISmoke(unittest.TestCase):
    def test_help(self):
        result = subprocess.run(["python3", "-m", "ncsdl", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Available commands", result.stdout)

    def test_count(self):
        result = subprocess.run(["python3", "-m", "ncsdl", "count"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Total NCS videos on YouTube", result.stdout)

    def test_list_genres(self):
        result = subprocess.run(["python3", "-m", "ncsdl.cli", "list-genres"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)

if __name__ == "__main__":
    unittest.main()
