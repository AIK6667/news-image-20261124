"""Check the entry end to end: two runs, one file, the contest's limits.

Run it with:  python3 -m unittest discover -s tests
"""

import hashlib
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def render(directory):
    env = dict(os.environ, MAKEFUN_OUTPUT_DIR=directory)
    subprocess.run([sys.executable, os.path.join(ROOT, "main.py")], check=True,
                   env=env, stdout=subprocess.DEVNULL)
    with open(os.path.join(directory, "entry.png"), "rb") as handle:
        return handle.read()


class EntryTest(unittest.TestCase):
    def test_two_runs_write_the_same_bytes(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            one = render(first)
            two = render(second)
        self.assertEqual(hashlib.sha256(one).hexdigest(), hashlib.sha256(two).hexdigest())

    def test_the_file_is_one_whole_png_within_the_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            data = render(directory)
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertLessEqual(len(data), 1048576)
        width, height, depth, colour, _compression, _filter, interlace = struct.unpack(
            ">IIBBBBB", data[16:29])
        self.assertEqual((depth, colour, interlace), (8, 2, 0))
        self.assertLessEqual(width, 1024)
        self.assertLessEqual(height, 1024)

        position = 8
        image = b""
        tags = []
        while position < len(data):
            length = struct.unpack(">I", data[position:position + 4])[0]
            tag = data[position + 4:position + 8]
            payload = data[position + 8:position + 8 + length]
            crc = struct.unpack(">I", data[position + 8 + length:position + 12 + length])[0]
            self.assertEqual(zlib.crc32(tag + payload) & 0xFFFFFFFF, crc, tag)
            tags.append(tag)
            if tag == b"IDAT":
                image += payload
            position += 12 + length
        self.assertEqual(tags[0], b"IHDR")
        self.assertEqual(tags[-1], b"IEND")
        self.assertEqual(len(zlib.decompress(image)), height * (1 + width * 3))

    def test_the_page_names_the_day_and_fits_its_columns(self):
        sys.path.insert(0, ROOT)
        import main
        self.assertEqual(main.DAY, "TUESDAY 24 NOVEMBER 2026")
        self.assertEqual(len(main.STORIES), 8)
        # Every line has to fit the column the layout gives it.
        for story in main.STORIES:
            for line in story["headline"]:
                self.assertLessEqual(main.text_width(line, 5), 468, line)
            self.assertLessEqual(len(main.wrap(story["deck"], 3, 468)), 3, story["deck"])


if __name__ == "__main__":
    unittest.main()
