import os
import shutil
import unittest
from pathlib import Path
from ncsdl.downloader.renamer import rename_songs

class TestRenamerLogic(unittest.TestCase):
    def setUp(self):
        self.dir = Path("test_rename_dir")
        if self.dir.exists(): shutil.rmtree(self.dir)
        self.dir.mkdir(parents=True)
        
        # Corrupted name
        (self.dir / "Artist - Song | Extra.m4a").write_text("dummy")

    def tearDown(self):
        if self.dir.exists(): shutil.rmtree(self.dir)

    def test_renamer_casing(self):
        import ncsdl.downloader.renamer
        ncsdl.downloader.renamer.is_audio_valid = lambda x: True
        # Mock get_ncsdl_id and cache
        ncsdl.downloader.renamer.get_ncsdl_id = lambda x: "id1"
        ncsdl.downloader.renamer._load_title_cache = lambda: {"id1": "Artist - SONG"}
        
        processed, renamed, skipped, errors = rename_songs(str(self.dir))
        
        self.assertEqual(renamed, 1)
        self.assertTrue((self.dir / "Artist - SONG.m4a").exists())

    def test_collision_handling(self):
        # Clear dir from setup
        for f in self.dir.iterdir(): f.unlink()
        
        # Create two files that would map to same name
        (self.dir / "File A.m4a").write_text("a")
        (self.dir / "File B.m4a").write_text("b")
        
        import ncsdl.downloader.renamer
        ncsdl.downloader.renamer.get_ncsdl_id = lambda x: "idX"
        ncsdl.downloader.renamer._load_title_cache = lambda: {"idX": "Artist - Fixed Name"}
        
        processed, renamed, skipped, errors = rename_songs(str(self.dir))
        
        # One should be renamed, one should be skipped due to collision
        self.assertEqual(renamed, 1)
        self.assertEqual(skipped, 1)

if __name__ == "__main__":
    unittest.main()
