import os
import tempfile
import unittest

import app


class OutputPathTests(unittest.TestCase):
    def test_create_output_path_uses_episode_suffix_for_bracketed_numbers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            try:
                path = app.create_output_path("異世界的處置依社畜而定 [02]")
            finally:
                os.chdir(original_cwd)

        normalized = path.replace('\\', '/')
        self.assertTrue(normalized.endswith("video/異世界的處置依社畜而定/異世界的處置依社畜而定-02.mp4"))


if __name__ == "__main__":
    unittest.main()
