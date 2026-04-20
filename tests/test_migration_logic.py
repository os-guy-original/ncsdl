import os
import shutil
import unittest
from pathlib import Path
from ncsdl.downloader.migration import migrate_songs

class TestMigrationLogic(unittest.TestCase):
    def setUp(self):
        self.src = Path("test_src")
        self.dst = Path("test_dst")
        for p in (self.src, self.dst):
            if p.exists(): shutil.rmtree(p)
            p.mkdir(parents=True)
        
        # Create some dummy files
        (self.src / "Artist - Song 1.m4a").write_text("dummy")
        (self.src / "Artist - Song 2.mp3").write_text("dummy")

    def tearDown(self):
        for p in (self.src, self.dst):
            if p.exists(): shutil.rmtree(p)

    def test_local_migration(self):
        # Mock dependencies in renamer/migration if needed
        import ncsdl.downloader.migration
        ncsdl.downloader.migration.is_audio_valid = lambda x: True
        
        transferred, renamed, skipped, errors = migrate_songs(
            str(self.src), str(self.dst), mode="copy"
        )
        
        self.assertEqual(transferred, 2)
        self.assertEqual(len(list(self.dst.iterdir())), 2)
        self.assertEqual(skipped, 0)
        self.assertEqual(len(errors), 0)

    def test_duplicate_skip(self):
        # Pre-create one file in dst
        (self.dst / "Artist - Song 1.m4a").write_text("existing")
        
        import ncsdl.downloader.migration
        ncsdl.downloader.migration.is_audio_valid = lambda x: True
        
        transferred, renamed, skipped, errors = migrate_songs(
            str(self.src), str(self.dst), mode="copy"
        )
        
        # Should transfer only the second file
        self.assertEqual(transferred, 1)
        self.assertEqual(skipped, 1)

if __name__ == "__main__":
    unittest.main()
